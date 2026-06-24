// ============================================================
// Sections: Navegación SPA, carga de contenido JSON,
// Acerca de, Identificación, Sidebar dinámica
// ============================================================

let appSettings = {};
let currentSection = 'dashboard';
let aboutData = {};

function staticAssetUrl(path) {
  if (!path) return '';
  return '/static/' + path + '?v=' + Date.now();
}

// --- Init ---
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', bootSections);
} else {
  bootSections();
}

function bootSections() {
  initNavigation();
  loadSettings();
  loadAboutData();
}

function initNavigation() {
  document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => {
      const section = item.dataset.section;
      const title = item.dataset.title;
      navigateTo(section, title);
    });
  });

  document.addEventListener('click', (e) => {
    const link = e.target.closest('a[data-nav]');
    if (link) {
      e.preventDefault();
      const section = link.dataset.nav;
      const navItem = document.querySelector(`.nav-item[data-section="${section}"]`);
      if (navItem) navigateTo(section, navItem.dataset.title);
    }
  });
}

function navigateTo(section, title) {
  if (currentSection === section) return;

  // Solo admin puede entrar a identidad
  if (section === 'identity' && typeof isAdmin === 'function' && !isAdmin()) return;

  document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
  const activeNav = document.querySelector(`.nav-item[data-section="${section}"]`);
  if (activeNav) activeNav.classList.add('active');

  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  const target = document.getElementById(`section-${section}`);
  if (target) target.classList.add('active');

  document.getElementById('sectionTitle').textContent = title || section;
  document.getElementById('sectionDesc').textContent = getSectionDesc(section);

  currentSection = section;

  if (section === 'components') loadComponents();
  if (section === 'help') loadHelp();
  if (section === 'about') loadAbout();
  if (section === 'identity') loadIdentity();

  document.getElementById('sidebar').classList.remove('open');
}

function getSectionDesc(section) {
  const descs = {
    dashboard: 'Monitoreo y control en tiempo real',
    about: 'Equipo, institución y proyecto',
    components: 'Hardware, pines y conexiones del sistema',
    help: 'Documentación, comandos y solución de problemas',
    identity: 'Editar datos del equipo e institución'
  };
  return descs[section] || '';
}

// --- About Data ---
async function loadAboutData() {
  let data = null;
  // Intentar API primero
  try {
    const resp = await fetch('/api/about');
    if (resp.ok) {
      data = await resp.json();
    }
  } catch (e) {
    console.warn('API /api/about no disponible, intentando archivo estatico...');
  }
  // Fallback a archivo estatico
  if (!data || !data.project) {
    try {
      const resp = await fetch('/static/config/about.json');
      if (resp.ok) {
        data = await resp.json();
      }
    } catch (e) {
      console.warn('No se pudo cargar about.json desde ninguna fuente');
      data = { project: {}, logo: '', team: [] };
    }
  }
  aboutData = data;
  populateSidebarBrand(aboutData);
  return aboutData;
}

function populateSidebarBrand(data) {
  const p = data.project || {};
  const logo = data.logo || '';

  // Title
  const titleEl = document.getElementById('brandTitle');
  if (titleEl) titleEl.textContent = p.title || 'MeteoDash';

  // Subtitle
  const subEl = document.getElementById('brandSubtitle');
  if (subEl) subEl.textContent = p.subtitle || 'Sistema Meteorológico';

  // School
  const schoolEl = document.getElementById('brandSchool');
  if (schoolEl) schoolEl.textContent = p.institution || '';

  // Course
  const courseEl = document.getElementById('brandCourse');
  if (courseEl) courseEl.textContent = p.course || '';

  // Logo
  const logoImg = document.getElementById('brandLogoImg');
  const fallback = document.getElementById('brandLogoFallback');
  if (logo && logoImg) {
    logoImg.src = staticAssetUrl(logo);
    logoImg.style.display = '';
    if (fallback) fallback.style.display = 'none';
  } else {
    if (logoImg) logoImg.style.display = 'none';
    if (fallback) {
      fallback.style.display = 'flex';
      fallback.textContent = (p.institution || 'CMA').substring(0, 3).toUpperCase();
    }
  }
}

// --- Windy ---
async function loadSettings() {
  try {
    const resp = await fetch('/static/config/settings.json');
    appSettings = await resp.json();
    initWindy();
  } catch (e) {
    appSettings = { windy: { lat: -25.3, lon: -57.633, zoom: 5 } };
    initWindy();
  }
}

function initWindy() {
  const w = appSettings.windy || {};
  const params = new URLSearchParams({
    type: 'map', location: 'coordinates',
    metricRain: w.metricRain || 'default',
    metricTemp: w.metricTemp || 'default',
    metricWind: w.metricWind || 'default',
    zoom: w.zoom || 5, overlay: w.overlay || 'satellite',
    product: w.product || 'ecmwf', level: w.level || 'surface',
    lat: w.lat || -25.3, lon: w.lon || -57.633
  });
  const frame = document.getElementById('windyFrame');
  if (frame) frame.src = 'https://embed.windy.com/embed.html?' + params.toString();
}

// --- Components ---
async function loadComponents() {
  const container = document.getElementById('componentsContent');
  if (!container || container.dataset.loaded) return;
  container.innerHTML = `
    <div class="comp-card"><div class="skeleton skeleton-text"></div><div class="skeleton skeleton-row"></div><div class="skeleton skeleton-row"></div></div>
    <div class="comp-card"><div class="skeleton skeleton-text"></div><div class="skeleton skeleton-row"></div><div class="skeleton skeleton-row"></div></div>
  `;
  try {
    const resp = await fetch('/static/config/components.json');
    const data = await resp.json();
    renderComponents(data, container);
    container.dataset.loaded = '1';
  } catch (e) {
    container.innerHTML = '<div class="card" style="text-align:center;padding:40px;color:var(--danger)">Error al cargar componentes.</div>';
  }
}

function renderComponents(data, container) {
  let html = '';

  html += `<div class="comp-card">
    <h3><span class="comp-icon">&#9733;</span> Bus I2C — Dispositivos Conectados</h3>
    <table class="comp-table"><thead><tr><th>Dispositivo</th><th>Dirección</th></tr></thead><tbody>`;
  (data.i2cDevices || []).forEach(d => {
    html += `<tr><td>${d.name}</td><td><span class="addr-code">${d.address}</span></td></tr>`;
  });
  html += `</tbody></table></div>`;

  html += `<div class="comp-card">
    <h3><span class="comp-icon">&#9745;</span> Sensores (${data.sensors.length})</h3>
    <table class="comp-table"><thead><tr><th>Sensor</th><th>Tipo</th><th>Pin</th><th>Protocolo</th><th>Rango</th></tr></thead><tbody>`;
  data.sensors.forEach(s => {
    const pinClass = s.pin.includes('A4') || s.pin.includes('A5') ? 'addr-code' : 'pin-code';
    html += `<tr><td><strong>${s.name}</strong></td><td>${s.type}</td><td><span class="${pinClass}">${s.pin}</span></td><td>${s.protocol}</td><td>${s.range}</td></tr>`;
    if (s.notes) html += `<tr><td colspan="5" style="font-size:0.72rem;color:var(--text-muted);padding-top:0">${s.notes}</td></tr>`;
  });
  html += `</tbody></table></div>`;

  html += `<div class="comp-card">
    <h3><span class="comp-icon">&#9881;</span> Módulos (${data.modules.length})</h3>
    <table class="comp-table"><thead><tr><th>Módulo</th><th>Tipo</th><th>Pin</th><th>Protocolo</th><th>Notas</th></tr></thead><tbody>`;
  data.modules.forEach(m => {
    html += `<tr><td><strong>${m.name}</strong></td><td>${m.type}</td><td><span class="pin-code">${m.pin}</span></td><td>${m.protocol}</td><td>${m.notes}</td></tr>`;
  });
  html += `</tbody></table></div>`;

  html += `<div class="comp-card">
    <h3><span class="comp-icon">&#9788;</span> Salidas — LEDs de Estado (${data.outputs.length})</h3>
    <table class="comp-table"><thead><tr><th>LED</th><th>Pin</th><th>Color</th><th>Función</th></tr></thead><tbody>`;
  data.outputs.forEach(o => {
    html += `<tr><td><strong>${o.name}</strong></td><td><span class="pin-code">${o.pin}</span></td><td>${o.color}</td><td>${o.function}</td></tr>`;
  });
  html += `</tbody></table></div>`;

  container.innerHTML = html;
}

// --- Help ---
async function loadHelp() {
  const container = document.getElementById('helpContent');
  if (!container || container.dataset.loaded) return;
  container.innerHTML = '<div class="help-block"><div class="skeleton skeleton-text"></div><div class="skeleton skeleton-text short"></div><div class="skeleton skeleton-text"></div></div>';
  try {
    const resp = await fetch('/static/config/help.json');
    const data = await resp.json();
    renderHelp(data, container);
    container.dataset.loaded = '1';
  } catch (e) {
    container.innerHTML = '<div class="card" style="text-align:center;padding:40px;color:var(--danger)">Error al cargar ayuda.</div>';
  }
}

function renderHelp(data, container) {
  let html = '';
  (data.sections || []).forEach(sec => {
    html += `<div class="help-block"><h3>${sec.title}</h3>`;
    if (sec.content) {
      html += '<ul>';
      sec.content.forEach(item => { html += `<li>${item}</li>`; });
      html += '</ul>';
    }
    html += `</div>`;
  });
  container.innerHTML = html;
}

// --- About (Acerca de) ---
async function loadAbout() {
  const container = document.getElementById('aboutContent');
  if (!container || container.dataset.loaded) return;
  container.innerHTML = '<div class="comp-card"><div class="skeleton skeleton-text"></div><div class="skeleton skeleton-row"></div><div class="skeleton" style="display:flex;gap:12px;align-items:center"><div class="skeleton skeleton-avatar"></div><div class="skeleton skeleton-text short"></div></div></div>';
  try {
    const data = await loadAboutData();
    renderAbout(data, container);
    container.dataset.loaded = '1';
  } catch (e) {
    container.innerHTML = '<div class="card" style="text-align:center;padding:40px;color:var(--danger)">Error al cargar datos.</div>';
  }
}

function renderAbout(data, container) {
  const p = data.project || {};
  const team = data.team || [];
  let html = '';

  html += `<div class="comp-card">
    <h3><span class="comp-icon">&#9733;</span> El Proyecto</h3>
    <table class="comp-table">
      <tbody>
        <tr><td><strong>Nombre</strong></td><td>${p.title || '—'}</td></tr>
        <tr><td><strong>Subtítulo</strong></td><td>${p.subtitle || '—'}</td></tr>
        <tr><td><strong>Curso / Bachiller</strong></td><td>${p.course || '—'}</td></tr>
        <tr><td><strong>Institución</strong></td><td>${p.institution || '—'}</td></tr>
      </tbody>
    </table>
  </div>`;

  html += `<div class="comp-card">
    <h3><span class="comp-icon">&#9813;</span> Equipo (${team.length} integrante${team.length !== 1 ? 's' : ''})</h3>`;

  if (team.length === 0) {
    html += '<p style="color:var(--text-muted);padding:12px">No hay integrantes registrados. Ve a <a href="#" data-nav="identity" style="color:var(--accent);font-weight:700">Identificación</a> para agregarlos.</p>';
  } else {
    team.forEach((member, idx) => {
      html += `<div class="member-card">
        <div class="member-header">`;
      if (member.avatar) {
        html += `<img src="${staticAssetUrl(member.avatar)}" class="member-avatar" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">`;
        html += `<span class="member-avatar" style="display:none">${(member.name || '?').charAt(0).toUpperCase()}</span>`;
      } else {
        html += `<span class="member-avatar">${(member.name || '?').charAt(0).toUpperCase()}</span>`;
      }
      html += `<div>
            <div class="member-name">${member.name || 'Sin nombre'}</div>
            <div class="member-role">${member.role || ''} &middot; ${member.course || ''}</div>
          </div>
        </div>`;
      if (member.bio) html += `<div class="member-bio">${member.bio}</div>`;
      if (member.skills && member.skills.length) {
        html += `<div class="member-skills">`;
        member.skills.forEach(s => { html += `<span class="skill-tag">${s}</span>`; });
        html += `</div>`;
      }
      html += `</div>`;
    });
  }
  html += `</div>`;

  container.innerHTML = html;
}

// --- Identity (Identificación - formulario editable) ---
async function loadIdentity() {
  const container = document.getElementById('identityContent');
  if (!container || container.dataset.loaded) return;
  container.innerHTML = '<div class="comp-card"><div class="skeleton skeleton-text"></div><div class="skeleton skeleton-row"></div><div class="skeleton skeleton-row"></div></div>';
  try {
    const data = aboutData.project ? aboutData : await loadAboutData();
    renderIdentity(data, container);
    container.dataset.loaded = '1';
  } catch (e) {
    container.innerHTML = '<div class="card" style="text-align:center;padding:40px;color:var(--danger)">Error al cargar editor.</div>';
  }
}

function renderIdentity(data, container) {
  const p = data.project || {};
  const team = data.team || [];
  const logo = data.logo || '';

  let html = '<div class="identity-form">';

  // Project info
  html += `<div class="comp-card">
    <h3><span class="comp-icon">&#9733;</span> Datos del Proyecto</h3>
    <div class="form-grid">
      <label>Título del Proyecto
        <input type="text" id="idProjTitle" value="${escAttr(p.title || '')}" placeholder="Sistema Meteorológico">
      </label>
      <label>Subtítulo
        <input type="text" id="idProjSub" value="${escAttr(p.subtitle || '')}" placeholder="con Dashboard">
      </label>
      <label>Curso / Bachiller
        <input type="text" id="idProjCourse" value="${escAttr(p.course || '')}" placeholder="BTI — Técnico en Informática">
      </label>
      <label>Institución / Colegio
        <input type="text" id="idProjInst" value="${escAttr(p.institution || '')}" placeholder="C.M.A.">
      </label>
      <label>Logo del Proyecto
        <div class="upload-row">
          <input type="file" id="idLogoFile" accept="image/*">
          <span id="idLogoStatus">${logo ? 'Logo cargado: ' + logo : 'Sin logo'}</span>
          <button class="btn btn-outline btn-xs" id="btnUploadLogo">Subir Logo</button>
        </div>
      </label>
    </div>
  </div>`;

  // Team
  html += `<div class="comp-card">
    <h3><span class="comp-icon">&#9813;</span> Integrantes del Equipo</h3>
    <div id="teamMembers"></div>
    <button class="btn btn-outline btn-xs" id="btnAddMember" style="margin-top:14px">+ Agregar Integrante</button>
  </div>`;

  // Save
  html += `<div style="margin-top:16px;display:flex;gap:10px">
    <button class="btn btn-primary" id="btnSaveIdentity">Guardar Cambios</button>
    <span id="idSaveStatus" style="font-family:var(--font-heading);font-size:0.78rem;letter-spacing:0.06em;align-self:center"></span>
  </div>`;

  html += '</div>';
  container.innerHTML = html;

  // Render team members
  renderTeamMembers(team);

  // Events
  document.getElementById('btnAddMember').addEventListener('click', () => {
    team.push({ name: '', role: '', course: '', bio: '', skills: [] });
    renderTeamMembers(team);
  });

  document.getElementById('btnUploadLogo').addEventListener('click', async () => {
    const fileInput = document.getElementById('idLogoFile');
    const file = fileInput.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    const resp = await authFetch('/api/upload-logo', { method: 'POST', body: formData });
    const result = await resp.json();
    if (result.path) {
      document.getElementById('idLogoStatus').textContent = 'Logo: ' + result.path;
      data.logo = result.path;
      populateSidebarBrand(data);
      if (typeof showToast === 'function') showToast('Logo subido. Pulsa Guardar Cambios para conservarlo.', 'success');
    }
  });

  document.getElementById('btnSaveIdentity').addEventListener('click', async () => {
    const newAbout = {
      project: {
        title: document.getElementById('idProjTitle').value.trim(),
        subtitle: document.getElementById('idProjSub').value.trim(),
        course: document.getElementById('idProjCourse').value.trim(),
        institution: document.getElementById('idProjInst').value.trim()
      },
      logo: data.logo,
      team: collectTeamData(team)
    };

    try {
      const resp = await authFetch('/api/about', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newAbout)
      });
      if (resp.ok) {
        aboutData = newAbout;
        populateSidebarBrand(newAbout);
        const aboutContainer = document.getElementById('aboutContent');
        if (aboutContainer) aboutContainer.dataset.loaded = '';
        document.getElementById('idSaveStatus').textContent = 'Guardado.';
        document.getElementById('idSaveStatus').style.color = 'var(--success)';
        if (typeof showToast === 'function') showToast('Datos guardados correctamente', 'success');
        setTimeout(() => { document.getElementById('idSaveStatus').textContent = ''; }, 3000);
      }
    } catch (e) {
      document.getElementById('idSaveStatus').textContent = 'Error al guardar.';
      document.getElementById('idSaveStatus').style.color = 'var(--danger)';
      if (typeof showToast === 'function') showToast('Error al guardar los datos', 'error');
    }
  });
}

function escAttr(str) {
  return String(str).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function renderTeamMembers(team) {
  const container = document.getElementById('teamMembers');
  if (!container) return;
  let html = '';
  team.forEach((m, i) => {
    html += `<div class="member-edit-card">
      <div class="member-edit-header">
        <span class="member-edit-num">#${i + 1}</span>
        <button class="btn-remove-member" data-idx="${i}" title="Eliminar integrante">&times;</button>
      </div>
      <div class="form-grid">
        <label>Nombre
          <input type="text" class="mem-name" value="${escAttr(m.name || '')}" placeholder="Nombre completo">
        </label>
        <label>Rol en el Proyecto
          <input type="text" class="mem-role" value="${escAttr(m.role || '')}" placeholder="Desarrollador, Diseñador...">
        </label>
        <label>Curso
          <input type="text" class="mem-course" value="${escAttr(m.course || '')}" placeholder="3er Año BTI">
        </label>
        <label>Biografía / Descripción
          <textarea class="mem-bio" rows="2" placeholder="Breve descripción del integrante...">${escAttr(m.bio || '')}</textarea>
        </label>
        <label>Habilidades (separadas por coma)
          <input type="text" class="mem-skills" value="${escAttr((m.skills || []).join(', '))}" placeholder="Arduino, Python, HTML">
        </label>
        <label>Foto de Perfil
          <div class="upload-row">
            <input type="file" class="mem-avatar-file" data-idx="${i}" accept="image/*">
            <button class="btn btn-outline btn-xs mem-avatar-btn" data-idx="${i}" type="button">Subir Foto</button>
            <span class="mem-avatar-status" data-idx="${i}">${m.avatar ? 'Foto: ' + m.avatar : 'Sin foto'}</span>
          </div>
          <input type="hidden" class="mem-avatar" value="${escAttr(m.avatar || '')}" data-idx="${i}">
        </label>
      </div>
    </div>`;
  });
  container.innerHTML = html;

  // Remove buttons
  container.querySelectorAll('.btn-remove-member').forEach(btn => {
    btn.addEventListener('click', () => {
      const idx = parseInt(btn.dataset.idx);
      team.splice(idx, 1);
      renderTeamMembers(team);
    });
  });

  // Avatar upload buttons
  container.querySelectorAll('.mem-avatar-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const idx = parseInt(btn.dataset.idx);
      const fileInput = container.querySelector(`.mem-avatar-file[data-idx="${idx}"]`);
      const file = fileInput.files[0];
      if (!file) return;
      const formData = new FormData();
      formData.append('file', file);
      const resp = await authFetch(`/api/upload-avatar/${idx}`, { method: 'POST', body: formData });
      if (resp.ok) {
        const result = await resp.json();
        team[idx].avatar = result.path;
        const statusEl = container.querySelector(`.mem-avatar-status[data-idx="${idx}"]`);
        if (statusEl) statusEl.textContent = 'Foto: ' + result.path;
        const hiddenEl = container.querySelector(`.mem-avatar[data-idx="${idx}"]`);
        if (hiddenEl) hiddenEl.value = result.path;
        if (typeof showToast === 'function') showToast('Foto subida: ' + result.path, 'success');
      } else {
        if (typeof showToast === 'function') showToast('Error al subir foto', 'error');
      }
    });
  });
}

function collectTeamData(team) {
  team = team || [];
  const members = [];
  document.querySelectorAll('.member-edit-card').forEach((card, i) => {
    members.push({
      name: card.querySelector('.mem-name')?.value.trim() || '',
      role: card.querySelector('.mem-role')?.value.trim() || '',
      course: card.querySelector('.mem-course')?.value.trim() || '',
      bio: card.querySelector('.mem-bio')?.value.trim() || '',
      skills: (card.querySelector('.mem-skills')?.value || '').split(',').map(s => s.trim()).filter(Boolean),
      avatar: (team[i] && team[i].avatar) || card.querySelector('.mem-avatar')?.value || ''
    });
  });
  return members;
}
