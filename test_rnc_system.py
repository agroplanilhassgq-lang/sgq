import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from rnc_system import CorrectiveActionInput, IshikawaInput, RNCInput, RNCSystem


class RNCSystemTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.db_path = str(Path(self.tmpdir.name) / "test.db")
        self.system = RNCSystem(self.db_path)
        self.system.init_db()

    def _create_rnc(self) -> int:
        return self.system.add_rnc(
            RNCInput(
                cliente="Cliente Teste",
                rastreabilidade="Lote-001",
                codigo_agro="AG-001",
                codigo_terceiro="T-001",
                procedente=True,
                formal=False,
                observacoes="Observação",
                data_registro=date.today(),
                prazo_resposta=date.today() + timedelta(days=3),
            )
        )

    def test_create_rnc_and_corrective_action(self) -> None:
        rnc_id = self._create_rnc()
        action_id = self.system.add_corrective_action(
            CorrectiveActionInput(
                rnc_id=rnc_id,
                descricao="Ação de teste",
                responsavel="Maria",
                prazo=date.today() + timedelta(days=2),
            )
        )

        rncs = self.system.list_rncs()
        actions = self.system.list_all_actions()

        self.assertEqual(1, len(rncs))
        self.assertEqual(rnc_id, rncs[0]["id"])
        self.assertEqual(1, len(actions))
        self.assertEqual(action_id, actions[0]["id"])

    def test_update_ishikawa(self) -> None:
        rnc_id = self._create_rnc()
        self.system.update_ishikawa(
            rnc_id,
            IshikawaInput(
                metodo="Método A",
                maquina="Máquina B",
                mao_de_obra="Mão de obra C",
                material="Material D",
                medicao="Medição E",
                meio_ambiente="Ambiente F",
            ),
        )

        row = self.system.list_rncs()[0]
        self.assertEqual("Método A", row["ishikawa_metodo"])
        self.assertEqual("Máquina B", row["ishikawa_maquina"])

    def test_attach_and_list_evidences(self) -> None:
        rnc_id = self._create_rnc()
        action_id = self.system.add_corrective_action(
            CorrectiveActionInput(
                rnc_id=rnc_id,
                descricao="Ação",
                responsavel="João",
                prazo=date.today() + timedelta(days=4),
            )
        )

        evid_file = Path(self.tmpdir.name) / "evid.txt"
        evid_file.write_text("ok", encoding="utf-8")

        ev_rnc = self.system.add_evidence("rnc", rnc_id, str(evid_file), "evid rnc")
        ev_action = self.system.add_evidence("acao", action_id, str(evid_file), "evid acao")

        all_evidences = self.system.list_evidences()
        self.assertEqual(2, len(all_evidences))
        self.assertIn(ev_rnc, {all_evidences[0]["id"], all_evidences[1]["id"]})
        self.assertIn(ev_action, {all_evidences[0]["id"], all_evidences[1]["id"]})

    def test_generate_html_report(self) -> None:
        rnc_id = self._create_rnc()
        self.system.update_ishikawa(rnc_id, IshikawaInput(metodo="Teste"))

        output = Path(self.tmpdir.name) / "painel.html"
        from rnc_system import generate_html_report

        generate_html_report(self.system, str(output), days_ahead=7)

        self.assertTrue(output.exists())
        content = output.read_text(encoding="utf-8")
        self.assertIn("Painel de Gestão de RNCs", content)


if __name__ == "__main__":
    unittest.main()
