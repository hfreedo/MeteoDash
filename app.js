// Sistema Meteorologico - App Core
// WebSocket URL: WSS si es HTTPS, WS si es localhost
var WS_URL;
if (window.location.protocol === 'https:') {
  WS_URL = 'wss://' + window.location.host + '/ws';
} else {
  WS_URL = 'ws://' + window.location.hostname + ':8000/ws';
}
var ws = null;
var reconnectTimer = null;
var ledStates = {};
var serialActive = false;
var authToken = null;
var authUser = null;

// --- Boot ---
function isLocal() {
  var h = window.location.hostname;
  return h === 'localhost' || h === '127.0.0.1' || h.startsWith('192.168.') || h.startsWith('10.') || h.startsWith('172.');
}

function bootApp() {
  document.getElementById('btnLoginSidebar').addEventListener('click', loginBtnHandler);
  // Ocultar panel serial si acceso remoto
  if (!isLocal()) {
    var bar = document.querySelector('.connect-bar');
    if (bar) bar.style.display = 'none';
    document.getElementById('serialBadge').textContent = 'Remoto';
  }
  checkStoredAuth();
  initTheme();
  initGauges();
  initCharts();
  connectWebSocket();
  initSerialControls();
  initControls();
  updateClock();
  setInterval(updateClock, 1000);
  loadHistory(24);
  scanPorts();
  updateAdminUI();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', bootApp);
} else {
  bootApp();
}

// --- Auth ---
function checkStoredAuth() {
  authToken = localStorage.getItem('meteodash-token');
  try { authUser = JSON.parse(localStorage.getItem('meteodash-user') || 'null'); } catch (e) { authUser = null; }
  if (authToken) {
    fetch('/api/me', { headers: { 'Authorization': 'Bearer ' + authToken } })
      .then(function(r) { return r.ok ? r.json() : null; })
      .then(function(u) { if (u) { authUser = u; updateAdminUI(); } else { clearAuth(); updateAdminUI(); } })
      .catch(function() {});
  }
}

function clearAuth() {
  authToken = null; authUser = null;
  localStorage.removeItem('meteodash-token');
  localStorage.removeItem('meteodash-user');
}

function isAdmin() { return authUser && authUser.role === 'admin'; }

function authFetch(url, options) {
  options = options || {};
  options.headers = options.headers || {};
  if (authToken) options.headers['Authorization'] = 'Bearer ' + authToken;
  return fetch(url, options);
}

// --- Theme ---
function getTheme() { return document.documentElement.getAttribute('data-theme') || 'dark'; }

function initTheme() {
  var saved = localStorage.getItem('meteodash-theme');
  if (saved === 'light' || saved === 'dark') document.documentElement.setAttribute('data-theme', saved);
  updateThemeUI();
  document.getElementById('themeToggle').addEventListener('click', toggleTheme);
}

function toggleTheme() {
  var next = getTheme() === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('meteodash-theme', next);
  updateThemeUI();
  reinitVisuals();
}

function updateThemeUI() {
  var isDark = getTheme() === 'dark';
  document.getElementById('themeIcon').textContent = isDark ? '\u2600' : '\u263E';
  document.getElementById('themeLabel').textContent = isDark ? 'Modo Claro' : 'Modo Oscuro';
}

// --- Serial ---
function initSerialControls() {
  document.getElementById('btnScan').addEventListener('click', scanPorts);
  document.getElementById('btnConnect').addEventListener('click', connectSerial);
  document.getElementById('btnDisconnect').addEventListener('click', disconnectSerial);
}

async function scanPorts() {
  var select = document.getElementById('portSelect');
  var msg = document.getElementById('connectMsg');
  select.innerHTML = '<option value="">Escaneando...</option>';
  msg.textContent = 'Buscando puertos...';
  msg.className = 'connect-status info';
  try {
    var resp = await fetch('/api/ports');
    var data = await resp.json();
    select.innerHTML = '';
    if (data.ports.length === 0) {
      select.innerHTML = '<option value="">No se encontraron puertos</option>';
      msg.textContent = 'No se detectaron puertos COM.';
      msg.className = 'connect-status error';
    } else {
      data.ports.forEach(function(p) {
        var opt = document.createElement('option');
        opt.value = p.device;
        opt.textContent = p.device + ' - ' + p.description;
        select.appendChild(opt);
      });
      msg.textContent = data.ports.length + ' puerto(s) encontrado(s).';
      msg.className = 'connect-status success';
    }
    if (data.connected) { setSerialUI(true, data.active_port); msg.textContent = 'Conectado a ' + data.active_port; msg.className = 'connect-status success'; }
  } catch (err) {
    select.innerHTML = '<option value="">Error</option>';
    msg.textContent = 'Error al escanear.';
    msg.className = 'connect-status error';
  }
}

async function connectSerial() {
  var select = document.getElementById('portSelect');
  var port = select.value;
  var msg = document.getElementById('connectMsg');
  if (!port) { msg.textContent = 'Selecciona un puerto.'; msg.className = 'connect-status error'; return; }
  msg.textContent = 'Conectando a ' + port + '...';
  msg.className = 'connect-status info';
  try {
    var resp = await authFetch('/api/connect?port=' + encodeURIComponent(port) + '&baud=9600', { method: 'POST' });
    if (resp.ok) { setSerialUI(true, port); msg.textContent = 'Conectado a ' + port + ' @ 9600 baud.'; msg.className = 'connect-status success'; }
    else { var err = await resp.json(); msg.textContent = err.detail || 'Requiere login admin.'; msg.className = 'connect-status error'; }
  } catch (err) { msg.textContent = 'Error de conexion.'; msg.className = 'connect-status error'; }
}

async function disconnectSerial() {
  var msg = document.getElementById('connectMsg');
  try { await authFetch('/api/disconnect', { method: 'POST' }); setSerialUI(false); msg.textContent = 'Desconectado.'; msg.className = 'connect-status info'; }
  catch (err) { msg.textContent = 'Error al desconectar.'; msg.className = 'connect-status error'; }
}

function setSerialUI(active, port) {
  serialActive = active;
  document.getElementById('btnConnect').disabled = active;
  document.getElementById('btnDisconnect').disabled = !active;
  document.getElementById('portSelect').disabled = active;
  var dot = document.getElementById('sbDot');
  var status = document.getElementById('sbStatus');
  var badge = document.getElementById('serialBadge');
  if (active) {
    dot.className = 'sidebar-dot on'; status.textContent = 'Conectado - ' + (port || 'COM');
    badge.textContent = 'Conectado ' + (port || ''); badge.className = 'topbar-badge connected';
  } else {
    dot.className = 'sidebar-dot off'; status.textContent = 'Sin conexion';
    badge.textContent = 'Sin conexion'; badge.className = 'topbar-badge';
  }
}

// --- WebSocket ---
function connectWebSocket() {
  try {
    ws = new WebSocket(WS_URL);
    ws.onopen = function() { clearTimeout(reconnectTimer); };
    ws.onmessage = function(event) {
      try { var msg = JSON.parse(event.data);
        if (msg.type === 'reading' && msg.data) updateDashboard(msg.data);
        if (msg.type === 'clear_widgets') clearWidgets();
        if (msg.type === 'history_cleared') clearCharts();
      } catch (e) {}
    };
    ws.onclose = function() { scheduleReconnect(); };
    ws.onerror = function() {};
  } catch (e) { scheduleReconnect(); }
}

function scheduleReconnect() { clearTimeout(reconnectTimer); reconnectTimer = setTimeout(connectWebSocket, 3000); }

function sendCommand(cmd) {
  if (!serialActive) { var msg = document.getElementById('connectMsg'); if (msg) { msg.textContent = 'Conecta el Arduino primero.'; msg.className = 'connect-status error'; } return; }
  if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ cmd: cmd }));
  else authFetch('/api/command?cmd=' + encodeURIComponent(cmd), { method: 'POST' }).catch(function() {});
}

// --- Dashboard Update ---
var latestData = null;
var lastDataTime = null;

function updateDashboard(data) {
  if (!data) return;
  latestData = data; lastDataTime = Date.now();
  updateGaugeValues(data);
  updateAccelGyro(data);
  updateIR(data);
  updateLastUpdate();
  addHistoryPoint(data);
}

function updateAccelGyro(data) {
  setText('valAccelX', (data.ax || 0).toFixed(2)); setText('valAccelY', (data.ay || 0).toFixed(2)); setText('valAccelZ', (data.az || 0).toFixed(2));
  setText('valGyroX', (data.gx || 0).toFixed(2)); setText('valGyroY', (data.gy || 0).toFixed(2)); setText('valGyroZ', (data.gz || 0).toFixed(2));
}

function updateIR(data) {
  var circle = document.getElementById('irCircle'); var text = document.getElementById('irText');
  if (data.ir === 0) { circle.className = 'ir-circle active'; text.textContent = 'Objeto Detectado'; text.style.color = '#ef4444'; }
  else { circle.className = 'ir-circle inactive'; text.textContent = 'Libre'; text.style.color = '#10b981'; }
}

function updateLastUpdate() {
  var el = document.getElementById('lastUpdate');
  if (!el) return;
  var now = new Date();
  var ts = now.toLocaleTimeString('es');
  if (lastDataTime) {
    var seconds = Math.floor((now - lastDataTime) / 1000);
    var age = seconds < 60 ? 'hace ' + seconds + 's' : 'hace ' + Math.floor(seconds / 60) + 'm';
    el.innerHTML = '<span class="pulse-dot"></span>Ultima lectura: ' + ts + ' (' + age + ')';
  } else {
    el.textContent = 'Ultima actualizacion: ' + ts;
  }
}

function updateClock() {
  var el = document.getElementById('clock');
  if (el) el.textContent = new Date().toLocaleString('es', { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

// --- Controls ---
function initControls() {
  document.querySelectorAll('.led-btn').forEach(function(btn) {
    btn.addEventListener('click', function() {
      var ledNum = btn.dataset.led; var cmdBase = btn.dataset.cmd;
      ledStates[ledNum] = !ledStates[ledNum];
      btn.classList.toggle('active', ledStates[ledNum]);
      sendCommand(cmdBase + ':' + (ledStates[ledNum] ? 1 : 0));
    });
  });
  document.getElementById('lcdSend').addEventListener('click', function() { var input = document.getElementById('lcdInput'); var msg = input.value.trim(); if (msg) { sendCommand('LCD:' + msg); input.value = ''; } });
  document.getElementById('lcdReset').addEventListener('click', function() { sendCommand('LCD_RESET'); document.getElementById('lcdInput').value = ''; });
  document.getElementById('lcdInput').addEventListener('keydown', function(e) { if (e.key === 'Enter') document.getElementById('lcdSend').click(); });
  document.getElementById('btSend').addEventListener('click', function() {
    var input = document.getElementById('btInput'); var name = input.value.trim();
    if (!name) return;
    if (!serialActive) { showToast('Conecta el Arduino primero (panel Serial)', 'error'); return; }
    sendCommand('BT_NAME:' + name);
    showToast('Nombre BT enviado: ' + name, 'info');
    input.value = '';
  });
  document.getElementById('btnRefresh').addEventListener('click', function() { sendCommand('STATUS'); });
  document.getElementById('historyRange').addEventListener('change', function(e) { loadHistory(parseInt(e.target.value)); });
  document.getElementById('btnTestMode').addEventListener('click', toggleTestMode);
  document.getElementById('btnClearHistory').addEventListener('click', clearHistory);
}

var testModeActive = false;

function showConfirm(msg, onYes) {
  document.getElementById('confirmMsg').textContent = msg;
  document.getElementById('confirmOverlay').classList.remove('hidden');
  document.getElementById('confirmYes').onclick = function() {
    document.getElementById('confirmOverlay').classList.add('hidden');
    onYes();
  };
  document.getElementById('confirmNo').onclick = function() {
    document.getElementById('confirmOverlay').classList.add('hidden');
  };
}

async function clearHistory() {
  showConfirm('Eliminar todo el historial de lecturas?', async function() {
    try {
      var resp = await authFetch('/api/clear-history', { method: 'POST' });
      if (resp.ok) {
        clearCharts();
        loadHistory(currentRange || 24);
        showToast('Historial eliminado', 'success');
      }
    } catch (e) {
      showToast('Error al limpiar', 'error');
    }
  });
}

async function toggleTestMode() {
  if (!isAdmin()) { showToast('Solo administradores', 'error'); return; }
  var btn = document.getElementById('btnTestMode');
  btn.textContent = testModeActive ? 'Desactivando...' : 'Activando...';
  btn.disabled = true;
  try {
    var resp = await authFetch('/api/test-mode', { method: 'POST' });
    var data = await resp.json();
    if (resp.ok) {
      testModeActive = data.status === 'test_mode_on';
      if (testModeActive) {
        btn.textContent = 'Modo Test: ON';
        btn.className = 'btn btn-success btn-xs';
        showToast('Modo Test activado - visible para todos', 'success');
      } else {
        btn.textContent = 'Modo Test';
        btn.className = 'btn btn-outline btn-xs';
        clearWidgets();
        showToast('Modo Test desactivado', 'info');
      }
    } else {
      showToast('Error: ' + (data.detail || 'No autorizado'), 'error');
    }
  } catch (e) {
    showToast('Error de conexion. Reinicia el servidor.', 'error');
    btn.textContent = 'Modo Test';
    btn.className = 'btn btn-outline btn-xs';
  }
  btn.disabled = false;
}

function clearWidgets() {
  if (typeof gauges !== 'undefined') {
    if (gauges.temp) gauges.temp.setValue(-10);
    if (gauges.hum)  gauges.hum.setValue(0);
    if (gauges.pres) gauges.pres.setValue(900);
    if (gauges.alt)  gauges.alt.setValue(-50);
    if (gauges.lux)  gauges.lux.setValue(0);
  }
  setText('valTemp', '--.-'); setText('valHum', '--.-'); setText('valPres', '----');
  setText('valAlt', '--.-'); setText('valLux', '--');
  ['valAccelX','valAccelY','valAccelZ','valGyroX','valGyroY','valGyroZ'].forEach(function(id) {
    var el = document.getElementById(id); if (el) el.textContent = '--';
  });
  var c = document.getElementById('irCircle'); if (c) c.className = 'ir-circle inactive';
  var t = document.getElementById('irText'); if (t) { t.textContent = 'Esperando...'; t.style.color = ''; }
  if (typeof chartTempHum !== 'undefined' && chartTempHum) {
    chartTempHum.data.labels = []; chartTempHum.data.datasets[0].data = [];
    chartTempHum.data.datasets[1].data = []; chartTempHum.update('none');
  }
  if (typeof chartPressure !== 'undefined' && chartPressure) {
    chartPressure.data.labels = []; chartPressure.data.datasets[0].data = []; chartPressure.update('none');
  }
  latestData = null; lastDataTime = null; updateLastUpdate();
}

function reinitVisuals() {
  if (typeof chartTempHum !== 'undefined' && chartTempHum) { chartTempHum.destroy(); chartTempHum = null; }
  if (typeof chartPressure !== 'undefined' && chartPressure) { chartPressure.destroy(); chartPressure = null; }
  createChartTempHum(); createChartPressure();
  loadHistory(parseInt(document.getElementById('historyRange').value || 24));
  var data = latestData || {}; gauges = {}; initGauges(); updateGaugeValues(data);
}

// --- Admin UI ---
function loginBtnHandler() {
  if (isAdmin()) { clearAuth(); updateAdminUI(); }
  else { showLoginOverlay(); }
}

function updateAdminUI() {
  var editBtn = document.getElementById('btnEditProfile');
  var loginBtn = document.getElementById('btnLoginSidebar');
  if (isAdmin()) {
    if (editBtn) { editBtn.style.display = ''; editBtn.onclick = function() { if (typeof navigateTo === 'function') navigateTo('identity', 'Identificacion'); }; }
    if (loginBtn) { loginBtn.innerHTML = '<span>Cerrar Sesion</span>'; loginBtn.title = 'Cerrar sesion de admin'; }
    var testBtn = document.getElementById('btnTestMode');
    if (testBtn) testBtn.style.display = '';
    var clearBtn = document.getElementById('btnClearHistory');
    if (clearBtn) clearBtn.style.display = '';
  } else {
    if (editBtn) { editBtn.style.display = 'none'; editBtn.onclick = null; }
    if (loginBtn) { loginBtn.innerHTML = '<span>Iniciar Sesion</span>'; loginBtn.title = 'Iniciar sesion para editar'; }
    var testBtn = document.getElementById('btnTestMode');
    if (testBtn) { testBtn.style.display = 'none'; testBtn.textContent = 'Modo Test'; testBtn.className = 'btn btn-outline btn-xs'; }
    var clearBtn = document.getElementById('btnClearHistory');
    if (clearBtn) clearBtn.style.display = 'none';
  }
}

// --- Login ---
function showLoginOverlay() {
  document.getElementById('loginOverlay').classList.remove('hidden');
  document.getElementById('loginError').textContent = '';
  document.getElementById('loginUser').value = '';
  document.getElementById('loginPass').value = '';
  document.getElementById('loginPass').type = 'password';
  document.getElementById('passToggle').textContent = 'Mostrar';
  // Actualizar con datos del proyecto
  var p = (typeof aboutData !== 'undefined' && aboutData.project) ? aboutData.project : {};
  var logo = (typeof aboutData !== 'undefined' && aboutData.logo) ? aboutData.logo : '';
  var logoImg = document.getElementById('loginLogoImg');
  var logoFallback = document.getElementById('loginLogoFallback');
  var titleEl = document.querySelector('#loginOverlay .login-header h2');
  if (logo && logoImg) {
    logoImg.src = (typeof staticAssetUrl === 'function') ? staticAssetUrl(logo) : '/static/' + logo + '?v=' + Date.now();
    logoImg.style.display = '';
    if (logoFallback) logoFallback.style.display = 'none';
  } else {
    if (logoImg) logoImg.style.display = 'none';
    if (logoFallback) {
      logoFallback.style.display = 'flex';
      logoFallback.textContent = (p.institution || 'CMA').substring(0, 3).toUpperCase();
    }
  }
  if (titleEl) titleEl.textContent = p.title || 'MeteoDash';
  setTimeout(function() { document.getElementById('loginUser').focus(); }, 100);
}

document.getElementById('loginClose').addEventListener('click', function() {
  document.getElementById('loginOverlay').classList.add('hidden');
});

document.getElementById('loginOverlay').addEventListener('click', function(e) {
  if (e.target === this) this.classList.add('hidden');
});

document.getElementById('passToggle').addEventListener('click', function() {
  var pass = document.getElementById('loginPass');
  var btn = document.getElementById('passToggle');
  if (pass.type === 'password') { pass.type = 'text'; btn.textContent = 'Ocultar'; }
  else { pass.type = 'password'; btn.textContent = 'Mostrar'; }
});

document.getElementById('btnLogin').addEventListener('click', async function() {
  var username = document.getElementById('loginUser').value.trim();
  var password = document.getElementById('loginPass').value.trim();
  var errEl = document.getElementById('loginError');
  if (!username || !password) { errEl.textContent = 'Completa ambos campos.'; return; }
  try {
    var resp = await fetch('/api/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username: username, password: password }) });
    if (resp.ok) {
      var data = await resp.json();
      authToken = data.token; authUser = data.user;
      localStorage.setItem('meteodash-token', authToken);
      localStorage.setItem('meteodash-user', JSON.stringify(authUser));
      document.getElementById('loginOverlay').classList.add('hidden');
      updateAdminUI();
      showToast('Sesion iniciada como admin', 'success');
      var ac = document.getElementById('aboutContent'); if (ac) ac.dataset.loaded = '';
    } else { errEl.textContent = 'Usuario o contrasena incorrectos.'; }
  } catch (e) { errEl.textContent = 'Error de conexion.'; }
});

document.getElementById('loginPass').addEventListener('keydown', function(e) {
  if (e.key === 'Enter') document.getElementById('btnLogin').click();
});

// --- Toast ---
function showToast(message, type) {
  type = type || 'info';
  var container = document.getElementById('toastContainer');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toastContainer';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }
  var icons = { success: '\u2713', error: '\u2717', info: 'i' };
  var toast = document.createElement('div');
  toast.className = 'toast ' + type;
  toast.innerHTML = '<span class="toast-icon">' + icons[type] + '</span><span>' + message + '</span>';
  container.appendChild(toast);
  setTimeout(function() { toast.remove(); }, 4000);
}
