/**
 * ============================================================================
 * 🌸 DELICE PÂTISSERIE - LOGICA CLIENT (JAVASCRIPT)
 * ============================================================================
 */

const DeliceApp = {
    user: null,
    token: null,
    cart: [],
    scalerRecipeId: 1,
    scalerPortions: 10,
    currentAIRecipeId: null,

    init() {
        this.token = localStorage.getItem('delice_token');
        const userStr = localStorage.getItem('delice_user');
        if (this.token && userStr) {
            try {
                this.user = JSON.parse(userStr);
                this.verifySession();
            } catch (e) {
                this.logout();
            }
        } else {
            this.showLogin();
        }
    },

    async api(endpoint, method = 'GET', body = null) {
        const headers = {
            'Content-Type': 'application/json'
        };
        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        const options = { method, headers };
        if (body) {
            options.body = JSON.stringify(body);
        }

        const res = await fetch(endpoint, options);
        const data = await res.json();
        return { status: res.status, ok: res.ok, data };
    },

    async verifySession() {
        const res = await this.api('/api/auth/me');
        if (res.ok && res.data.authenticated) {
            this.user = res.data.user;
            this.showApp();
        } else {
            this.logout();
        }
    },

    fillLogin(username, password) {
        document.getElementById('loginUsername').value = username;
        document.getElementById('loginPassword').value = password;
        const alertBox = document.getElementById('loginAlertBox');
        if (alertBox) alertBox.style.display = 'none';
    },

    async handleLogin(e) {
        e.preventDefault();
        const username = document.getElementById('loginUsername').value.trim();
        const password = document.getElementById('loginPassword').value.trim();
        const alertBox = document.getElementById('loginAlertBox');

        alertBox.style.display = 'none';

        try {
            const res = await this.api('/api/auth/login', 'POST', { username, password });
            if (res.ok && res.data.success) {
                this.user = res.data.user;
                this.token = res.data.user.token;
                localStorage.setItem('delice_token', this.token);
                localStorage.setItem('delice_user', JSON.stringify(this.user));
                this.showApp();
            } else {
                alertBox.textContent = res.data.error || 'Autentificare eșuată!';
                alertBox.style.display = 'block';
            }
        } catch (err) {
            alertBox.textContent = 'Eroare de conexiune la server!';
            alertBox.style.display = 'block';
        }
    },

    logout() {
        localStorage.removeItem('delice_token');
        localStorage.removeItem('delice_user');
        this.user = null;
        this.token = null;
        this.cart = [];
        this.showLogin();
    },

    showLogin() {
        document.getElementById('loginSection').style.display = 'flex';
        document.getElementById('appHeader').style.display = 'none';
        document.getElementById('appMainContent').style.display = 'none';
    },

    showApp() {
        document.getElementById('loginSection').style.display = 'none';
        document.getElementById('appHeader').style.display = 'block';
        document.getElementById('appMainContent').style.display = 'block';

        // Profil
        document.getElementById('navUsername').textContent = this.user.nume;
        document.getElementById('navRole').textContent = this.user.rol.toUpperCase();
        document.getElementById('navAvatar').textContent = this.user.nume.charAt(0).toUpperCase();

        this.setupNavigation();
    },

    setupNavigation() {
        const navContainer = document.getElementById('roleNavigation');
        navContainer.innerHTML = '';

        // Ascundem toate sectiunile
        document.getElementById('adminView').classList.remove('active');
        document.getElementById('cofetarView').classList.remove('active');
        document.getElementById('vanzatorView').classList.remove('active');

        if (this.user.rol === 'administrator') {
            document.getElementById('adminView').classList.add('active');
            navContainer.innerHTML = `
                <button class="nav-pill-btn active" onclick="DeliceApp.switchAdminTab('alerte')">🔔 Alerte & Stocuri</button>
                <button class="nav-pill-btn" onclick="DeliceApp.switchAdminTab('catalog')">📦 Loturi FEFO</button>
                <button class="nav-pill-btn" onclick="DeliceApp.switchAdminTab('ai')">✨ Aprobare AI</button>
                <button class="nav-pill-btn" onclick="DeliceApp.switchAdminTab('rapoarte')">📊 Rapoarte (20)</button>
            `;
            this.loadAdminData();
        } else if (this.user.rol === 'cofetar') {
            document.getElementById('cofetarView').classList.add('active');
            navContainer.innerHTML = `
                <button class="nav-pill-btn active" onclick="DeliceApp.switchCofetarTab('sarcini')">📋 Tabloul Zilei</button>
                <button class="nav-pill-btn" onclick="DeliceApp.switchCofetarTab('scalare')">⚖️ Scalare Rețetar</button>
                <button class="nav-pill-btn" onclick="DeliceApp.switchCofetarTab('ai')">✨ Asistent Rețete AI</button>
            `;
            this.loadCofetarData();
        } else if (this.user.rol === 'vanzator') {
            document.getElementById('vanzatorView').classList.add('active');
            navContainer.innerHTML = `
                <button class="nav-pill-btn active" onclick="DeliceApp.switchVanzatorTab('pos')">🛒 Punct Vânzare (POS)</button>
                <button class="nav-pill-btn" onclick="DeliceApp.switchVanzatorTab('istoric')">📜 Istoric Comenzi</button>
            `;
            this.loadVanzatorData();
        }
    },

    /* =========================================================================
       MODUL ADMINISTRATOR
       ========================================================================= */

    switchAdminTab(tab) {
        document.getElementById('adminSubAlerte').style.display = tab === 'alerte' ? 'block' : 'none';
        document.getElementById('adminSubCatalog').style.display = tab === 'catalog' ? 'block' : 'none';
        document.getElementById('adminSubAI').style.display = tab === 'ai' ? 'block' : 'none';
        document.getElementById('adminSubRapoarte').style.display = tab === 'rapoarte' ? 'block' : 'none';

        document.getElementById('btnAdminTabAlerte').classList.toggle('active', tab === 'alerte');
        document.getElementById('btnAdminTabCatalog').classList.toggle('active', tab === 'catalog');
        document.getElementById('btnAdminTabAI').classList.toggle('active', tab === 'ai');
        document.getElementById('btnAdminTabRapoarte').classList.toggle('active', tab === 'rapoarte');

        if (tab === 'catalog') this.loadCatalogFEFO();
        if (tab === 'ai') this.loadReteteAIAdmin();
        if (tab === 'rapoarte') this.loadRapoarteAdmin();
    },

    async loadAdminData() {
        // KPI
        const statsRes = await this.api('/api/dashboard/stats');
        if (statsRes.ok) {
            document.getElementById('kpiCritice').textContent = statsRes.data.ingrediente_critice;
            document.getElementById('kpiExpirabile').textContent = statsRes.data.loturi_urgente;
            document.getElementById('kpiVenit').textContent = statsRes.data.venit_total.toFixed(2) + ' lei';
            document.getElementById('kpiReteteAI').textContent = statsRes.data.retete_ai_in_asteptare;
        }

        // Stocuri critice
        const criticeRes = await this.api('/api/stocuri/critice');
        const tbodyCritice = document.querySelector('#tableStocuriCritice tbody');
        tbodyCritice.innerHTML = '';
        if (criticeRes.ok && criticeRes.data.length > 0) {
            criticeRes.data.forEach(item => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>#${item.id_ingredient}</td>
                    <td><strong>${item.nume}</strong></td>
                    <td style="color: var(--danger); font-weight: 700;">${item.stoc_curent} ${item.unitate_masura}</td>
                    <td>${item.prag_minim} ${item.unitate_masura}</td>
                    <td>${item.unitate_masura}</td>
                    <td><span class="badge-pill badge-critic">🚨 Sub Prag</span></td>
                    <td>
                        <button class="btn-delice-sm btn-delice-primary" onclick="DeliceApp.openReceptieModal(${item.id_ingredient})">
                            Recepționează Marfă
                        </button>
                    </td>
                `;
                tbodyCritice.appendChild(tr);
            });
        } else {
            tbodyCritice.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--success); font-weight: 600;">Toate stocurile sunt în parametri optimi!</td></tr>`;
        }

        // Loturi urgente
        const urgenteRes = await this.api('/api/stocuri/loturi-urgente?zile=7');
        const tbodyUrgente = document.querySelector('#tableLoturiUrgente tbody');
        tbodyUrgente.innerHTML = '';
        if (urgenteRes.ok && urgenteRes.data.length > 0) {
            urgenteRes.data.forEach(item => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>#${item.id_lot}</td>
                    <td><strong>${item.ingredient}</strong></td>
                    <td>${item.cantitate_ramasa} ${item.unitate_masura}</td>
                    <td style="color: var(--warning); font-weight: 700;">${item.data_expirarii}</td>
                    <td>${item.furnizor}</td>
                `;
                tbodyUrgente.appendChild(tr);
            });
        } else {
            tbodyUrgente.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">Nu există loturi urgente care expiră în următoarele 7 zile.</td></tr>`;
        }

        // Incarcam si tabelul de aprobare AI ca sa fie gata instantaneu
        this.loadReteteAIAdmin();
    },

    async loadCatalogFEFO() {
        const res = await this.api('/api/stocuri/loturi-fefo');
        const tbody = document.querySelector('#tableLoturiFEFO tbody');
        tbody.innerHTML = '';
        if (res.ok && res.data.length > 0) {
            res.data.forEach(l => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>#${l.id_lot}</td>
                    <td><strong>${l.ingredient}</strong></td>
                    <td style="font-weight: 700;">${l.cantitate_ramasa} ${l.unitate_masura}</td>
                    <td>${l.data_receptiei}</td>
                    <td><span class="badge-pill badge-warning">📅 ${l.data_expirarii}</span></td>
                    <td>${l.furnizor}</td>
                `;
                tbody.appendChild(tr);
            });
        }
    },

    async loadReteteAIAdmin() {
        const res = await this.api('/api/retete/flux-ai');
        const tbody = document.querySelector('#tableReteteAIAdmin tbody');
        if (!tbody) return;
        tbody.innerHTML = '';
        if (res.ok && Array.isArray(res.data) && res.data.length > 0) {
            this.cachedPendingAIRecipes = res.data;
            res.data.forEach(r => {
                const tr = document.createElement('tr');
                const badgeClass = r.stare === 'verificata' ? 'badge-ok' : 'badge-warning';
                tr.innerHTML = `
                    <td>#${r.id_reteta}</td>
                    <td><strong>${r.reteta_propusa}</strong></td>
                    <td>${r.portii_baza} porții</td>
                    <td>${r.cofetar_solicitant || '-'}</td>
                    <td style="font-size: 0.85rem; color: var(--text-muted);">${r.ingrediente_trimise || '-'}</td>
                    <td><span class="badge-pill ${badgeClass}">${r.stare.toUpperCase()}</span></td>
                    <td>${r.data_generarii || '-'}</td>
                    <td>
                        <button class="btn-delice-sm btn-delice-primary" onclick="DeliceApp.openAprobaModal(${r.id_reteta})">
                            ✔️ Aprobă & Pune Preț
                        </button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        } else {
            tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">Nu există rețete AI în așteptarea aprobării.</td></tr>`;
        }
    },

    async loadRapoarteAdmin() {
        // 4.1 Top produse
        const topRes = await this.api('/api/rapoarte/top-produse');
        const tbodyTop = document.querySelector('#tableTopProduse tbody');
        tbodyTop.innerHTML = '';
        if (topRes.ok) {
            topRes.data.forEach(p => {
                const tr = document.createElement('tr');
                tr.innerHTML = `<td><strong>${p.produs}</strong></td><td>${p.bucati_vandute} buc</td><td style="color: var(--primary); font-weight: 700;">${p.total_incasat.toFixed(2)} lei</td>`;
                tbodyTop.appendChild(tr);
            });
        }

        // 4.3 Clienti fideli
        const fideliRes = await this.api('/api/rapoarte/clienti-fideli?prag=200');
        const tbodyFideli = document.querySelector('#tableClientiFideli tbody');
        tbodyFideli.innerHTML = '';
        if (fideliRes.ok) {
            fideliRes.data.forEach(c => {
                const tr = document.createElement('tr');
                tr.innerHTML = `<td><strong>${c.client}</strong></td><td>${c.telefon}</td><td>${c.numar_comenzi}</td><td style="color: var(--accent-gold); font-weight: 700;">${c.total_cheltuit.toFixed(2)} lei</td>`;
                tbodyFideli.appendChild(tr);
            });
        }

        // 4.4 Produse peste medie
        const medieRes = await this.api('/api/rapoarte/produse-peste-media');
        const tbodyMedie = document.querySelector('#tablePesteMedie tbody');
        tbodyMedie.innerHTML = '';
        if (medieRes.ok) {
            document.getElementById('textPretMediu').textContent = `Prețul mediu al catalogului: ${medieRes.data.pret_mediu} lei`;
            medieRes.data.produse.forEach(p => {
                const tr = document.createElement('tr');
                tr.innerHTML = `<td>${p.denumire}</td><td style="font-weight: 700;">${p.pret_vanzare.toFixed(2)} lei</td>`;
                tbodyMedie.appendChild(tr);
            });
        }

        // 3.2 Incarcare cofetari
        const cofetariRes = await this.api('/api/rapoarte/incarcare-cofetari');
        const tbodyCofetari = document.querySelector('#tableIncarcareCofetari tbody');
        tbodyCofetari.innerHTML = '';
        if (cofetariRes.ok) {
            cofetariRes.data.forEach(u => {
                const tr = document.createElement('tr');
                tr.innerHTML = `<td>👨‍🍳 <strong>${u.cofetar}</strong></td><td><span class="badge-pill badge-info">${u.sarcini_active} sarcini active</span></td>`;
                tbodyCofetari.appendChild(tr);
            });
        }
    },

    async openReceptieModal(idIngredientPrefill = null) {
        const [ingRes, furnRes] = await Promise.all([
            this.api('/api/stocuri/ingrediente'),
            this.api('/api/stocuri/furnizori')
        ]);

        const selIng = document.getElementById('recIngredient');
        selIng.innerHTML = '';
        if (ingRes.ok) {
            ingRes.data.forEach(i => {
                const opt = document.createElement('option');
                opt.value = i.id_ingredient;
                opt.textContent = `${i.nume} (${i.unitate_masura})`;
                if (idIngredientPrefill && i.id_ingredient === idIngredientPrefill) {
                    opt.selected = true;
                }
                selIng.appendChild(opt);
            });
        }

        const selFurn = document.getElementById('recFurnizor');
        selFurn.innerHTML = '';
        if (furnRes.ok) {
            furnRes.data.forEach(f => {
                const opt = document.createElement('option');
                opt.value = f.id_furnizor;
                opt.textContent = `${f.denumire} (Tel: ${f.telefon})`;
                selFurn.appendChild(opt);
            });
        }

        // Data expirarii implicita: +30 zile
        const date30 = new Date();
        date30.setDate(date30.getDate() + 30);
        document.getElementById('recDataExp').value = date30.toISOString().split('T')[0];
        document.getElementById('recCantitate').value = '';

        document.getElementById('modalReceptie').classList.add('active');
    },

    async handleReceptieSubmit(e) {
        e.preventDefault();
        const id_ingredient = parseInt(document.getElementById('recIngredient').value);
        const id_furnizor = parseInt(document.getElementById('recFurnizor').value);
        const cantitate = parseFloat(document.getElementById('recCantitate').value);
        const data_expirarii = document.getElementById('recDataExp').value;

        const res = await this.api('/api/stocuri/receptie-lot', 'POST', {
            id_ingredient, id_furnizor, cantitate, data_expirarii
        });

        if (res.ok) {
            this.closeModal('modalReceptie');
            alert("Lotul a fost recepționat cu succes! Triggerul bazei de date a actualizat automat stocul ingredientului.");
            this.loadAdminData();
        } else {
            alert(res.data.error || "Eroare la recepționarea mărfii!");
        }
    },

    openAprobaModal(idReteta, denumire = null) {
        let name = denumire;
        if (!name && this.cachedPendingAIRecipes) {
            const found = this.cachedPendingAIRecipes.find(r => r.id_reteta === idReteta);
            if (found) name = found.reteta_propusa;
        }
        document.getElementById('aprobareIdReteta').value = idReteta;
        document.getElementById('aprobareDenumire').value = name || ('Rețetă #' + idReteta);
        document.getElementById('aprobarePret').value = '45.00';
        document.getElementById('modalAprobaReteta').classList.add('active');
    },

    async handleAprobaRetetaSubmit(e) {
        e.preventDefault();
        const idReteta = document.getElementById('aprobareIdReteta').value;
        const pret = parseFloat(document.getElementById('aprobarePret').value);

        const res = await this.api(`/api/retete/${idReteta}/aproba`, 'POST', { pret_vanzare: pret });
        if (res.ok) {
            this.closeModal('modalAprobaReteta');
            alert("Rețeta a fost aprobată! Noul produs este acum activ în catalogul vânzătorilor.");
            this.loadReteteAIAdmin();
            this.loadAdminData();
        } else {
            alert(res.data.error || "Eroare la aprobarea rețetei!");
        }
    },

    closeModal(modalId) {
        document.getElementById(modalId).classList.remove('active');
    },

    /* =========================================================================
       MODUL COFETAR: TABLOU PRODUCȚIE, SCALARE & ASISTENT AI
       ========================================================================= */

    switchCofetarTab(tab) {
        document.getElementById('cofetarSubSarcini').style.display = tab === 'sarcini' ? 'block' : 'none';
        document.getElementById('cofetarSubScalare').style.display = tab === 'scalare' ? 'block' : 'none';
        document.getElementById('cofetarSubAI').style.display = tab === 'ai' ? 'block' : 'none';

        document.getElementById('btnCofetarSarcini').classList.toggle('active', tab === 'sarcini');
        document.getElementById('btnCofetarScalare').classList.toggle('active', tab === 'scalare');
        document.getElementById('btnCofetarAI').classList.toggle('active', tab === 'ai');

        if (tab === 'sarcini') this.loadCofetarSarcini();
        if (tab === 'scalare') this.loadCofetarScalare();
        if (tab === 'ai') this.loadCofetarAIView();
    },

    async loadCofetarData() {
        this.loadCofetarSarcini();
    },

    async loadCofetarSarcini() {
        const res = await this.api('/api/productie/sarcini');
        const container = document.getElementById('sarciniListContainer');
        container.innerHTML = '';

        if (res.ok && res.data.length > 0) {
            res.data.forEach(s => {
                const card = document.createElement('div');
                card.className = `production-task-card ${s.stare_sarcina}`;
                const isDone = s.stare_sarcina === 'gata';

                let personalizareBadge = '';
                if (s.text_personalizat || s.model_dorit) {
                    personalizareBadge = `<div style="margin-top: 6px; font-size: 0.85rem; color: var(--primary);">
                        🎀 <strong>Personalizare:</strong> "${s.text_personalizat || '-'}" | Model: <em>${s.model_dorit || '-'}</em>
                    </div>`;
                }

                card.innerHTML = `
                    <div>
                        <div class="task-title font-serif">${s.produs} (x${s.cantitate} buc)</div>
                        <div class="task-meta">
                            Comandă #${s.id_comanda} • Client: <strong>${s.client}</strong> • Programată pentru: ${s.data_productie}
                        </div>
                        ${personalizareBadge}
                    </div>
                    <div class="task-actions">
                        ${!isDone ? `
                            ${s.stare_sarcina === 'in_asteptare' ? `
                                <button class="btn-delice-sm btn-delice-outline" onclick="DeliceApp.setTaskState(${s.id_sarcina}, 'in_lucru')">
                                    👨‍🍳 Preia în Lucru
                                </button>
                            ` : ''}
                            <button class="btn-delice-sm btn-delice-success" onclick="DeliceApp.finalizeTaskFEFO(${s.id_sarcina})">
                                ✔️ Finalizează (Consum FEFO)
                            </button>
                        ` : `
                            <span class="badge-pill badge-ok">✅ Finalizată (Consum FEFO efectuat)</span>
                        `}
                    </div>
                `;
                container.appendChild(card);
            });
        } else {
            container.innerHTML = `<p style="color: var(--text-muted); text-align: center; padding: 2rem;">Nu există sarcini de producție pentru astăzi.</p>`;
        }
    },

    async setTaskState(idSarcina, stare) {
        const res = await this.api(`/api/productie/sarcini/${idSarcina}/stare`, 'POST', { stare });
        if (res.ok) {
            this.loadCofetarSarcini();
        }
    },

    async finalizeTaskFEFO(idSarcina) {
        if (!confirm("Confirmați finalizarea preparatului? Se va executa tranzacția FEFO de consum a materiilor prime din loturi.")) {
            return;
        }

        const res = await this.api(`/api/productie/sarcini/${idSarcina}/finalizeaza-fefo`, 'POST');
        if (res.ok && res.data.success) {
            let consumDetalii = res.data.consum_fefo.map(c => 
                `• ${c.ingredient}: -${c.cantitate_consumata} ${c.unitate_masura} (Lot #${c.id_lot}, exp: ${c.data_expirarii})`
            ).join('\n');

            alert(`🎉 ${res.data.mesaj}\n\nIngrediente scăzute automat din depozit:\n${consumDetalii}`);
            this.loadCofetarSarcini();
        } else {
            alert(res.data.error || "Eroare la scăderea stocului FEFO!");
        }
    },

    async loadCofetarScalare() {
        const reteteRes = await this.api('/api/retete');
        const sel = document.getElementById('scalerRecipeSelect');
        sel.innerHTML = '';
        if (reteteRes.ok) {
            reteteRes.data.forEach(r => {
                const opt = document.createElement('option');
                opt.value = r.id_reteta;
                opt.textContent = `${r.denumire} (Bază: ${r.portii_baza} porții)`;
                sel.appendChild(opt);
            });
            this.scalerRecipeId = reteteRes.data[0].id_reteta;
            this.scalerPortions = reteteRes.data[0].portii_baza;
            document.getElementById('scalerPortionsDisplay').textContent = this.scalerPortions;
            this.runRecipeScaling();
        }
    },

    handleScaleRecipeChange() {
        this.scalerRecipeId = parseInt(document.getElementById('scalerRecipeSelect').value);
        this.runRecipeScaling();
    },

    adjustScalerPortions(delta) {
        this.scalerPortions = Math.max(1, this.scalerPortions + delta);
        document.getElementById('scalerPortionsDisplay').textContent = this.scalerPortions;
        this.runRecipeScaling();
    },

    async runRecipeScaling() {
        if (!this.scalerRecipeId) return;
        const res = await this.api(`/api/retete/${this.scalerRecipeId}/scale?portii=${this.scalerPortions}`);
        const tbody = document.querySelector('#tableScalerResults tbody');
        tbody.innerHTML = '';

        if (res.ok && res.data) {
            res.data.ingrediente.forEach(ing => {
                const tr = document.createElement('tr');
                const badge = ing.stoc_suficient 
                    ? `<span class="badge-pill badge-ok">✔️ Stoc Suficient</span>`
                    : `<span class="badge-pill badge-critic">⚠️ Insuficient în Depozit</span>`;

                tr.innerHTML = `
                    <td><strong>${ing.nume}</strong></td>
                    <td>${ing.cantitate_baza} ${ing.unitate_masura}</td>
                    <td style="color: var(--primary); font-weight: 700; font-size: 1.05rem;">
                        ${ing.cantitate_scalata} ${ing.unitate_masura}
                    </td>
                    <td>${ing.stoc_curent} ${ing.unitate_masura}</td>
                    <td>${badge}</td>
                `;
                tbody.appendChild(tr);
            });
        }
    },

    async loadCofetarAIView() {
        const urgenteRes = await this.api('/api/stocuri/loturi-urgente?zile=7');
        const container = document.getElementById('aiExpiringIngredientsList');
        container.innerHTML = '';

        if (urgenteRes.ok && urgenteRes.data.length > 0) {
            const added = new Set();
            urgenteRes.data.forEach(item => {
                if (!added.has(item.ingredient)) {
                    added.add(item.ingredient);
                    const label = document.createElement('label');
                    label.style.display = 'flex';
                    label.style.alignItems = 'center';
                    label.style.gap = '8px';
                    label.style.fontSize = '0.88rem';
                    label.style.cursor = 'pointer';
                    label.innerHTML = `
                        <input type="checkbox" name="aiIngExp" value="${item.ingredient}" checked>
                        <span><strong>${item.ingredient}</strong> (rămas: ${item.cantitate_ramasa} ${item.unitate_masura}, exp: ${item.data_expirarii})</span>
                    `;
                    container.appendChild(label);
                }
            });
        } else {
            container.innerHTML = `<p style="font-size: 0.85rem; color: var(--text-muted);">Nu există loturi ce expiră în 7 zile. Puteți introduce ingrediente libere în câmpul de mai jos.</p>`;
        }

        // Incarcam si tabelul cu toate retetele AI generate salvate in baza de date
        this.loadCofetarAITable();
    },

    async loadCofetarAITable() {
        const res = await this.api('/api/retete/toate-ai');
        const tbody = document.querySelector('#tableCofetarAIRecipes tbody');
        if (!tbody) return;
        tbody.innerHTML = '';

        if (res.ok && res.data.length > 0) {
            res.data.forEach(r => {
                const tr = document.createElement('tr');
                let badge = '';
                if (r.stare === 'ciorna') {
                    badge = `<span class="badge-pill badge-warning">📝 Ciornă (Salvat)</span>`;
                } else if (r.stare === 'verificata') {
                    badge = `<span class="badge-pill badge-info">⏳ Verificată (Așteaptă Admin)</span>`;
                } else if (r.stare === 'aprobata') {
                    badge = `<span class="badge-pill badge-ok">🧁 Aprobată (${r.pret_vanzare ? r.pret_vanzare.toFixed(2) + ' lei' : 'Activă'})</span>`;
                }

                let actions = `
                    <button class="btn-delice-sm btn-delice-outline" onclick="DeliceApp.scaleSpecificRecipe(${r.id_reteta})">
                        ⚖️ Scalează
                    </button>
                `;

                if (r.stare === 'ciorna') {
                    actions = `
                        <button class="btn-delice-sm btn-delice-success" onclick="DeliceApp.submitRecipeToVerify(${r.id_reteta})">
                            ✔️ Trimite la Admin
                        </button>
                    ` + actions;
                }

                tr.innerHTML = `
                    <td><strong>#${r.id_reteta}</strong></td>
                    <td><strong>${r.denumire}</strong></td>
                    <td>${r.portii_baza} porții</td>
                    <td style="font-size: 0.82rem; color: var(--text-muted);">${r.ingrediente_trimise || '-'}</td>
                    <td style="font-size: 0.85rem;">${r.data_generarii || '-'}</td>
                    <td>${badge}</td>
                    <td style="display: flex; gap: 6px; flex-wrap: wrap;">${actions}</td>
                `;
                tbody.appendChild(tr);
            });
        } else {
            tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">Nu există încă rețete AI generate. Selectați ingredientele de mai sus și apăsați 'Generează Rețetă AI'!</td></tr>`;
        }
    },

    async scaleSpecificRecipe(idReteta) {
        this.switchCofetarTab('scalare');
        const sel = document.getElementById('scalerRecipeSelect');
        if (sel) {
            sel.value = idReteta;
            this.handleScaleRecipeChange();
        }
    },

    async generateAIRecipe() {
        const checkedBoxes = document.querySelectorAll('input[name="aiIngExp"]:checked');
        const ingredients = Array.from(checkedBoxes).map(cb => cb.value);

        const custom = document.getElementById('aiCustomIngredients').value.trim();
        if (custom) {
            custom.split(',').forEach(c => {
                if (c.trim()) ingredients.push(c.trim());
            });
        }

        if (ingredients.length === 0) {
            alert("Vă rugăm să selectați cel puțin un ingredient!");
            return;
        }

        const tip_desert = document.getElementById('aiDessertType').value;
        const resultCard = document.getElementById('aiResultCard');
        resultCard.style.display = 'block';
        document.getElementById('aiRecipeTitle').textContent = "Se generează rețeta... Vă rugăm așteptați 🍰";
        document.getElementById('aiRecipeInstructions').textContent = "Asistentul AI analizează ingredientele și elaborează pașii de lucru...";
        document.getElementById('aiRecipeIngredientsList').innerHTML = '';

        const res = await this.api('/api/ai/genereaza', 'POST', {
            ingrediente: ingredients,
            tip_desert
        });

        if (res.ok && res.data.success) {
            const data = res.data.data;
            const r = data.reteta;
            this.currentAIRecipeId = r.id_reteta;

            document.getElementById('aiRecipeTitle').textContent = r.denumire;
            document.getElementById('aiRecipeTime').textContent = (r.timp_minute || 50) + " min";
            document.getElementById('aiRecipePortions').textContent = r.portii_baza || 10;
            document.getElementById('aiSourceBadge').textContent = data.sursa === 'baza_de_date' ? 'Rețetă Existentă în DB' : 'Generată AI (Ciornă Salvată)';

            const listEl = document.getElementById('aiRecipeIngredientsList');
            listEl.innerHTML = '';
            (r.ingrediente || []).forEach(ing => {
                const li = document.createElement('li');
                li.innerHTML = `<strong>${ing.nume}</strong>: ${ing.cantitate} ${ing.unitate_masura}`;
                listEl.appendChild(li);
            });

            document.getElementById('aiRecipeInstructions').textContent = r.pasi_preparare || r.instructiuni || '-';
            document.getElementById('aiActionButtonsArea').style.display = data.sursa === 'baza_de_date' ? 'none' : 'block';

            // Actualizam instantaneu tabelul cu retetele AI si lista din scalator!
            this.loadCofetarAITable();
            this.loadCofetarScalare();
            
            // Scroll fin la reteta
            resultCard.scrollIntoView({ behavior: 'smooth' });
        } else {
            alert(res.data.error || "Eroare la generarea rețetei!");
        }
    },

    async submitRecipeToVerify(idRetetaParam = null) {
        const idReteta = idRetetaParam || this.currentAIRecipeId;
        if (!idReteta) return;
        const res = await this.api(`/api/retete/${idReteta}/trimite-verificare`, 'POST');
        if (res.ok) {
            alert("✅ Rețeta a fost verificată și trimisă administratorului pentru aprobare și stabilire de preț!");
            if (this.currentAIRecipeId === idReteta) {
                document.getElementById('aiActionButtonsArea').style.display = 'none';
            }
            this.loadCofetarAITable();
        } else {
            alert(res.data.error || "Eroare la trimiterea rețetei!");
        }
    },

    /* =========================================================================
       MODUL VÂNZĂTOR: POS TEJGHEA, VERIFICARE STOC & COMENZI
       ========================================================================= */

    switchVanzatorTab(tab) {
        document.getElementById('vanzatorSubPos').style.display = tab === 'pos' ? 'block' : 'none';
        document.getElementById('vanzatorSubIstoric').style.display = tab === 'istoric' ? 'block' : 'none';

        document.getElementById('btnPosVanzare').classList.toggle('active', tab === 'pos');
        document.getElementById('btnPosIstoric').classList.toggle('active', tab === 'istoric');

        if (tab === 'pos') this.loadPosProducts();
        if (tab === 'istoric') this.loadOrdersHistory();
    },

    async loadVanzatorData() {
        this.loadPosProducts();
    },

    async loadPosProducts() {
        const res = await this.api('/api/produse/active');
        const grid = document.getElementById('posProductsGrid');
        grid.innerHTML = '';

        if (res.ok && res.data.length > 0) {
            const emojis = ['🎂', '🧁', '🍰', '🥧', '🍮', '🍩', '🍪'];
            res.data.forEach((p, idx) => {
                const card = document.createElement('div');
                card.className = 'product-item-card';
                card.onclick = () => DeliceApp.addToCart(p);
                card.innerHTML = `
                    <div class="product-emoji">${emojis[idx % emojis.length]}</div>
                    <div class="product-card-title font-serif"><strong>${p.denumire}</strong></div>
                    <div class="product-card-price">${p.pret_vanzare.toFixed(2)} lei</div>
                    <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 4px;">+ Adaugă în coș</div>
                `;
                grid.appendChild(card);
            });
        }
    },

    addToCart(product) {
        const existing = this.cart.find(item => item.id_produs === product.id_produs);
        if (existing) {
            existing.cantitate += 1;
        } else {
            this.cart.push({
                id_produs: product.id_produs,
                denumire: product.denumire,
                pret_vanzare: product.pret_vanzare,
                cantitate: 1
            });
        }
        this.renderCart();
    },

    updateCartQty(idProdus, delta) {
        const item = this.cart.find(i => i.id_produs === idProdus);
        if (item) {
            item.cantitate += delta;
            if (item.cantitate <= 0) {
                this.cart = this.cart.filter(i => i.id_produs !== idProdus);
            }
        }
        this.renderCart();
    },

    renderCart() {
        const container = document.getElementById('cartItemsContainer');
        const errorAlert = document.getElementById('posStockErrorAlert');
        errorAlert.style.display = 'none';

        if (this.cart.length === 0) {
            container.innerHTML = `<p style="color: var(--text-muted); font-size: 0.88rem; text-align: center; padding: 2rem 0;">Nu ați adăugat încă niciun produs. Apăsați pe prăjiturile din stânga!</p>`;
            document.getElementById('cartTotalPrice').textContent = '0.00 lei';
            return;
        }

        let total = 0;
        container.innerHTML = '';
        this.cart.forEach(item => {
            const subtotal = item.cantitate * item.pret_vanzare;
            total += subtotal;

            const row = document.createElement('div');
            row.className = 'cart-item-row';
            row.innerHTML = `
                <div>
                    <strong>${item.denumire}</strong>
                    <div style="font-size: 0.8rem; color: var(--text-muted);">${item.pret_vanzare.toFixed(2)} lei / buc</div>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <button class="stepper-btn" style="width: 26px; height: 26px; font-size: 0.9rem;" onclick="DeliceApp.updateCartQty(${item.id_produs}, -1)">-</button>
                    <strong>${item.cantitate}</strong>
                    <button class="stepper-btn" style="width: 26px; height: 26px; font-size: 0.9rem;" onclick="DeliceApp.updateCartQty(${item.id_produs}, 1)">+</button>
                    <span style="font-weight: 700; min-width: 65px; text-align: right;">${subtotal.toFixed(2)} lei</span>
                </div>
            `;
            container.appendChild(row);
        });

        document.getElementById('cartTotalPrice').textContent = total.toFixed(2) + ' lei';
    },

    async handleClientSearch() {
        const tel = document.getElementById('posClientPhone').value.trim();
        const badge = document.getElementById('clientStatusBadge');
        if (tel.length >= 7) {
            const res = await this.api(`/api/clienti/cauta?telefon=${tel}`);
            if (res.ok && res.data.gasit) {
                document.getElementById('posClientName').value = res.data.client.nume;
                badge.innerHTML = `<span style="color: var(--success); font-weight: 600;">✔️ Client recurent: ${res.data.client.nume}</span>`;
            } else {
                badge.innerHTML = `<span style="color: var(--info); font-weight: 600;">ℹ️ Cumpărător nou (se va salva automat)</span>`;
            }
        } else {
            badge.innerHTML = '';
        }
    },

    handleOrderTypeChange() {
        const tip = document.getElementById('posOrderType').value;
        document.getElementById('posCustomFieldsArea').style.display = tip === 'custom' ? 'block' : 'none';
    },

    async submitOrder() {
        if (this.cart.length === 0) {
            alert("Adăugați cel puțin un produs în comandă!");
            return;
        }

        const tel = document.getElementById('posClientPhone').value.trim();
        const nume = document.getElementById('posClientName').value.trim() || 'Client Tejghea';
        const tip = document.getElementById('posOrderType').value;
        const text_personalizat = document.getElementById('posCustomText').value.trim();
        const model_dorit = document.getElementById('posCustomModel').value.trim();
        const data_livrare = document.getElementById('posDeliveryDate').value;
        const errorAlert = document.getElementById('posStockErrorAlert');

        errorAlert.style.display = 'none';

        const payload = {
            client: { nume, telefon: tel || '0700000000' },
            produse: this.cart.map(c => ({ id_produs: c.id_produs, cantitate: c.cantitate })),
            tip,
            text_personalizat,
            model_dorit,
            data_livrare
        };

        const res = await this.api('/api/comenzi/plasare', 'POST', payload);
        if (res.ok && res.data.success) {
            alert(`🎉 Comandă #${res.data.id_comanda} plasată cu succes!\n\nVerificarea atomică a stocurilor a confirmat disponibilitatea ingredientelor. Sarcina a fost transmisă în laborator!`);
            this.cart = [];
            this.renderCart();
            document.getElementById('posCustomText').value = '';
            document.getElementById('posCustomModel').value = '';
        } else {
            // ROLLBACK atomic declansat de stoc insuficient!
            errorAlert.textContent = `❌ ${res.data.error || 'Eroare la salvarea comenzii!'}`;
            errorAlert.style.display = 'block';
        }
    },

    async loadOrdersHistory() {
        const res = await this.api('/api/comenzi');
        const tbody = document.querySelector('#tableOrdersHistory tbody');
        tbody.innerHTML = '';

        if (res.ok && res.data.length > 0) {
            res.data.forEach(c => {
                const tr = document.createElement('tr');
                const badgeStare = c.stare === 'finalizata' ? 'badge-ok' : (c.stare === 'in_productie' ? 'badge-warning' : 'badge-info');
                tr.innerHTML = `
                    <td><strong>#${c.id_comanda}</strong></td>
                    <td>${c.data_livrare}</td>
                    <td><strong>${c.client}</strong><br><span style="font-size: 0.78rem; color: var(--text-muted);">${c.telefon_client}</span></td>
                    <td>${c.tip === 'custom' ? '🎀 Custom' : '⚡ Rapidă'}</td>
                    <td style="font-size: 0.85rem;">${c.text_personalizat || c.model_dorit ? `"${c.text_personalizat || '-'}" (${c.model_dorit || '-'})` : '-'}</td>
                    <td><span class="badge-pill ${badgeStare}">${c.stare.toUpperCase()}</span></td>
                    <td style="font-weight: 700; color: var(--primary);">${c.valoare_totala.toFixed(2)} lei</td>
                `;
                tbody.appendChild(tr);
            });
        }
    }
};

document.addEventListener('DOMContentLoaded', () => {
    DeliceApp.init();
});
