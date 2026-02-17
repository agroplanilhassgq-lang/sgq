const STORAGE_KEY = "sgq-rncs-v1";

const state = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{"rncs":[],"acoes":[]}');

const rncForm = document.getElementById('rnc-form');
const acaoForm = document.getElementById('acao-form');
const rncBody = document.getElementById('rnc-body');
const acoesBody = document.getElementById('acoes-body');
const alertasList = document.getElementById('alertas');
const acaoRnc = document.getElementById('acao-rnc');

const save = () => localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
const todayISO = () => new Date().toISOString().slice(0, 10);

function createId(prefix) {
  return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 9999)}`;
}

function renderRncOptions() {
  acaoRnc.innerHTML = '<option value="">Selecione RNC</option>' + state.rncs
    .map(r => `<option value="${r.id}">${r.id} - ${r.cliente}</option>`)
    .join('');
}

function renderRncs() {
  rncBody.innerHTML = state.rncs.map(r => {
    const eightD = r.eightD && Object.values(r.eightD).some(Boolean) ? 'Sim' : 'Não';
    const anexos = r.anexos?.length ? `<ul>${r.anexos.map(a => `<li>${a.nome}</li>`).join('')}</ul>` : '-';
    return `<tr>
      <td>${r.id}</td>
      <td>${r.rastreabilidade}</td>
      <td>${r.cliente}</td>
      <td>${r.prazoResposta}</td>
      <td>${r.procedente}</td>
      <td>${anexos}</td>
      <td>${eightD}</td>
    </tr>`;
  }).join('');
}

function renderAcoes() {
  acoesBody.innerHTML = state.acoes.map(a => {
    const prazoVencido = a.prazo < todayISO() && a.status === 'Aberta';
    return `<tr>
      <td>${a.rncId}</td>
      <td>${a.descricao}</td>
      <td>${a.responsavel}</td>
      <td class="${prazoVencido ? 'alerta-vencido' : ''}">${a.prazo}</td>
      <td><span class="tag ${a.status === 'Aberta' ? 'aberta' : 'concluida'}">${a.status}</span></td>
      <td><button data-id="${a.id}" class="toggle-status">${a.status === 'Aberta' ? 'Concluir' : 'Reabrir'}</button></td>
    </tr>`;
  }).join('');
}

function renderAlertas() {
  const alertas = [];

  state.rncs.forEach(r => {
    if (r.prazoResposta < todayISO()) {
      alertas.push(`RNC ${r.id} (${r.cliente}) com prazo de resposta vencido.`);
    }
  });

  state.acoes.forEach(a => {
    if (a.status === 'Aberta' && a.prazo < todayISO()) {
      alertas.push(`Ação corretiva em atraso (${a.responsavel}) na ${a.rncId}.`);
    }
  });

  alertasList.innerHTML = alertas.length ? alertas.map(a => `<li>${a}</li>`).join('') : '<li>Sem alertas no momento.</li>';
}

function renderDashboard() {
  const total = state.rncs.length;
  const procedentes = state.rncs.filter(r => r.procedente === 'Sim').length;
  const vencidas = state.rncs.filter(r => r.prazoResposta < todayISO()).length;
  const acoesAbertas = state.acoes.filter(a => a.status === 'Aberta').length;

  document.getElementById('kpi-total').textContent = total;
  document.getElementById('kpi-procedentes').textContent = procedentes;
  document.getElementById('kpi-prazo').textContent = vencidas;
  document.getElementById('kpi-acoes').textContent = acoesAbertas;

  const canvas = document.getElementById('cliente-chart');
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const porCliente = state.rncs.reduce((acc, item) => {
    acc[item.cliente] = (acc[item.cliente] || 0) + 1;
    return acc;
  }, {});

  const entries = Object.entries(porCliente);
  if (!entries.length) {
    ctx.fillText('Sem dados para gráfico.', 20, 40);
    return;
  }

  const max = Math.max(...entries.map(([, totalRnc]) => totalRnc));
  const barW = Math.max(40, (canvas.width - 60) / entries.length - 20);

  entries.forEach(([cliente, qtd], i) => {
    const x = 30 + i * (barW + 20);
    const h = (qtd / max) * 180;
    const y = 240 - h;
    ctx.fillStyle = '#1e88e5';
    ctx.fillRect(x, y, barW, h);
    ctx.fillStyle = '#1f2d3d';
    ctx.fillText(cliente.slice(0, 11), x, 258);
    ctx.fillText(String(qtd), x + barW / 2 - 4, y - 6);
  });
}

function render() {
  renderRncOptions();
  renderRncs();
  renderAcoes();
  renderAlertas();
  renderDashboard();
  save();
}

rncForm.addEventListener('submit', (e) => {
  e.preventDefault();
  const fd = new FormData(rncForm);
  const files = document.getElementById('anexos').files;

  const rnc = {
    id: createId('RNC'),
    rastreabilidade: fd.get('rastreabilidade'),
    codigoAgro: fd.get('codigoAgro'),
    codigoTerceiro: fd.get('codigoTerceiro'),
    quantidade: Number(fd.get('quantidade')),
    cliente: fd.get('cliente'),
    planta: fd.get('planta'),
    contencao: fd.get('contencao'),
    prazoResposta: fd.get('prazoResposta'),
    procedente: fd.get('procedente'),
    formar: fd.get('formar'),
    observacoes: fd.get('observacoes'),
    anexos: Array.from(files).map(file => ({ nome: file.name, tipo: file.type, tamanho: file.size })),
    eightD: {
      d1: fd.get('d1'), d2: fd.get('d2'), d3: fd.get('d3'), d4: fd.get('d4'),
      d5: fd.get('d5'), d6: fd.get('d6'), d7: fd.get('d7'), d8: fd.get('d8')
    }
  };

  state.rncs.push(rnc);
  rncForm.reset();
  render();
});

acaoForm.addEventListener('submit', (e) => {
  e.preventDefault();
  const acao = {
    id: createId('ACAO'),
    rncId: document.getElementById('acao-rnc').value,
    descricao: document.getElementById('acao-desc').value,
    responsavel: document.getElementById('acao-resp').value,
    prazo: document.getElementById('acao-prazo').value,
    status: 'Aberta'
  };

  if (!acao.rncId) return;
  state.acoes.push(acao);
  acaoForm.reset();
  render();
});

acoesBody.addEventListener('click', (e) => {
  const button = e.target.closest('.toggle-status');
  if (!button) return;
  const action = state.acoes.find(a => a.id === button.dataset.id);
  if (!action) return;
  action.status = action.status === 'Aberta' ? 'Concluída' : 'Aberta';
  render();
});

render();
