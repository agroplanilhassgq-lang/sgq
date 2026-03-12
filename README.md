# Sistema de Gestão de RNCs (Python)

Sistema em Python para controle de **RNCs** com:

- Emissão de alertas por prazo.
- Cadastro de cliente e rastreabilidade.
- Código agro e código terceiro.
- Campos de procedente/formal.
- Observações, data e prazo de resposta.
- Controle de ações corretivas com prazo e responsável.
- **Ishikawa (6M)** por RNC.
- **Anexos de evidências** para RNC e ações corretivas.
- Exportação de relatório em **HTML e PDF**.

## Requisitos

- Python 3.10+
- SQLite (já incluído no Python)
- Para PDF: `reportlab`


## Passo a passo (iniciante total)

Se você **nunca usou Python**, siga exatamente estes passos.

### 1) Onde colocar o código

Crie uma pasta no seu computador, por exemplo:

- **Windows:** `C:\rnc`
- **macOS/Linux:** `~/rnc`

Dentro dessa pasta, coloque estes arquivos:

- `rnc_system.py`
- `README.md`

> Dica: se você baixou este projeto do Git, esses arquivos já virão na pasta.

### 2) Instalar Python

- Acesse: https://www.python.org/downloads/
- Instale a versão 3.10 ou superior.
- No Windows, marque a opção **“Add Python to PATH”** durante a instalação.

### 3) Abrir o terminal na pasta do projeto

- **Windows:** abra o Prompt de Comando e rode:

```bat
cd C:\rnc
```

- **macOS/Linux:** abra o Terminal e rode:

```bash
cd ~/rnc
```

### 4) (Opcional) Criar ambiente virtual

- **Windows:**

```bat
python -m venv .venv
.venv\Scripts\activate
```

- **macOS/Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 5) Inicializar o sistema

```bash
python3 rnc_system.py --db dados/rnc.db init
```

> No Windows, se `python3` não funcionar, use `python`.

### 6) Cadastrar primeira RNC (teste)

```bash
python3 rnc_system.py --db dados/rnc.db nova-rnc \
  --cliente "Cliente Teste" \
  --rastreabilidade "Lote-001" \
  --codigo-agro "AG-001" \
  --codigo-terceiro "T-001" \
  --procedente sim \
  --formal sim \
  --observacoes "Primeiro teste" \
  --data 2026-03-12 \
  --prazo-resposta 2026-03-20
```

### 7) Ver se funcionou

```bash
python3 rnc_system.py --db dados/rnc.db listar-rncs
```

Se aparecer uma lista com sua RNC, está tudo certo.

### 8) Gerar painel visual (HTML)

```bash
python3 rnc_system.py --db dados/rnc.db exportar-html --saida dados/painel_rnc.html --dias 7
```

Depois abra o arquivo `dados/painel_rnc.html` com dois cliques no navegador.

### 9) (Opcional) Exportar PDF

Instale dependência:

```bash
pip install reportlab
```

E exporte:

```bash
python3 rnc_system.py --db dados/rnc.db exportar-pdf --saida dados/relatorio_rnc.pdf --dias 7
```


## Rodar localmente na sua máquina

1. Salve os arquivos (`rnc_system.py` e `README.md`) em uma pasta.
2. (Opcional) crie um ambiente virtual:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. (Opcional, para PDF) instale dependência:

```bash
pip install reportlab
```

4. Inicialize o banco:

```bash
python3 rnc_system.py --db dados/rnc.db init
```

## Uso rápido

### 1) Cadastrar RNC

```bash
python3 rnc_system.py --db dados/rnc.db nova-rnc \
  --cliente "Cliente X" \
  --rastreabilidade "Lote 2026-001" \
  --codigo-agro "AGRO-7788" \
  --codigo-terceiro "T-900" \
  --procedente sim \
  --formal sim \
  --observacoes "Desvio identificado no recebimento" \
  --data 2026-03-12 \
  --prazo-resposta 2026-03-20
```

### 2) Preencher Ishikawa (6M)

```bash
python3 rnc_system.py --db dados/rnc.db ishikawa \
  --rnc-id 1 \
  --metodo "Instrução de trabalho desatualizada" \
  --maquina "Sensor descalibrado" \
  --mao-de-obra "Treinamento insuficiente" \
  --material "Matéria-prima fora da especificação" \
  --medicao "Falta de plano de calibração" \
  --meio-ambiente "Umidade elevada na área"
```

### 3) Adicionar ação corretiva

```bash
python3 rnc_system.py --db dados/rnc.db nova-acao \
  --rnc-id 1 \
  --descricao "Treinamento da equipe de recebimento" \
  --responsavel "Ana" \
  --prazo 2026-03-18
```

### 4) Anexar evidência da RNC

```bash
python3 rnc_system.py --db dados/rnc.db anexar-evidencia-rnc \
  --rnc-id 1 \
  --arquivo ./evidencias/foto_rnc_1.jpg \
  --descricao "Foto da não conformidade no recebimento"
```

### 5) Anexar evidência da ação corretiva

```bash
python3 rnc_system.py --db dados/rnc.db anexar-evidencia-acao \
  --acao-id 1 \
  --arquivo ./evidencias/checklist_treinamento.pdf \
  --descricao "Lista de presença do treinamento"
```

### 6) Visualizar dados

```bash
python3 rnc_system.py --db dados/rnc.db listar-rncs
python3 rnc_system.py --db dados/rnc.db listar-evidencias
python3 rnc_system.py --db dados/rnc.db alertas --dias 5
```

### 7) Exportar HTML (abrir no navegador)

```bash
python3 rnc_system.py --db dados/rnc.db exportar-html --saida dados/painel_rnc.html --dias 7
```

Depois abra `dados/painel_rnc.html` no navegador.

### 8) Exportar PDF

```bash
python3 rnc_system.py --db dados/rnc.db exportar-pdf --saida dados/relatorio_rnc.pdf --dias 7
```


## Como testar

### Teste automatizado

```bash
python3 -m unittest -v
```

### Teste manual rápido (fluxo completo)

```bash
mkdir -p /tmp/rnc_ev
echo "foto" > /tmp/rnc_ev/foto.jpg
echo "check" > /tmp/rnc_ev/checklist.pdf

python3 rnc_system.py --db /tmp/rnc_full.db init
python3 rnc_system.py --db /tmp/rnc_full.db nova-rnc --cliente "Cliente C" --rastreabilidade "Lote 3" --codigo-agro "AG-3" --codigo-terceiro "T-3" --procedente sim --formal nao --observacoes "Teste completo" --data 2026-03-12 --prazo-resposta 2026-03-25
python3 rnc_system.py --db /tmp/rnc_full.db ishikawa --rnc-id 1 --metodo "sem padrão" --maquina "falha sensor" --mao-de-obra "sem treinamento" --material "fora especificação" --medicao "sem calibração" --meio-ambiente "poeira"
python3 rnc_system.py --db /tmp/rnc_full.db nova-acao --rnc-id 1 --descricao "Treinar equipe" --responsavel "Joana" --prazo 2026-03-20
python3 rnc_system.py --db /tmp/rnc_full.db anexar-evidencia-rnc --rnc-id 1 --arquivo /tmp/rnc_ev/foto.jpg --descricao "foto da rnc"
python3 rnc_system.py --db /tmp/rnc_full.db anexar-evidencia-acao --acao-id 1 --arquivo /tmp/rnc_ev/checklist.pdf --descricao "ata de treinamento"
python3 rnc_system.py --db /tmp/rnc_full.db exportar-html --saida /tmp/rnc_ev/painel.html --dias 10
python3 rnc_system.py --db /tmp/rnc_full.db listar-evidencias
```

> Para PDF, rode `pip install reportlab` e depois: `python3 rnc_system.py --db /tmp/rnc_full.db exportar-pdf --saida /tmp/rnc_ev/relatorio.pdf --dias 10`.

## Comandos principais

- `init`
- `nova-rnc`
- `ishikawa`
- `nova-acao`
- `concluir-acao`
- `encerrar-rnc`
- `anexar-evidencia-rnc`
- `anexar-evidencia-acao`
- `listar-evidencias`
- `listar-rncs`
- `rastrear`
- `alertas`
- `exportar-html`
- `exportar-pdf`
