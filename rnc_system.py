#!/usr/bin/env python3
"""Sistema de gestão de RNCs (Registro de Não Conformidade)."""

from __future__ import annotations

import argparse
import html
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable

DATE_FMT = "%Y-%m-%d"


@dataclass
class RNCInput:
    cliente: str
    rastreabilidade: str
    codigo_agro: str
    codigo_terceiro: str
    procedente: bool
    formal: bool
    observacoes: str
    data_registro: date
    prazo_resposta: date


@dataclass
class CorrectiveActionInput:
    rnc_id: int
    descricao: str
    responsavel: str
    prazo: date


@dataclass
class IshikawaInput:
    metodo: str = ""
    maquina: str = ""
    mao_de_obra: str = ""
    material: str = ""
    medicao: str = ""
    meio_ambiente: str = ""


class RNCSystem:
    def __init__(self, db_path: str = "rnc.db") -> None:
        self.db_path = db_path
        self._ensure_parent_exists()

    def _ensure_parent_exists(self) -> None:
        Path(self.db_path).resolve().parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _ensure_column(self, conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
        cols = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
        if column not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")

    def init_db(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS rncs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cliente TEXT NOT NULL,
                    rastreabilidade TEXT NOT NULL,
                    codigo_agro TEXT NOT NULL,
                    codigo_terceiro TEXT NOT NULL,
                    procedente INTEGER NOT NULL CHECK (procedente IN (0, 1)),
                    formal INTEGER NOT NULL CHECK (formal IN (0, 1)),
                    observacoes TEXT NOT NULL,
                    data_registro TEXT NOT NULL,
                    prazo_resposta TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'aberta',
                    data_encerramento TEXT
                );

                CREATE TABLE IF NOT EXISTS corrective_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rnc_id INTEGER NOT NULL,
                    descricao TEXT NOT NULL,
                    responsavel TEXT NOT NULL,
                    prazo TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'aberta',
                    data_conclusao TEXT,
                    FOREIGN KEY (rnc_id) REFERENCES rncs(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS evidences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    target_type TEXT NOT NULL CHECK (target_type IN ('rnc', 'acao')),
                    target_id INTEGER NOT NULL,
                    file_path TEXT NOT NULL,
                    descricao TEXT NOT NULL,
                    data_anexo TEXT NOT NULL
                );
                """
            )
            self._ensure_column(conn, "rncs", "ishikawa_metodo", "ishikawa_metodo TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "rncs", "ishikawa_maquina", "ishikawa_maquina TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "rncs", "ishikawa_mao_de_obra", "ishikawa_mao_de_obra TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "rncs", "ishikawa_material", "ishikawa_material TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "rncs", "ishikawa_medicao", "ishikawa_medicao TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "rncs", "ishikawa_meio_ambiente", "ishikawa_meio_ambiente TEXT NOT NULL DEFAULT ''")

    def add_rnc(self, rnc: RNCInput) -> int:
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO rncs (
                    cliente, rastreabilidade, codigo_agro, codigo_terceiro,
                    procedente, formal, observacoes, data_registro, prazo_resposta
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rnc.cliente,
                    rnc.rastreabilidade,
                    rnc.codigo_agro,
                    rnc.codigo_terceiro,
                    int(rnc.procedente),
                    int(rnc.formal),
                    rnc.observacoes,
                    rnc.data_registro.strftime(DATE_FMT),
                    rnc.prazo_resposta.strftime(DATE_FMT),
                ),
            )
            return int(cur.lastrowid)

    def update_ishikawa(self, rnc_id: int, ish: IshikawaInput) -> None:
        with self.connect() as conn:
            cur = conn.execute(
                """
                UPDATE rncs
                SET ishikawa_metodo = ?,
                    ishikawa_maquina = ?,
                    ishikawa_mao_de_obra = ?,
                    ishikawa_material = ?,
                    ishikawa_medicao = ?,
                    ishikawa_meio_ambiente = ?
                WHERE id = ?
                """,
                (
                    ish.metodo,
                    ish.maquina,
                    ish.mao_de_obra,
                    ish.material,
                    ish.medicao,
                    ish.meio_ambiente,
                    rnc_id,
                ),
            )
            if cur.rowcount == 0:
                raise ValueError(f"RNC {rnc_id} não encontrada")

    def list_rncs(self, status: str | None = None) -> list[sqlite3.Row]:
        query = "SELECT * FROM rncs"
        params: tuple[str, ...] = ()
        if status:
            query += " WHERE status = ?"
            params = (status,)
        query += " ORDER BY data_registro DESC, id DESC"
        with self.connect() as conn:
            return list(conn.execute(query, params))

    def add_corrective_action(self, action: CorrectiveActionInput) -> int:
        with self.connect() as conn:
            if not conn.execute("SELECT 1 FROM rncs WHERE id = ?", (action.rnc_id,)).fetchone():
                raise ValueError(f"RNC {action.rnc_id} não encontrada")
            cur = conn.execute(
                """
                INSERT INTO corrective_actions (rnc_id, descricao, responsavel, prazo)
                VALUES (?, ?, ?, ?)
                """,
                (action.rnc_id, action.descricao, action.responsavel, action.prazo.strftime(DATE_FMT)),
            )
            return int(cur.lastrowid)

    def close_rnc(self, rnc_id: int, data_encerramento: date | None = None) -> None:
        dt = data_encerramento or date.today()
        with self.connect() as conn:
            cur = conn.execute(
                "UPDATE rncs SET status = 'encerrada', data_encerramento = ? WHERE id = ?",
                (dt.strftime(DATE_FMT), rnc_id),
            )
            if cur.rowcount == 0:
                raise ValueError(f"RNC {rnc_id} não encontrada")

    def close_corrective_action(self, action_id: int, data_conclusao: date | None = None) -> None:
        dt = data_conclusao or date.today()
        with self.connect() as conn:
            cur = conn.execute(
                "UPDATE corrective_actions SET status = 'concluida', data_conclusao = ? WHERE id = ?",
                (dt.strftime(DATE_FMT), action_id),
            )
            if cur.rowcount == 0:
                raise ValueError(f"Ação corretiva {action_id} não encontrada")

    def traceability_search(self, termo: str) -> list[sqlite3.Row]:
        like = f"%{termo}%"
        with self.connect() as conn:
            return list(
                conn.execute(
                    """
                    SELECT * FROM rncs
                    WHERE cliente LIKE ?
                       OR rastreabilidade LIKE ?
                       OR codigo_agro LIKE ?
                       OR codigo_terceiro LIKE ?
                    ORDER BY data_registro DESC
                    """,
                    (like, like, like, like),
                )
            )

    def list_all_actions(self) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return list(
                conn.execute(
                    """
                    SELECT ca.*, r.cliente, r.codigo_agro
                    FROM corrective_actions ca
                    JOIN rncs r ON r.id = ca.rnc_id
                    ORDER BY ca.prazo ASC, ca.id ASC
                    """
                )
            )

    def get_alerts(self, days_ahead: int = 3) -> dict[str, list[sqlite3.Row]]:
        today = date.today()
        limit = today + timedelta(days=days_ahead)
        with self.connect() as conn:
            overdue_responses = list(
                conn.execute(
                    "SELECT * FROM rncs WHERE status = 'aberta' AND prazo_resposta < ? ORDER BY prazo_resposta ASC",
                    (today.strftime(DATE_FMT),),
                )
            )
            upcoming_responses = list(
                conn.execute(
                    """
                    SELECT * FROM rncs
                    WHERE status = 'aberta' AND prazo_resposta >= ? AND prazo_resposta <= ?
                    ORDER BY prazo_resposta ASC
                    """,
                    (today.strftime(DATE_FMT), limit.strftime(DATE_FMT)),
                )
            )
            overdue_actions = list(
                conn.execute(
                    """
                    SELECT ca.*, r.cliente, r.codigo_agro
                    FROM corrective_actions ca JOIN rncs r ON r.id = ca.rnc_id
                    WHERE ca.status = 'aberta' AND ca.prazo < ?
                    ORDER BY ca.prazo ASC
                    """,
                    (today.strftime(DATE_FMT),),
                )
            )
            upcoming_actions = list(
                conn.execute(
                    """
                    SELECT ca.*, r.cliente, r.codigo_agro
                    FROM corrective_actions ca JOIN rncs r ON r.id = ca.rnc_id
                    WHERE ca.status = 'aberta' AND ca.prazo >= ? AND ca.prazo <= ?
                    ORDER BY ca.prazo ASC
                    """,
                    (today.strftime(DATE_FMT), limit.strftime(DATE_FMT)),
                )
            )
        return {
            "respostas_vencidas": overdue_responses,
            "respostas_proximas": upcoming_responses,
            "acoes_vencidas": overdue_actions,
            "acoes_proximas": upcoming_actions,
        }

    def _ensure_target_exists(self, conn: sqlite3.Connection, target_type: str, target_id: int) -> None:
        if target_type == "rnc":
            exists = conn.execute("SELECT 1 FROM rncs WHERE id = ?", (target_id,)).fetchone()
        else:
            exists = conn.execute("SELECT 1 FROM corrective_actions WHERE id = ?", (target_id,)).fetchone()
        if not exists:
            nome = "RNC" if target_type == "rnc" else "Ação corretiva"
            raise ValueError(f"{nome} {target_id} não encontrada")

    def add_evidence(self, target_type: str, target_id: int, file_path: str, descricao: str) -> int:
        path = Path(file_path).expanduser().resolve()
        if not path.exists():
            raise ValueError(f"Arquivo de evidência não encontrado: {path}")
        with self.connect() as conn:
            self._ensure_target_exists(conn, target_type, target_id)
            cur = conn.execute(
                """
                INSERT INTO evidences (target_type, target_id, file_path, descricao, data_anexo)
                VALUES (?, ?, ?, ?, ?)
                """,
                (target_type, target_id, str(path), descricao, date.today().strftime(DATE_FMT)),
            )
            return int(cur.lastrowid)

    def list_evidences(self, target_type: str | None = None, target_id: int | None = None) -> list[sqlite3.Row]:
        query = "SELECT * FROM evidences"
        params: list[object] = []
        filters = []
        if target_type:
            filters.append("target_type = ?")
            params.append(target_type)
        if target_id is not None:
            filters.append("target_id = ?")
            params.append(target_id)
        if filters:
            query += " WHERE " + " AND ".join(filters)
        query += " ORDER BY data_anexo DESC, id DESC"
        with self.connect() as conn:
            return list(conn.execute(query, tuple(params)))


def _status_badge(status: str) -> str:
    color = "#027a48" if status in {"encerrada", "concluida"} else "#9f580a"
    return (
        "<span style='padding:2px 8px;border-radius:12px;"
        f"background:#fff4e5;color:{color};font-weight:600'>{html.escape(status)}</span>"
    )


def generate_html_report(system: RNCSystem, output_path: str, days_ahead: int = 7) -> None:
    rncs = [dict(r) for r in system.list_rncs()]
    actions = [dict(a) for a in system.list_all_actions()]
    evidences = [dict(e) for e in system.list_evidences()]
    alerts = {k: [dict(v) for v in vals] for k, vals in system.get_alerts(days_ahead).items()}

    def table(headers: list[str], rows: list[list[str]]) -> str:
        head = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
        body = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
        if not body:
            body = f"<tr><td colspan='{len(headers)}'><em>Sem registros</em></td></tr>"
        return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"

    rnc_rows = [
        [
            str(r["id"]),
            html.escape(r["cliente"]),
            html.escape(r["rastreabilidade"]),
            html.escape(r["codigo_agro"]),
            html.escape(r["codigo_terceiro"]),
            "Sim" if r["procedente"] else "Não",
            "Sim" if r["formal"] else "Não",
            html.escape(r["prazo_resposta"]),
            _status_badge(r["status"]),
        ]
        for r in rncs
    ]
    action_rows = [
        [
            str(a["id"]),
            str(a["rnc_id"]),
            html.escape(a["cliente"]),
            html.escape(a["descricao"]),
            html.escape(a["responsavel"]),
            html.escape(a["prazo"]),
            _status_badge(a["status"]),
        ]
        for a in actions
    ]
    evidence_rows = [
        [
            str(e["id"]),
            html.escape(e["target_type"]),
            str(e["target_id"]),
            html.escape(e["descricao"]),
            f"<code>{html.escape(e['file_path'])}</code>",
            html.escape(e["data_anexo"]),
        ]
        for e in evidences
    ]

    html_content = f"""<!doctype html>
<html lang='pt-BR'>
<head>
  <meta charset='utf-8' />
  <meta name='viewport' content='width=device-width, initial-scale=1' />
  <title>Painel de RNCs</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; color: #1f2937; }}
    h1, h2 {{ margin-bottom: 8px; }}
    .muted {{ color: #6b7280; margin-top: 0; }}
    .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin: 20px 0; }}
    .card {{ border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; background: #f9fafb; }}
    .big {{ font-size: 28px; font-weight: 700; margin: 4px 0 0; }}
    table {{ width: 100%; border-collapse: collapse; margin: 10px 0 24px; }}
    th, td {{ border: 1px solid #e5e7eb; padding: 8px; text-align: left; vertical-align: top; }}
    th {{ background: #f3f4f6; }}
    .grid2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
    .box {{ border:1px solid #e5e7eb; border-radius:6px; padding:8px; background:#fff; }}
  </style>
</head>
<body>
  <h1>Painel de Gestão de RNCs</h1>
  <p class='muted'>Gerado em {html.escape(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}</p>

  <div class='cards'>
    <div class='card'><strong>Total de RNCs</strong><p class='big'>{len(rncs)}</p></div>
    <div class='card'><strong>RNCs abertas</strong><p class='big'>{sum(1 for r in rncs if r['status'] == 'aberta')}</p></div>
    <div class='card'><strong>Ações em aberto</strong><p class='big'>{sum(1 for a in actions if a['status'] == 'aberta')}</p></div>
    <div class='card'><strong>Evidências</strong><p class='big'>{len(evidences)}</p></div>
  </div>

  <h2>RNCs</h2>
  {table(['ID', 'Cliente', 'Rastreabilidade', 'Código Agro', 'Código Terceiro', 'Procedente', 'Formal', 'Prazo resposta', 'Status'], rnc_rows)}

  <h2>Ishikawa (6M) por RNC</h2>
  {''.join(
      f"<h3>RNC #{r['id']} - {html.escape(r['cliente'])}</h3>"
      f"<div class='grid2'>"
      f"<div class='box'><strong>Método</strong><br>{html.escape(r.get('ishikawa_metodo','')) or '<em>Não preenchido</em>'}</div>"
      f"<div class='box'><strong>Máquina</strong><br>{html.escape(r.get('ishikawa_maquina','')) or '<em>Não preenchido</em>'}</div>"
      f"<div class='box'><strong>Mão de obra</strong><br>{html.escape(r.get('ishikawa_mao_de_obra','')) or '<em>Não preenchido</em>'}</div>"
      f"<div class='box'><strong>Material</strong><br>{html.escape(r.get('ishikawa_material','')) or '<em>Não preenchido</em>'}</div>"
      f"<div class='box'><strong>Medição</strong><br>{html.escape(r.get('ishikawa_medicao','')) or '<em>Não preenchido</em>'}</div>"
      f"<div class='box'><strong>Meio ambiente</strong><br>{html.escape(r.get('ishikawa_meio_ambiente','')) or '<em>Não preenchido</em>'}</div>"
      f"</div>"
      for r in rncs
  ) or '<p><em>Sem RNCs para exibir Ishikawa.</em></p>'}

  <h2>Ações corretivas</h2>
  {table(['ID', 'RNC', 'Cliente', 'Descrição', 'Responsável', 'Prazo', 'Status'], action_rows)}

  <h2>Evidências anexadas</h2>
  {table(['ID', 'Tipo', 'ID alvo', 'Descrição', 'Arquivo', 'Data'], evidence_rows)}

  <h2>Alertas (próximos {days_ahead} dias)</h2>
  <ul>
    <li>Respostas vencidas: <strong>{len(alerts['respostas_vencidas'])}</strong></li>
    <li>Respostas próximas: <strong>{len(alerts['respostas_proximas'])}</strong></li>
    <li>Ações vencidas: <strong>{len(alerts['acoes_vencidas'])}</strong></li>
    <li>Ações próximas: <strong>{len(alerts['acoes_proximas'])}</strong></li>
  </ul>
</body>
</html>
"""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html_content, encoding="utf-8")


def generate_pdf_report(system: RNCSystem, output_path: str, days_ahead: int = 7) -> None:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError as exc:
        raise RuntimeError(
            "Para exportar PDF, instale a dependência: pip install reportlab"
        ) from exc

    rncs = [dict(r) for r in system.list_rncs()]
    actions = [dict(a) for a in system.list_all_actions()]
    evidences = [dict(e) for e in system.list_evidences()]
    alerts = system.get_alerts(days_ahead)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    c = canvas.Canvas(str(out), pagesize=A4)
    width, height = A4
    y = height - 40

    def write_line(text: str, step: int = 16) -> None:
        nonlocal y
        if y < 40:
            c.showPage()
            y = height - 40
        c.drawString(40, y, text[:130])
        y -= step

    write_line("Relatório de Gestão de RNCs")
    write_line(f"Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    write_line("")
    write_line(f"Total de RNCs: {len(rncs)}")
    write_line(f"Ações corretivas: {len(actions)}")
    write_line(f"Evidências anexadas: {len(evidences)}")
    write_line(
        "Alertas: "
        f"resp vencidas={len(alerts['respostas_vencidas'])}, "
        f"resp próximas={len(alerts['respostas_proximas'])}, "
        f"ações vencidas={len(alerts['acoes_vencidas'])}, "
        f"ações próximas={len(alerts['acoes_proximas'])}"
    )

    write_line("")
    write_line("RNCs:")
    for r in rncs:
        write_line(
            f"- #{r['id']} {r['cliente']} | {r['codigo_agro']} | prazo {r['prazo_resposta']} | status {r['status']}"
        )

    write_line("")
    write_line("Ações corretivas:")
    for a in actions:
        write_line(
            f"- #{a['id']} RNC {a['rnc_id']} | {a['responsavel']} | prazo {a['prazo']} | status {a['status']}"
        )

    write_line("")
    write_line("Evidências:")
    for e in evidences:
        write_line(
            f"- #{e['id']} {e['target_type']} {e['target_id']} | {e['descricao']} | {e['file_path']}"
        )

    c.save()


def parse_date(value: str) -> date:
    return datetime.strptime(value, DATE_FMT).date()


def bool_flag(value: str) -> bool:
    if value.lower() in {"sim", "s", "true", "1", "yes", "y"}:
        return True
    if value.lower() in {"nao", "não", "n", "false", "0", "no"}:
        return False
    raise argparse.ArgumentTypeError("Use sim/nao (ou true/false) para os campos booleanos.")


def print_rows(rows: Iterable[sqlite3.Row], title: str) -> None:
    print(f"\n{title}")
    print("-" * len(title))
    found = False
    for row in rows:
        found = True
        print(dict(row))
    if not found:
        print("(nenhum resultado)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sistema de gestão de RNCs")
    parser.add_argument("--db", default="rnc.db", help="Caminho do arquivo SQLite")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Inicializa/atualiza o banco")

    rnc = sub.add_parser("nova-rnc", help="Cadastra nova RNC")
    rnc.add_argument("--cliente", required=True)
    rnc.add_argument("--rastreabilidade", required=True)
    rnc.add_argument("--codigo-agro", required=True)
    rnc.add_argument("--codigo-terceiro", required=True)
    rnc.add_argument("--procedente", required=True, type=bool_flag)
    rnc.add_argument("--formal", required=True, type=bool_flag)
    rnc.add_argument("--observacoes", required=True)
    rnc.add_argument("--data", required=True, type=parse_date)
    rnc.add_argument("--prazo-resposta", required=True, type=parse_date)

    ish = sub.add_parser("ishikawa", help="Preenche causas Ishikawa (6M) da RNC")
    ish.add_argument("--rnc-id", required=True, type=int)
    ish.add_argument("--metodo", default="")
    ish.add_argument("--maquina", default="")
    ish.add_argument("--mao-de-obra", default="")
    ish.add_argument("--material", default="")
    ish.add_argument("--medicao", default="")
    ish.add_argument("--meio-ambiente", default="")

    lst = sub.add_parser("listar-rncs", help="Lista RNCs")
    lst.add_argument("--status", choices=["aberta", "encerrada"])

    busca = sub.add_parser("rastrear", help="Busca por cliente/códigos")
    busca.add_argument("--termo", required=True)

    acao = sub.add_parser("nova-acao", help="Adiciona ação corretiva")
    acao.add_argument("--rnc-id", required=True, type=int)
    acao.add_argument("--descricao", required=True)
    acao.add_argument("--responsavel", required=True)
    acao.add_argument("--prazo", required=True, type=parse_date)

    conclui = sub.add_parser("concluir-acao", help="Conclui ação corretiva")
    conclui.add_argument("--acao-id", required=True, type=int)
    conclui.add_argument("--data-conclusao", type=parse_date)

    fecha = sub.add_parser("encerrar-rnc", help="Encerra RNC")
    fecha.add_argument("--rnc-id", required=True, type=int)
    fecha.add_argument("--data-encerramento", type=parse_date)

    evr = sub.add_parser("anexar-evidencia-rnc", help="Anexa evidência à RNC")
    evr.add_argument("--rnc-id", required=True, type=int)
    evr.add_argument("--arquivo", required=True)
    evr.add_argument("--descricao", required=True)

    eva = sub.add_parser("anexar-evidencia-acao", help="Anexa evidência à ação corretiva")
    eva.add_argument("--acao-id", required=True, type=int)
    eva.add_argument("--arquivo", required=True)
    eva.add_argument("--descricao", required=True)

    lev = sub.add_parser("listar-evidencias", help="Lista evidências")
    lev.add_argument("--tipo", choices=["rnc", "acao"])
    lev.add_argument("--id", type=int)

    alert = sub.add_parser("alertas", help="Exibe alertas")
    alert.add_argument("--dias", type=int, default=3)

    htmlp = sub.add_parser("exportar-html", help="Gera painel HTML")
    htmlp.add_argument("--saida", required=True)
    htmlp.add_argument("--dias", type=int, default=7)

    pdfp = sub.add_parser("exportar-pdf", help="Gera relatório PDF")
    pdfp.add_argument("--saida", required=True)
    pdfp.add_argument("--dias", type=int, default=7)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    system = RNCSystem(args.db)

    if args.command == "init":
        system.init_db()
        print(f"Banco inicializado em: {args.db}")
        return

    system.init_db()

    if args.command == "nova-rnc":
        rnc_id = system.add_rnc(
            RNCInput(
                cliente=args.cliente,
                rastreabilidade=args.rastreabilidade,
                codigo_agro=args.codigo_agro,
                codigo_terceiro=args.codigo_terceiro,
                procedente=args.procedente,
                formal=args.formal,
                observacoes=args.observacoes,
                data_registro=args.data,
                prazo_resposta=args.prazo_resposta,
            )
        )
        print(f"RNC criada com ID {rnc_id}")
    elif args.command == "ishikawa":
        system.update_ishikawa(
            args.rnc_id,
            IshikawaInput(
                metodo=args.metodo,
                maquina=args.maquina,
                mao_de_obra=args.mao_de_obra,
                material=args.material,
                medicao=args.medicao,
                meio_ambiente=args.meio_ambiente,
            ),
        )
        print(f"Ishikawa atualizado para RNC {args.rnc_id}")
    elif args.command == "listar-rncs":
        print_rows(system.list_rncs(args.status), "RNCs")
    elif args.command == "rastrear":
        print_rows(system.traceability_search(args.termo), f"Busca: {args.termo}")
    elif args.command == "nova-acao":
        action_id = system.add_corrective_action(
            CorrectiveActionInput(
                rnc_id=args.rnc_id,
                descricao=args.descricao,
                responsavel=args.responsavel,
                prazo=args.prazo,
            )
        )
        print(f"Ação corretiva criada com ID {action_id}")
    elif args.command == "concluir-acao":
        system.close_corrective_action(args.acao_id, args.data_conclusao)
        print(f"Ação corretiva {args.acao_id} concluída")
    elif args.command == "encerrar-rnc":
        system.close_rnc(args.rnc_id, args.data_encerramento)
        print(f"RNC {args.rnc_id} encerrada")
    elif args.command == "anexar-evidencia-rnc":
        evid = system.add_evidence("rnc", args.rnc_id, args.arquivo, args.descricao)
        print(f"Evidência {evid} anexada à RNC {args.rnc_id}")
    elif args.command == "anexar-evidencia-acao":
        evid = system.add_evidence("acao", args.acao_id, args.arquivo, args.descricao)
        print(f"Evidência {evid} anexada à ação {args.acao_id}")
    elif args.command == "listar-evidencias":
        print_rows(system.list_evidences(args.tipo, args.id), "Evidências")
    elif args.command == "alertas":
        alerts = system.get_alerts(args.dias)
        print_rows(alerts["respostas_vencidas"], "RNCs com resposta vencida")
        print_rows(alerts["respostas_proximas"], "RNCs com prazo de resposta próximo")
        print_rows(alerts["acoes_vencidas"], "Ações corretivas vencidas")
        print_rows(alerts["acoes_proximas"], "Ações corretivas próximas do vencimento")
    elif args.command == "exportar-html":
        generate_html_report(system, args.saida, args.dias)
        print(f"Relatório HTML gerado em: {args.saida}")
    elif args.command == "exportar-pdf":
        generate_pdf_report(system, args.saida, args.dias)
        print(f"Relatório PDF gerado em: {args.saida}")


if __name__ == "__main__":
    main()
