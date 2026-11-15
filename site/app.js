(function () {
  'use strict';

  const page = document.body.dataset.page || 'today';
  const demo = window.JOB_WATCHER_DEMO || { status: {}, history: [] };
  const state = { status: null, history: [], scope: 'role', filters: { search: '', employer: '', location: '', days: '' }, sort: 'dallas', shortlistOnly: false };
  const SHORTLIST_KEY = 'job-watcher-shortlist-v1';

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
  const esc = value => String(value ?? '').replace(/[&<>"']/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[character]));
  const asDate = value => value ? new Date(`${value}T00:00:00Z`) : null;
  const dateOnly = value => value ? String(value).slice(0, 10) : '';
  const daysBetween = (from, to) => {
    const a = asDate(from); const b = asDate(to);
    return a && b ? Math.max(0, Math.round((b - a) / 86400000)) : null;
  };
  const latestDate = history => history.reduce((latest, row) => [latest, row.last_seen, row.removed_date, row.first_seen].filter(Boolean).sort().pop() || latest, '');
  const latestRunDate = () => dateOnly(state.status && state.status.run_time) || latestDate(state.history);
  const formatRun = value => {
    if (!value) return '—';
    const date = new Date(value);
    return new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit', timeZone: 'UTC' }).format(date) + ' UTC';
  };
  const formatShortDate = value => value ? new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' }).format(asDate(value)) : '—';
  const relativeAge = row => row.first_run === 'true' ? 'Before watch' : `${daysBetween(row.first_seen, latestRunDate()) || 0}d open`;
  const getShortlist = () => { try { return JSON.parse(localStorage.getItem(SHORTLIST_KEY) || '[]'); } catch (error) { return []; } };
  const setShortlist = values => localStorage.setItem(SHORTLIST_KEY, JSON.stringify(values));
  const isSaved = id => getShortlist().includes(id);
  const isDallasArea = location => /\b(?:dallas|fort worth|irving|plano|frisco|richardson|arlington|mckinney|carrollton|addison|grapevine|coppell|lewisville|southlake|the colony|allen|garland|mesquite|farmers branch)\b/i.test(location || '');

  function parseCSV(text) {
    const rows = []; let row = []; let cell = ''; let quoted = false;
    for (let index = 0; index < text.length; index += 1) {
      const character = text[index]; const next = text[index + 1];
      if (character === '"' && quoted && next === '"') { cell += '"'; index += 1; continue; }
      if (character === '"') { quoted = !quoted; continue; }
      if (character === ',' && !quoted) { row.push(cell); cell = ''; continue; }
      if ((character === '\n' || character === '\r') && !quoted) {
        if (character === '\r' && next === '\n') index += 1;
        row.push(cell); cell = '';
        if (row.some(value => value !== '')) rows.push(row);
        row = []; continue;
      }
      cell += character;
    }
    if (cell || row.length) { row.push(cell); rows.push(row); }
    const headers = rows.shift() || [];
    return rows.map(values => headers.reduce((record, header, index) => { record[header] = values[index] || ''; return record; }, {}));
  }

  async function loadData() {
    try {
      const [statusResponse, historyResponse] = await Promise.all([fetch('data/status.json', { cache: 'no-store' }), fetch('data/history.csv', { cache: 'no-store' })]);
      if (!statusResponse.ok || !historyResponse.ok) throw new Error('Data files unavailable');
      state.status = await statusResponse.json(); state.history = parseCSV(await historyResponse.text());
      localStorage.setItem('job-watcher-status-v1', JSON.stringify(state.status));
      localStorage.setItem('job-watcher-history-v1', JSON.stringify(state.history));
    } catch (error) {
      try {
        state.status = JSON.parse(localStorage.getItem('job-watcher-status-v1') || 'null');
        state.history = JSON.parse(localStorage.getItem('job-watcher-history-v1') || 'null');
      } catch (cacheError) { state.status = null; state.history = null; }
      if (!state.status || !Array.isArray(state.history)) { state.status = demo.status; state.history = demo.history; }
    }
    document.body.classList.toggle('is-demo', Boolean(state.status.demo));
    renderShared();
    if (page === 'today') renderToday();
    if (page === 'browse') renderBrowse();
    if (page === 'market') renderMarket();
  }

  function renderShared() {
    $$('[data-open-count]').forEach(element => { element.textContent = state.status.open ?? state.history.filter(row => row.status === 'open').length; });
    $$('[data-run-label]').forEach(element => { element.innerHTML = `<span class="live-dot"></span>${state.status.demo ? 'Design preview' : 'Live watchlist'}`; });
    $$('[data-last-run]').forEach(element => { element.textContent = formatRun(state.status.run_time); });
    $$('[data-last-run-short]').forEach(element => { element.textContent = formatShortDate(latestRunDate()); });
    $$('[data-footer-date]').forEach(element => { element.textContent = `Updated ${formatShortDate(latestRunDate())} · UTC`; });
    $$('[data-metric]').forEach(element => { const key = element.dataset.metric; element.textContent = state.status[key] ?? '—'; });
  }

  function miniPosting(row, kind) {
    return `<a class="posting-mini ${kind}" href="${esc(row.url)}" target="_blank" rel="noopener noreferrer"><div><div class="posting-mini-title">${esc(row.title)}</div><div class="posting-mini-meta">${esc(row.employer)} · ${esc(row.location)}</div></div><span class="posting-mini-date">${kind === 'new' ? formatShortDate(row.first_seen) : formatShortDate(row.removed_date)}</span></a>`;
  }

  function renderToday() {
    const date = latestRunDate();
    const newRows = state.history.filter(row => row.first_seen === date && row.first_run !== 'true');
    const removedRows = state.history.filter(row => row.removed_date === date);
    $('[data-new-list]').innerHTML = newRows.length ? newRows.map(row => miniPosting(row, 'new')).join('') : '<p class="panel-intro">No new roles in the latest run.</p>';
    $('[data-removed-list]').innerHTML = removedRows.length ? removedRows.map(row => miniPosting(row, 'removed')).join('') : '<p class="panel-intro">No removed roles in the latest run.</p>';
    $('[data-new-count]').textContent = newRows.length; $('[data-removed-count]').textContent = removedRows.length;
    const sources = state.status.sources || [];
    const healthy = sources.filter(source => source.ok).length;
    $('[data-health-score]').textContent = `${sources.length ? Math.round(healthy / sources.length * 100) : 0}%`;
    $('[data-source-list]').innerHTML = sources.map(source => `<div class="health-item ${source.ok ? '' : 'is-failed'}"><span class="health-name">${esc(source.name)}</span><span class="health-value">${source.ok ? `${source.count} roles` : 'unavailable'}</span><div class="health-track"><span style="width:${source.ok ? 100 : 22}%"></span></div></div>`).join('');
  }

  function initBrowse() {
    $$('[data-scope]').forEach(button => button.addEventListener('click', () => { state.scope = button.dataset.scope; state.shortlistOnly = false; $$('[data-scope]').forEach(item => item.classList.toggle('active', item === button)); renderBrowse(); }));
    $('[data-search]').addEventListener('input', event => { state.filters.search = event.target.value.trim().toLowerCase(); renderBrowse(); });
    $$('[data-filter]').forEach(select => select.addEventListener('change', event => { state.filters[select.dataset.filter] = event.target.value; renderBrowse(); }));
    $('[data-sort]').addEventListener('change', event => { state.sort = event.target.value; renderBrowse(); });
    $('[data-show-shortlist]').addEventListener('click', event => { event.preventDefault(); state.shortlistOnly = !state.shortlistOnly; renderBrowse(); });
  }

  function populateSelect(selector, values, label) {
    const select = $(selector); const current = select.value;
    select.innerHTML = `<option value="">${label}</option>` + values.sort((a, b) => a.localeCompare(b)).map(value => `<option value="${esc(value)}">${esc(value)}</option>`).join('');
    select.value = values.includes(current) ? current : '';
  }

  function renderBrowse() {
    if (!$('[data-role-list]')) return;
    const open = state.history.filter(row => row.status === 'open');
    populateSelect('[data-filter="employer"]', [...new Set(open.map(row => row.employer))], 'All employers');
    populateSelect('[data-filter="location"]', [...new Set(open.map(row => row.location))], 'All locations');
    let rows = open.filter(row => state.scope === 'all' || row.in_role === 'true');
    if (state.shortlistOnly) rows = rows.filter(row => isSaved(row.posting_id));
    const search = state.filters.search;
    rows = rows.filter(row => !search || `${row.title} ${row.employer} ${row.department}`.toLowerCase().includes(search));
    rows = rows.filter(row => !state.filters.employer || row.employer === state.filters.employer);
    rows = rows.filter(row => !state.filters.location || row.location === state.filters.location);
    rows = rows.filter(row => !state.filters.days || (daysBetween(row.first_seen, latestRunDate()) ?? 999) <= Number(state.filters.days));
    rows.sort((a, b) => state.sort === 'dallas' ? Number(isDallasArea(b.location)) - Number(isDallasArea(a.location)) || b.first_seen.localeCompare(a.first_seen) : state.sort === 'employer' ? a.employer.localeCompare(b.employer) : state.sort === 'oldest' ? a.first_seen.localeCompare(b.first_seen) : b.first_seen.localeCompare(a.first_seen));
    $('[data-result-count]').textContent = rows.length;
    $('[data-browse-heading]').textContent = state.shortlistOnly ? 'Saved roles' : state.scope === 'role' ? 'Roles in your lane' : 'All open postings';
    $('[data-role-list]').innerHTML = rows.map((row, index) => roleCard(row, index)).join('');
    $('[data-empty-state]').hidden = rows.length > 0;
    $$('[data-star]').forEach(button => button.addEventListener('click', () => toggleStar(button.dataset.star)));
    renderShortlist();
  }

  function roleCard(row, index) {
    return `<article class="role-card"><span class="role-index">${String(index + 1).padStart(2, '0')}</span><div><div class="role-title">${esc(row.title)}</div><div class="role-employer">${esc(row.employer)}</div></div><div class="role-location"><span>Location${isDallasArea(row.location) ? ' · DFW' : ''}</span>${esc(row.location || 'Not listed')}</div><div class="role-department"><span>Team</span>${esc(row.department || '—')}</div><div class="role-age"><strong>${esc(relativeAge(row))}</strong><span>${formatShortDate(row.first_seen)}</span></div><div class="role-actions"><a class="apply-link" href="${esc(row.url)}" target="_blank" rel="noopener noreferrer" aria-label="Open application">↗</a><button class="star-button ${isSaved(row.posting_id) ? 'saved' : ''}" data-star="${esc(row.posting_id)}" aria-label="${isSaved(row.posting_id) ? 'Remove from shortlist' : 'Save to shortlist'}">★</button></div></article>`;
  }

  function toggleStar(id) { const values = getShortlist(); const next = values.includes(id) ? values.filter(value => value !== id) : [...values, id]; setShortlist(next); renderBrowse(); }
  function renderShortlist() {
    const values = getShortlist(); $$('[data-shortlist-count]').forEach(element => element.textContent = values.length);
    const rows = state.history.filter(row => values.includes(row.posting_id) && row.status === 'open');
    $('[data-shortlist-preview]').innerHTML = rows.length ? rows.slice(0, 4).map(row => `<a class="short-role" href="${esc(row.url)}" target="_blank" rel="noopener noreferrer"><div class="short-role-title">${esc(row.title)}</div><div class="short-role-meta">${esc(row.employer)} · ${esc(row.location)}</div></a>`).join('') : '<div class="shortlist-empty">Your saved roles will appear here.</div>';
  }

  function groupCount(rows, key) {
    return rows.reduce((result, row) => { const value = row[key] || 'Not listed'; result[value] = (result[value] || 0) + 1; return result; }, {});
  }
  function median(values) { if (!values.length) return null; const sorted = [...values].sort((a, b) => a - b); const middle = Math.floor(sorted.length / 2); return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2; }
  function barChart(values, options = {}) {
    const entries = Object.entries(values); const max = Math.max(...entries.map(entry => entry[1]), 1); const width = 440; const height = options.height || 170; const bottom = 28; const plotHeight = height - bottom; const step = width / Math.max(entries.length, 1); const barWidth = Math.min(30, step * .52);
    const bars = entries.map(([label, value], index) => { const barHeight = value / max * (plotHeight - 18); const x = index * step + (step - barWidth) / 2; const y = plotHeight - barHeight; return `<line class="chart-gridline" x1="${x + barWidth / 2}" y1="8" x2="${x + barWidth / 2}" y2="${plotHeight}"/><rect class="chart-bar-fill ${index % 2 ? 'alt' : ''}" x="${x}" y="${y}" width="${barWidth}" height="${Math.max(3, barHeight)}" rx="4"/><text class="chart-value" x="${x + barWidth / 2}" y="${Math.max(12, y - 7)}" text-anchor="middle">${value}</text><text class="chart-label" x="${x + barWidth / 2}" y="${height - 7}" text-anchor="middle">${esc(label)}</text>`; }).join('');
    return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Bar chart">${bars}</svg>`;
  }
  function horizontalBars(values) {
    const entries = Object.entries(values).slice(0, 5); const max = Math.max(...entries.map(entry => entry[1]), 1); const width = 440; const rowHeight = 28; const height = Math.max(145, entries.length * rowHeight + 8);
    return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Horizontal bar chart">${entries.map(([label, value], index) => { const y = index * rowHeight + 5; const barWidth = value / max * 250; return `<text class="chart-label" x="0" y="${y + 12}">${esc(label.length > 20 ? `${label.slice(0, 19)}…` : label)}</text><rect class="chart-bar-bg" x="145" y="${y}" width="250" height="12" rx="6"/><rect class="chart-bar-fill ${index > 0 ? 'alt' : ''}" x="145" y="${y}" width="${Math.max(7, barWidth)}" height="12" rx="6"/><text class="chart-value" x="410" y="${y + 10}" text-anchor="end">${value}</text>`; }).join('')}</svg>`;
  }
  function donutChart(value, label) {
    const circumference = 2 * Math.PI * 56; const dash = Math.max(0, Math.min(1, value)) * circumference;
    return `<svg viewBox="0 0 180 180" role="img" aria-label="${esc(label)}"><circle class="donut-base" cx="90" cy="90" r="56"/><circle class="donut-fill" cx="90" cy="90" r="56" stroke-dasharray="${dash} ${circumference - dash}"/><text class="donut-center" x="90" y="93">${Math.round(value * 100)}%</text><text class="donut-sub" x="90" y="110">within 7 days</text></svg>`;
  }

  function renderMarket() {
    const history = state.history; const latest = latestRunDate(); const start = history.map(row => row.first_seen).filter(Boolean).sort()[0] || latest; const open = history.filter(row => row.status === 'open'); const newRows = history.filter(row => row.first_seen && row.first_run !== 'true'); const removedRows = history.filter(row => row.removed_date); const knownDurations = removedRows.filter(row => row.first_run !== 'true' && row.first_seen).map(row => daysBetween(row.first_seen, row.removed_date)).filter(value => value !== null); const qualified = removedRows.filter(row => row.first_run !== 'true' && row.first_seen && daysBetween(row.first_seen, latest) >= 7); const withinSeven = qualified.filter(row => daysBetween(row.first_seen, row.removed_date) <= 7);
    $('[data-market-window]').textContent = `${formatShortDate(start)}–${formatShortDate(latest)}, ${new Date(asDate(latest)).getUTCFullYear()}`; $('[data-market-open]').textContent = open.length; $('[data-market-employers]').textContent = new Set(history.map(row => row.employer)).size;
    const dates = [...new Set(history.flatMap(row => [row.first_seen, row.removed_date]).filter(Boolean))].sort();
    const newByDate = dates.reduce((result, date) => { result[date.slice(5)] = newRows.filter(row => row.first_seen === date).length; return result; }, {});
    const removedByDate = dates.reduce((result, date) => { result[date.slice(5)] = removedRows.filter(row => row.removed_date === date).length; return result; }, {});
    const employerCounts = groupCount(open, 'employer'); const locationCounts = groupCount(open, 'location');
    $('[data-chart="new"]').innerHTML = barChart(newByDate); $('[data-chart="removed"]').innerHTML = barChart(removedByDate, { height: 150 }); $('[data-chart="employers"]').innerHTML = horizontalBars(employerCounts); $('[data-chart="locations"]').innerHTML = horizontalBars(locationCounts); $('[data-chart="days"]').innerHTML = donutChart(knownDurations.length ? Math.min(1, median(knownDurations) / 14) : 0, 'Median days open');
    $('[data-insight="new-total"]').textContent = newRows.length; $('[data-insight="removed-total"]').textContent = removedRows.length; $('[data-insight="top-employer"]').textContent = Object.entries(employerCounts).sort((a, b) => b[1] - a[1])[0]?.[0] || '—'; $('[data-insight="median-days"]').textContent = knownDurations.length ? `${Math.round(median(knownDurations))}d` : '—'; $('[data-insight="seven-day"]').textContent = qualified.length ? `${Math.round(withinSeven.length / qualified.length * 100)}%` : '—'; $('[data-insight="seven-count"]').textContent = withinSeven.length; $('[data-insight="seven-total"]').textContent = qualified.length; $('[data-insight="top-location"]').textContent = Object.entries(locationCounts).sort((a, b) => b[1] - a[1])[0]?.[0] || '—';
  }

  if (page === 'browse') initBrowse();
  loadData();
  if ('serviceWorker' in navigator) window.addEventListener('load', () => navigator.serviceWorker.register('sw.js').catch(() => {}));
})();
