/* ============================================================
   DASHBOARD INDUSTRIAL AMT — dashboard.js
   ============================================================ */

'use strict';

// ── CHART REGISTRY ──────────────────────────────────────────
const charts = {};

// ── HELPERS ─────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const fmt = n => (n == null ? '0' : Number(n).toLocaleString('pt-BR'));
const fmtH = h => `${Number(h || 0).toFixed(1)}h`;
const fmtPct = p => `${Number(p || 0).toFixed(1)}%`;

function animateCounter(el, target, decimals = 0, suffix = '') {
  if (!el) return;
  const start = 0, duration = 1200;
  const startTime = performance.now();
  const step = now => {
    const elapsed = now - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const ease = 1 - Math.pow(1 - progress, 3);
    const val = start + (target - start) * ease;
    el.textContent = decimals > 0
      ? val.toFixed(decimals) + suffix
      : Math.round(val).toLocaleString('pt-BR') + suffix;
    if (progress < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

// ── CLOCK ───────────────────────────────────────────────────
function updateClock() {
  const now = new Date();
  const hh = String(now.getHours()).padStart(2,'0');
  const mm = String(now.getMinutes()).padStart(2,'0');
  const ss = String(now.getSeconds()).padStart(2,'0');
  const ct = $('clock-time');
  if (ct) ct.textContent = `${hh}:${mm}:${ss}`;

  const dias = ['Domingo','Segunda','Terça','Quarta','Quinta','Sexta','Sábado'];
  const meses = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'];
  const cd = $('clock-date');
  if (cd) cd.textContent = `${dias[now.getDay()]}, ${now.getDate()} ${meses[now.getMonth()]} ${now.getFullYear()}`;
}
setInterval(updateClock, 1000);
updateClock();

// ── SIDEBAR TOGGLE ──────────────────────────────────────────
const sidebar = document.getElementById('sidebar');
const mainWrap = document.querySelector('.main-wrap');
let sidebarOpen = true;

document.getElementById('sidebarToggle')?.addEventListener('click', () => {
  sidebarOpen = !sidebarOpen;
  sidebar.classList.toggle('collapsed', !sidebarOpen);
  mainWrap.classList.toggle('expanded', !sidebarOpen);
});

// Active nav items on scroll
const sections = document.querySelectorAll('.section-block[id]');
const navItems = document.querySelectorAll('.nav-item');
window.addEventListener('scroll', () => {
  let current = '';
  sections.forEach(s => {
    if (window.scrollY >= s.offsetTop - 100) current = s.id;
  });
  navItems.forEach(n => {
    n.classList.toggle('active', n.getAttribute('href') === `#${current}`);
  });
}, { passive: true });

navItems.forEach(n => {
  n.addEventListener('click', () => {
    navItems.forEach(x => x.classList.remove('active'));
    n.classList.add('active');
  });
});

// ── DB STATUS ───────────────────────────────────────────────
async function checkStatus() {
  try {
    const r = await fetch('/api/status');
    const d = await r.json();
    const online = d.status === 'ok';
    setStatus(online);
  } catch { setStatus(false); }
}

function setStatus(online) {
  const pill = $('db-status-pill');
  const dot  = $('pulse-dot');
  const label = $('db-status-label');
  const sbDot = $('sb-status-dot');
  const sbTxt = $('sb-status-text');

  if (online) {
    pill?.classList.add('online'); pill?.classList.remove('error');
    dot?.classList.add('online'); dot?.classList.remove('error');
    if (label) label.textContent = 'Banco de Dados Conectado';
    sbDot?.classList.add('online'); sbDot?.classList.remove('error');
    if (sbTxt) sbTxt.textContent = 'BD Online';
  } else {
    pill?.classList.remove('online'); pill?.classList.add('error');
    dot?.classList.remove('online'); dot?.classList.add('error');
    if (label) label.textContent = 'Erro na Conexão';
    sbDot?.classList.remove('online'); sbDot?.classList.add('error');
    if (sbTxt) sbTxt.textContent = 'BD Offline';
  }
}

// ── FILTER PARAMS ───────────────────────────────────────────
function getFilterParams() {
  const params = new URLSearchParams();
  const v = id => $(id)?.value;
  if (v('f-dt-ini'))  params.set('dt_ini', v('f-dt-ini'));
  if (v('f-dt-fim'))  params.set('dt_fim', v('f-dt-fim'));
  const fields = { 'f-turno':'turno','f-maquina':'maquina','f-operador':'operador','f-produto':'produto','f-processo':'processo' };
  Object.entries(fields).forEach(([id, key]) => {
    const val = v(id);
    if (val && val !== 'todos') params.set(key, val);
  });
  return params.toString() ? '?' + params.toString() : '';
}

// ── LOAD FILTROS ─────────────────────────────────────────────
async function loadFiltros() {
  try {
    const r = await fetch('/api/filtros');
    const d = await r.json();
    const map = {
      'f-turno': d.turnos, 'f-maquina': d.maquinas,
      'f-operador': d.operadores, 'f-produto': d.produtos, 'f-processo': d.processos
    };
    const defaults = {
      'f-turno': 'Todos', 'f-maquina': 'Todas',
      'f-operador': 'Todos', 'f-produto': 'Todos', 'f-processo': 'Todos'
    };
    Object.entries(map).forEach(([id, items]) => {
      const sel = $(id);
      if (!sel) return;
      sel.innerHTML = `<option value="todos">${defaults[id]}</option>`;
      (items || []).forEach(v => {
        const opt = document.createElement('option');
        opt.value = v; opt.textContent = v;
        sel.appendChild(opt);
      });
    });
  } catch(e) { console.warn('Filtros error', e); }
}

// ── CARDS ────────────────────────────────────────────────────
async function loadResumo(qs='') {
  try {
    const r = await fetch('/api/resumo' + qs);
    const d = await r.json();

    animateCounter($('c-total'),    d.producao_total || 0);
    animateCounter($('c-boas'),     d.pecas_boas || 0);
    animateCounter($('c-perdas'),   d.perdas || 0);
    animateCounter($('c-pct-perda'), +(d.pct_perda||0), 1, '%');
    animateCounter($('c-meta'),     d.meta || 0);
    animateCounter($('c-maq'),      d.maquinas_ativas || 0);
    animateCounter($('c-apto'),     d.apontamentos_dia || 0);

    const tp = $('c-tp');
    if (tp) tp.textContent = fmtH(d.tempo_produzindo);
    const tpar = $('c-tpar');
    if (tpar) tpar.textContent = fmtH(d.tempo_parado);
    const ef = $('c-ef');
    if (ef) ef.textContent = fmtPct(d.eficiencia);

    const barEl = $('bar-ef');
    if (barEl) {
      setTimeout(() => { barEl.style.width = Math.min(100, d.eficiencia || 0) + '%'; }, 300);
    }

    const lu = $('last-update');
    if (lu) {
      const now = new Date();
      lu.textContent = `Última atualização: ${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}:${String(now.getSeconds()).padStart(2,'0')}`;
    }
  } catch(e) { console.error('resumo error', e); }
}

// ── CHART FACTORY ────────────────────────────────────────────
const BLUE_PALETTE = [
  '#1D559E','#2a6dd9','#123B75','#3b82f6','#0ea5e9',
  '#0284c7','#0369a1','#075985','#0c4a6e','#BDD7EE'
];
const BLUE_GRADIENT_ALPHA = (ctx, area) => {
  if (!ctx || !area) return '#1D559E';
  const g = ctx.createLinearGradient(0, area.top, 0, area.bottom);
  g.addColorStop(0, 'rgba(29,85,158,.85)');
  g.addColorStop(1, 'rgba(29,85,158,.15)');
  return g;
};

const BASE_OPTS = {
  responsive: true, maintainAspectRatio: false,
  plugins: {
    legend: { labels: { font: { family: 'Inter', size: 12 }, color: '#64748b', padding: 16, boxWidth: 12 } },
    tooltip: {
      backgroundColor: '#1e293b', titleColor: '#f8fafc', bodyColor: '#cbd5e1',
      borderColor: '#334155', borderWidth: 1, padding: 12, cornerRadius: 10,
      titleFont: { family: 'Rajdhani', size: 14, weight: '700' }
    }
  },
  animation: { duration: 900, easing: 'easeOutQuart' }
};

function makeChart(id, config) {
  const canvas = $(id);
  if (!canvas) return null;
  if (charts[id]) { charts[id].destroy(); }
  charts[id] = new Chart(canvas, config);
  return charts[id];
}

// ── GRAFICOS ────────────────────────────────────────────────
async function loadGraficos(qs='') {
  try {
    const r = await fetch('/api/graficos' + qs);
    const d = await r.json();

    // Produção por máquina — grouped bar
    makeChart('chartMaquina', {
      type: 'bar',
      data: {
        labels: d.prod_maquina.labels,
        datasets: [
          { label: 'Produção', data: d.prod_maquina.producao, backgroundColor: BLUE_PALETTE, borderRadius: 6 },
          { label: 'Perdas', data: d.prod_maquina.perda, backgroundColor: '#ef4444', borderRadius: 6 }
        ]
      },
      options: { ...BASE_OPTS, scales: barScales() }
    });

    // Produção por turno — doughnut
    makeChart('chartTurno', {
      type: 'doughnut',
      data: {
        labels: d.prod_turno.labels,
        datasets: [{ data: d.prod_turno.producao, backgroundColor: BLUE_PALETTE, borderWidth: 2, borderColor: '#fff' }]
      },
      options: { ...BASE_OPTS, cutout: '65%' }
    });

    // Evolução diária — area
    makeChart('chartEvolucao', {
      type: 'line',
      data: {
        labels: d.evolucao.labels,
        datasets: [
          {
            label: 'Produção', data: d.evolucao.producao,
            borderColor: '#1D559E', backgroundColor: 'rgba(29,85,158,.15)',
            fill: true, tension: .4, pointRadius: 4,
            pointBackgroundColor: '#1D559E', pointBorderColor: '#fff', pointBorderWidth: 2
          },
          {
            label: 'Perdas', data: d.evolucao.perda,
            borderColor: '#ef4444', backgroundColor: 'rgba(239,68,68,.1)',
            fill: true, tension: .4, pointRadius: 3,
            pointBackgroundColor: '#ef4444', pointBorderColor: '#fff', pointBorderWidth: 2
          }
        ]
      },
      options: { ...BASE_OPTS, scales: lineScales() }
    });

    // Produção por operador — horizontal bar
    makeChart('chartOperador', {
      type: 'bar',
      data: {
        labels: d.prod_operador.labels,
        datasets: [
          { label: 'Produção', data: d.prod_operador.producao, backgroundColor: BLUE_PALETTE, borderRadius: 6 }
        ]
      },
      options: { ...BASE_OPTS, indexAxis: 'y', scales: barScales(true) }
    });

    // Top produtos — horizontal bar
    makeChart('chartProdutos', {
      type: 'bar',
      data: {
        labels: d.top_produtos.labels,
        datasets: [{ label: 'Qtd', data: d.top_produtos.valores, backgroundColor: BLUE_PALETTE, borderRadius: 5 }]
      },
      options: { ...BASE_OPTS, indexAxis: 'y', scales: barScales(true), plugins: { ...BASE_OPTS.plugins, legend: { display: false } } }
    });

    // Tempo parado x produzindo
    makeChart('chartTempo', {
      type: 'bar',
      data: {
        labels: d.tempo_maquina.labels,
        datasets: [
          { label: 'Produzindo (h)', data: d.tempo_maquina.produzindo, backgroundColor: '#1D559E', borderRadius: 5, stack: 'a' },
          { label: 'Parado (h)', data: d.tempo_maquina.parado, backgroundColor: '#ef4444', borderRadius: 5, stack: 'a' }
        ]
      },
      options: { ...BASE_OPTS, scales: barScales() }
    });

    // Meta x Realizado — gauge style
    const mv = d.meta_x_realizado;
    makeChart('chartMeta', {
      type: 'doughnut',
      data: {
        labels: ['Realizado', 'Faltante'],
        datasets: [{
          data: [
            mv.realizado,
            Math.max(0, mv.meta - mv.realizado)
          ],
          backgroundColor: [
            mv.realizado >= mv.meta ? '#16a34a' : '#1D559E',
            '#e2e8f0'
          ],
          borderWidth: 0
        }]
      },
      options: {
        ...BASE_OPTS, cutout: '72%',
        plugins: {
          ...BASE_OPTS.plugins,
          tooltip: { ...BASE_OPTS.plugins.tooltip,
            callbacks: { label: ctx => ` ${fmt(ctx.raw)} peças` }
          }
        }
      }
    });

    // Ranking operadores — eficiência bar
    const ro = d.ranking_operadores;
    makeChart('chartRankingOp', {
      type: 'bar',
      data: {
        labels: ro.map(x => x.nome),
        datasets: [{
          label: 'Eficiência %',
          data: ro.map(x => x.eficiencia),
          backgroundColor: ro.map(x => x.eficiencia >= 95 ? '#16a34a' : x.eficiencia >= 85 ? '#1D559E' : '#ea580c'),
          borderRadius: 6
        }]
      },
      options: {
        ...BASE_OPTS,
        scales: barScales(),
        plugins: {
          ...BASE_OPTS.plugins,
          tooltip: { ...BASE_OPTS.plugins.tooltip, callbacks: { label: ctx => ` ${ctx.raw}%` } }
        }
      }
    });

    // Ranking máquinas — produção
    const rm = d.ranking_maquinas;
    makeChart('chartRankingMaq', {
      type: 'bar',
      data: {
        labels: rm.map(x => x.nome),
        datasets: [{
          label: 'Produção',
          data: rm.map(x => x.producao),
          backgroundColor: BLUE_PALETTE,
          borderRadius: 6
        }]
      },
      options: { ...BASE_OPTS, scales: barScales() }
    });

  } catch(e) { console.error('graficos error', e); }
}

function barScales(horizontal=false) {
  return {
    x: { grid: { color: '#f1f5f9' }, ticks: { color: '#64748b', font: { size: 11 } }, border: { display: false } },
    y: { grid: { color: '#f1f5f9' }, ticks: { color: '#64748b', font: { size: 11 } }, border: { display: false } }
  };
}
function lineScales() {
  return {
    x: { grid: { display: false }, ticks: { color: '#64748b', font: { size: 11 } }, border: { display: false } },
    y: { grid: { color: '#f1f5f9' }, ticks: { color: '#64748b', font: { size: 11 } }, border: { display: false } }
  };
}

// ── TABLES ───────────────────────────────────────────────────
async function loadTabelas(qs='') {
  try {
    const r = await fetch('/api/tabelas' + qs);
    const d = await r.json();

    // Operadores
    renderTable('tbl-operadores', d.operadores_produtivos, (row, i) => `
      <td><span class="rank-num ${i<3?`rank-medal-${i+1}`:''}">${i===0?'🥇':i===1?'🥈':i===2?'🥉':i+1}</span></td>
      <td>${row.operador}</td>
      <td>${fmt(row.total)}</td>
      <td>${fmt(row.perdas)}</td>
      <td><span class="badge ${efBadge(row.eficiencia)}">${fmtPct(row.eficiencia)}</span></td>
    `);

    // Máquinas perda
    renderTable('tbl-maq-perda', d.maquinas_perda, (row, i) => `
      <td><span class="rank-num">${i+1}</span></td>
      <td>${row.maquina}</td>
      <td>${fmt(row.total)}</td>
      <td>${fmt(row.perdas)}</td>
      <td><span class="badge ${pctBadge(row.pct_perda)}">${fmtPct(row.pct_perda)}</span></td>
    `);

    // Produtos
    renderTable('tbl-produtos', d.produtos_fabricados, (row, i) => `
      <td><span class="rank-num">${i+1}</span></td>
      <td>${row.produto}</td>
      <td>${fmt(row.total)}</td>
      <td>${fmt(row.perdas)}</td>
      <td>${fmt(row.apontamentos)}</td>
    `);

    // Últimos apontamentos
    renderTable('tbl-ultimos', d.ultimos_apontamentos, (row) => `
      <td>${row.data}</td>
      <td><span class="badge badge-blue">${row.turno}</span></td>
      <td>${row.maquina}</td>
      <td>${row.produto}</td>
      <td>${row.operador}</td>
      <td>${fmt(row.quantidade)}</td>
      <td><span class="badge ${row.perda > 0 ? 'badge-red' : 'badge-green'}">${fmt(row.perda)}</span></td>
    `);

    const badge = $('badge-ultimos');
    if (badge) badge.textContent = d.ultimos_apontamentos.length;

  } catch(e) { console.error('tabelas error', e); }
}

function renderTable(id, rows, rowFn) {
  const tbl = $(id);
  if (!tbl) return;
  const tbody = tbl.querySelector('tbody');
  if (!tbody) return;
  if (!rows || !rows.length) {
    tbody.innerHTML = '<tr><td colspan="99" style="text-align:center;padding:24px;color:#94a3b8">Sem dados para exibir</td></tr>';
    return;
  }
  tbody.innerHTML = rows.map((row, i) => `<tr>${rowFn(row, i)}</tr>`).join('');
}

function efBadge(v) {
  v = +v;
  if (v >= 95) return 'badge-green';
  if (v >= 85) return 'badge-blue';
  if (v >= 70) return 'badge-yellow';
  return 'badge-red';
}
function pctBadge(v) {
  v = +v;
  if (v <= 2)  return 'badge-green';
  if (v <= 5)  return 'badge-yellow';
  return 'badge-red';
}

// ── REFRESH ─────────────────────────────────────────────────
async function refreshAll() {
  const btn = $('btnRefresh');
  if (btn) btn.querySelector('i').classList.add('spinning');

  const qs = getFilterParams();
  await Promise.allSettled([loadResumo(qs), loadGraficos(qs), loadTabelas(qs), checkStatus()]);

  if (btn) setTimeout(() => btn.querySelector('i').classList.remove('spinning'), 600);
}

// ── EXPORT ───────────────────────────────────────────────────
$('btnExport')?.addEventListener('click', () => {
  const qs = getFilterParams();
  const url = '/api/tabelas' + qs;
  fetch(url)
    .then(r => r.json())
    .then(d => {
      const rows = d.ultimos_apontamentos || [];
      if (!rows.length) { alert('Sem dados para exportar.'); return; }
      const headers = Object.keys(rows[0]);
      const csv = [headers.join(';'), ...rows.map(r => headers.map(h => r[h] ?? '').join(';'))].join('\n');
      const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `amt_producao_${new Date().toISOString().slice(0,10)}.csv`;
      a.click();
    });
});

// ── FILTER EVENTS ────────────────────────────────────────────
$('btnApply')?.addEventListener('click', refreshAll);

$('btnClearFilters')?.addEventListener('click', () => {
  ['f-dt-ini','f-dt-fim','f-turno','f-maquina','f-operador','f-produto','f-processo']
    .forEach(id => {
      const el = $(id);
      if (!el) return;
      if (el.tagName === 'SELECT') el.value = 'todos';
      else el.value = '';
    });
  refreshAll();
});

$('btnRefresh')?.addEventListener('click', refreshAll);

// ── INIT ─────────────────────────────────────────────────────
async function init() {
  await loadFiltros();
  await refreshAll();

  // Hide loading screen
  setTimeout(() => {
    const ls = $('loading-screen');
    if (ls) ls.classList.add('hidden');
  }, 2000);

  // Auto-refresh every 5 minutes
  setInterval(refreshAll, 5 * 60 * 1000);
}

document.addEventListener('DOMContentLoaded', init);
