/* Исповедь Mini App — guest + staff + director */
(function () {
  const tg = window.Telegram && window.Telegram.WebApp;
  if (tg) {
    tg.ready();
    tg.expand();
    try { tg.setHeaderColor("#0a090c"); tg.setBackgroundColor("#0a090c"); } catch (_) {}
  }

  const params = new URLSearchParams(location.search);
  function resolveApiBase() {
    if (params.get("api")) return params.get("api").replace(/\/$/, "");
    if (window.ISPOVED_API) return String(window.ISPOVED_API).replace(/\/$/, "");
    return "";
  }
  const API_BASE = resolveApiBase();

  const SOPD_HTML = `
    <p><b>Политика обработки персональных данных</b><br>
    Программа лояльности лаундж-бара «Исповедь»</p>
    <p>г. Пермь, ул. Николая Островского, 93Д<br>
    Telegram-бот карты лояльности</p>

    <h3>1. Кто обрабатывает данные</h3>
    <p>Оператор — заведение «Исповедь» (лаундж-бар). Обработка ведётся с помощью Telegram-бота и мини-приложения карты лояльности.</p>

    <h3>2. Какие данные мы получаем</h3>
    <ul>
      <li>имя и (если указана) фамилия;</li>
      <li>номер телефона (если вы его передали);</li>
      <li>дата рождения (если указали — для поздравления и бонуса);</li>
      <li>идентификатор и username в Telegram;</li>
      <li>номер карты лояльности, баланс бонусов, история визитов и начислений;</li>
      <li>технические данные работы бота (время обращений), без продажи третьим лицам.</li>
    </ul>

    <h3>3. Зачем</h3>
    <ul>
      <li>программа лояльности: бонусы, уровни, штампы, купоны;</li>
      <li>идентификация гостя в зале (QR / номер карты);</li>
      <li>уведомления о визитах, акциях, дне рождения (можно отключить);</li>
      <li>бронь и сообщения администрации (если вы ими пользуетесь);</li>
      <li>статистика для улучшения сервиса заведения.</li>
    </ul>

    <h3>4. Правовая основа</h3>
    <p>Согласие субъекта персональных данных, которое вы даёте при выпуске карты (галочка и кнопка «Выпустить карту» / «Принимаю»). Отзыв согласия — через сообщение директору в боте или администратору заведения; карта и бонусы при этом могут быть аннулированы.</p>

    <h3>5. Срок хранения</h3>
    <p>Пока вы участник программы лояльности. После отзыва согласия или запроса на удаление — в разумный срок, если иное не требуется законом.</p>

    <h3>6. Кому могут передаваться данные</h3>
    <p>Мы не продаём ваши данные. Доступ могут иметь сотрудники заведения (официант, администрация) в объёме, нужном для начисления бонусов. Технические площадки (Telegram, хостинг бота) обрабатывают данные только для работы сервиса.</p>

    <h3>7. Ваши права</h3>
    <p>Вы можете запросить уточнение данных, их удаление или копию через бота («Написать директору») или администрацию заведения.</p>

    <h3>8. Контакты</h3>
    <p>«Исповедь», Пермь, ул. Николая Островского, 93Д. Связь — через Telegram-бота программы лояльности.</p>

    <p class="muted">Текст подготовлен для работы сервиса. При необходимости заведение может заменить его официальной редакцией.</p>
  `;

  const state = {
    me: null,
    guest: null,
    role: "guest",
    staffGuest: null,
    canGrant: ["staff"],
    canManageOwners: false,
    assistant: true,
    aiHistory: [],
    aiBusy: false,
  };

  function initData() {
    return (tg && tg.initData) || params.get("initData") || "";
  }

  async function api(path, opts = {}) {
    const headers = Object.assign(
      { "Content-Type": "application/json" },
      opts.headers || {}
    );
    const id = initData();
    if (id) headers["X-Telegram-InitData"] = id;
    const url = (API_BASE || "") + path;
    const res = await fetch(url, {
      method: opts.method || "GET",
      headers,
      body: opts.body ? JSON.stringify(opts.body) : undefined,
    });
    const text = await res.text();
    let data;
    try { data = JSON.parse(text); } catch { data = { error: text || res.statusText }; }
    if (!res.ok) {
      const err = new Error(data.error || res.statusText);
      err.code = data.code;
      err.status = res.status;
      err.data = data;
      throw err;
    }
    return data;
  }

  function $(id) { return document.getElementById(id); }
  function show(viewId) {
    document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
    const el = $(viewId);
    if (el) el.classList.add("active");
    const key = viewId.replace("view-", "");
    document.querySelectorAll(".tab").forEach((t) => {
      t.classList.toggle("active", t.dataset.go === key);
    });
    if (tg && tg.HapticFeedback) {
      try { tg.HapticFeedback.selectionChanged(); } catch (_) {}
    }
  }

  function money(n) {
    return (Number(n) || 0).toLocaleString("ru-RU") + " ₽";
  }
  function pts(n) {
    return (Number(n) || 0).toLocaleString("ru-RU");
  }

  function renderStamps(count) {
    const box = $("stamps");
    box.innerHTML = "";
    for (let i = 0; i < 8; i++) {
      const d = document.createElement("div");
      const filled = i < 7 && i < count;
      const isGift = i === 7;
      d.className = "stamp" + (filled || (isGift && count >= 7) ? " filled" : "") + (isGift ? " gift" : "");
      d.style.animationDelay = i * 0.05 + "s";
      const icon = isGift ? "i-gift" : (filled ? "i-star" : "i-star-o");
      d.innerHTML = '<svg viewBox="0 0 24 24" width="20" height="20"><use href="#' + icon + '"/></svg>';
      box.appendChild(d);
    }
  }

  function renderGuest(g) {
    state.guest = g;
    if (!g) return;
    const first = (g.name || "Гость").split(" ")[0];
    $("hello-name").textContent = first + "!";
    $("bonus").textContent = pts(g.bonus);
    $("level-name").textContent = g.level?.name || "Гость";
    $("level-cb").textContent = "кэшбэк " + (g.level?.cashback || 5) + "%";
    $("free-count").textContent = g.free_hookah_pending || 0;
    renderStamps(g.stamp_count || 0);

    let pct = 100;
    let nextTxt = "Максимальный уровень 👑";
    if (g.next_level) {
      const prev = g.level?.from || 0;
      const need = g.next_level.from - prev;
      const done = (g.spent || 0) - prev;
      pct = need > 0 ? Math.min(100, Math.round((done / need) * 100)) : 100;
      const left = g.next_level.from - (g.spent || 0);
      nextTxt = "До «" + g.next_level.name + "» — " + money(left);
    }
    $("level-bar").style.width = pct + "%";
    $("level-next").textContent = nextTxt;

    $("p-name").textContent = [g.name, g.last_name].filter(Boolean).join(" ") || "Гость";
    $("p-phone").textContent = g.phone || "телефон не указан";
    $("p-card").textContent = g.card_pretty || g.card;
    $("avatar").textContent = (g.name || "И").charAt(0).toUpperCase();
    $("tile-hist").textContent = (g.visits || 0) + " визитов";

    const brand = g.brand || {};
    const al = $("addr-link");
    const addrLabel = (brand.addr || "Адрес") + (brand.phone ? " · " + brand.phone : "");
    const addrText = $("addr-text");
    if (addrText) addrText.textContent = addrLabel;
    else al.textContent = addrLabel;
    al.href = "https://yandex.ru/maps/?text=" + encodeURIComponent(
      (brand.city || "Пермь") + " " + (brand.addr || "")
    );
  }

  async function loadHistory() {
    try {
      const data = await api("/api/history");
      const items = data.items || [];
      const recent = $("recent-list");
      const full = $("history-list");
      if (!items.length) {
        recent.className = "list empty-hint";
        recent.textContent = "Здесь появится история ваших визитов";
        full.innerHTML = '<div class="empty-hint">Пока пусто</div>';
        return;
      }
      recent.className = "list";
      const html = items.map((v, i) => {
        const title = v.type === "visit" ? "Визит" : v.type === "signup" ? "Регистрация" : v.type || "Операция";
        const sub = (v.at || "").slice(0, 16);
        const right = v.earned
          ? "+" + pts(v.earned)
          : v.total
            ? money(v.total)
            : "";
        return (
          '<div class="item" style="animation-delay:' + i * 0.03 + 's">' +
          "<div><div>" + title + "</div><div class=\"muted\">" + sub +
          (v.why ? " · " + escapeHtml(v.why) : "") + "</div></div>" +
          "<div class=\"amt\">" + right + "</div></div>"
        );
      }).join("");
      recent.innerHTML = items.slice(0, 3).map((v, i) => {
        const title = v.type === "visit" ? "Визит" : v.type || "Операция";
        return (
          '<div class="item" style="animation-delay:' + i * 0.03 + 's">' +
          "<div><div>" + title + "</div><div class=\"muted\">" + (v.at || "").slice(0, 16) +
          "</div></div><div class=\"amt\">" + (v.earned ? "+" + pts(v.earned) : "") + "</div></div>"
        );
      }).join("");
      full.innerHTML = html;
    } catch (e) {
      console.warn(e);
    }
  }

  async function loadMenu() {
    try {
      const data = await api("/api/menu");
      const box = $("menu-list");
      box.innerHTML = (data.menu || []).map((cat) => {
        const items = (cat.items || []).map((it) => {
          return (
            '<div class="menu-item"><div><div>' + escapeHtml(it.t) + "</div>" +
            (it.d ? '<div class="desc">' + escapeHtml(it.d) + "</div>" : "") +
            '</div><div class="price">' + money(it.p) + "</div></div>"
          );
        }).join("");
        return '<div class="menu-cat">' + escapeHtml(cat.t) + "</div>" + items;
      }).join("");
    } catch (e) {
      $("menu-list").innerHTML = '<div class="empty-hint">Меню недоступно</div>';
    }
  }

  function escapeHtml(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  async function openQr() {
    $("qr-overlay").classList.remove("hidden");
    $("qr-num").textContent = state.guest?.card_pretty || "…";
    $("qr-img").removeAttribute("src");
    try {
      const data = await api("/api/qr");
      $("qr-img").src = "data:image/png;base64," + data.png_base64;
      $("qr-num").textContent = data.card_pretty || data.card;
      if (tg && tg.HapticFeedback) tg.HapticFeedback.impactOccurred("light");
    } catch (e) {
      $("qr-num").textContent = "Ошибка QR";
    }
  }

  function closeQr() {
    $("qr-overlay").classList.add("hidden");
  }

  function isDirector() {
    return state.role === "admin" || state.role === "owner";
  }

  function go(name) {
    const map = {
      home: "view-home",
      history: "view-history",
      menu: "view-menu",
      promos: "view-promos",
      profile: "view-profile",
      staff: "view-staff",
      admin: "view-admin",
      assistant: "view-assistant",
      reg: "view-reg",
    };
    if (name === "history") loadHistory();
    if (name === "menu") loadMenu();
    if (name === "admin") {
      if (!isDirector()) return;
      loadAdminStats();
    }
    if (name === "assistant") ensureAiWelcome();
    show(map[name] || "view-home");
    if (["home", "promos", "profile", "staff", "admin", "assistant"].includes(name)) {
      $("tabs").classList.remove("hidden");
    }
  }

  // ── AI assistant ───────────────────────────────────────
  function ensureAiWelcome() {
    const box = $("ai-chat");
    if (!box || box.dataset.ready) return;
    box.dataset.ready = "1";
    appendAiMsg(
      "bot",
      "Привет! Я помощник «Исповеди». Спросите про бонусы, 8-й кальян, адрес или вашу карту — или выберите подсказку сверху."
    );
  }

  function appendAiMsg(role, text, cls) {
    const box = $("ai-chat");
    if (!box) return null;
    const el = document.createElement("div");
    el.className = "ai-msg " + role + (cls ? " " + cls : "");
    el.textContent = text;
    box.appendChild(el);
    box.scrollTop = box.scrollHeight;
    return el;
  }

  async function sendAi(text) {
    text = (text || "").trim();
    if (!text || state.aiBusy) return;
    state.aiBusy = true;
    const btn = $("btn-ai-send");
    if (btn) btn.disabled = true;
    $("ai-input").value = "";
    appendAiMsg("user", text);
    const typing = appendAiMsg("bot", "Думаю…", "typing");
    try {
      const data = await api("/api/assistant", {
        method: "POST",
        body: {
          message: text,
          history: state.aiHistory.slice(-8),
        },
      });
      if (typing) typing.remove();
      const reply = data.reply || "…";
      appendAiMsg("bot", reply);
      state.aiHistory.push({ role: "user", content: text });
      state.aiHistory.push({ role: "assistant", content: reply });
      if (state.aiHistory.length > 16) {
        state.aiHistory = state.aiHistory.slice(-16);
      }
      if (tg && tg.HapticFeedback) {
        try { tg.HapticFeedback.notificationOccurred("success"); } catch (_) {}
      }
    } catch (e) {
      if (typing) typing.remove();
      appendAiMsg("bot", "Не смог ответить: " + (e.message || "ошибка"));
      if (tg && tg.HapticFeedback) {
        try { tg.HapticFeedback.notificationOccurred("error"); } catch (_) {}
      }
    } finally {
      state.aiBusy = false;
      if (btn) btn.disabled = false;
    }
  }

  // ── Admin ──────────────────────────────────────────────
  function showAdminPanel(name) {
    document.querySelectorAll(".admin-panel").forEach((p) => p.classList.add("hidden"));
    document.querySelectorAll(".admin-tab").forEach((t) => {
      t.classList.toggle("active", t.dataset.admin === name);
    });
    const el = $("admin-panel-" + name);
    if (el) el.classList.remove("hidden");
    if (name === "roles") loadRoles();
    if (name === "stats") loadAdminStats();
    if (name === "bot") loadAdminStats();
  }

  async function loadAdminStats() {
    try {
      const data = await api("/api/admin/stats");
      const s = data.stats || {};
      $("st-today-v").textContent = pts(s.today_visits);
      $("st-today-r").textContent = money(s.today_revenue);
      $("st-guests").textContent = pts(s.guests);
      $("st-active").textContent = pts(s.active30);
      $("st-revenue").textContent = money(s.revenue);
      $("st-liab").textContent = pts(s.liability);

      const levels = s.levels || [];
      const maxL = Math.max(1, ...levels.map((l) => l.count || 0));
      $("st-levels").innerHTML = levels.map((l) => {
        const w = Math.round(((l.count || 0) / maxL) * 100);
        return (
          '<div class="level-row"><span class="ln">' + escapeHtml(l.name) +
          '</span><div class="lb"><div class="lf" style="width:' + w +
          '%"></div></div><span class="lc">' + (l.count || 0) + "</span></div>"
        );
      }).join("") || '<div class="muted">Нет данных</div>';

      const top = s.top || [];
      $("st-top").innerHTML = top.length
        ? top.map((t, i) =>
            '<div class="item" style="animation-delay:' + i * 0.03 + 's">' +
            "<div>" + escapeHtml(t.name) + "</div><div class=\"amt\">×" + t.qty + "</div></div>"
          ).join("")
        : '<div class="empty-hint" style="padding:12px">Пока пусто</div>';

      const bot = data.bot || {};
      $("bot-name").textContent = bot.name ? "@" + bot.name : "—";
      $("bot-webapp").textContent = bot.webapp ? "вкл" : "выкл";
      $("bot-sheets").textContent = bot.sheets ? "подключены" : "нет";
      $("bot-maint").textContent = bot.maintenance ? "обслуживание" : "работа";

      const labels = { owner: "Владелец", admin: "Директор" };
      $("admin-role-pill").textContent = labels[data.role] || data.role || state.role;
    } catch (e) {
      console.warn("stats", e);
      if (e.status === 403) {
        $("st-guests").textContent = "!";
        $("level-next") && ($("level-next").textContent = e.message);
      }
    }
  }

  async function loadRoles() {
    try {
      const data = await api("/api/admin/roles");
      state.canGrant = data.can_grant || ["staff"];
      state.canManageOwners = !!data.can_manage_owners;

      const sel = $("role-want");
      const allowed = new Set(state.canGrant);
      Array.from(sel.options).forEach((opt) => {
        opt.disabled = !allowed.has(opt.value);
        opt.hidden = !allowed.has(opt.value);
      });
      // pick first allowed
      const first = state.canGrant[0] || "staff";
      if (!allowed.has(sel.value)) sel.value = first;

      $("roles-hint").textContent = state.canManageOwners
        ? "Владелец: выдача всех ролей, снятие любой (кроме последнего владельца)."
        : "Директор: выдача и снятие только официантов.";

      const icons = { owner: "👑", admin: "🎩", staff: "🧑‍🍳" };
      const items = data.items || [];
      $("roles-list").innerHTML = items.length
        ? items.map((r, i) => {
            const who = r.username
              ? "@" + r.username
              : r.tg_id
                ? "id " + r.tg_id
                : "—";
            const canRevoke =
              (state.role === "owner") ||
              (state.role === "admin" && r.role === "staff");
            return (
              '<div class="role-card" style="animation-delay:' + i * 0.04 + 's">' +
              '<div class="role-badge">' + (icons[r.role] || "•") + "</div>" +
              '<div class="ri"><div class="rt">' + escapeHtml(r.role_name || r.role) +
              (r.pending ? '<span class="pending-tag">ждёт /start</span>' : "") +
              '</div><div class="rs">' + escapeHtml(who) +
              (r.at ? " · " + String(r.at).slice(0, 10) : "") +
              "</div></div>" +
              (canRevoke
                ? '<button type="button" class="btn danger" data-revoke="' + r.id + '">Снять</button>'
                : "") +
              "</div>"
            );
          }).join("")
        : '<div class="empty-hint">Пока никого нет</div>';

      $("roles-list").querySelectorAll("[data-revoke]").forEach((btn) => {
        btn.addEventListener("click", () => revokeRole(btn.dataset.revoke));
      });
    } catch (e) {
      $("roles-list").innerHTML =
        '<div class="empty-hint">' + escapeHtml(e.message || "Ошибка") + "</div>";
    }
  }

  async function grantRole() {
    const role = $("role-want").value;
    const who = $("role-who").value.trim();
    if (!who) {
      alert("Укажите @username или Telegram ID");
      return;
    }
    const body = { role };
    if (/^\d{5,15}$/.test(who)) body.tg_id = parseInt(who, 10);
    else body.username = who.replace(/^@/, "");

    try {
      await api("/api/admin/roles/grant", { method: "POST", body });
      if (tg && tg.HapticFeedback) tg.HapticFeedback.notificationOccurred("success");
      $("role-who").value = "";
      loadRoles();
    } catch (e) {
      alert(e.message || "Ошибка");
      if (tg && tg.HapticFeedback) tg.HapticFeedback.notificationOccurred("error");
    }
  }

  async function revokeRole(id) {
    if (!confirm("Снять роль?")) return;
    try {
      await api("/api/admin/roles/revoke", { method: "POST", body: { id: parseInt(id, 10) } });
      if (tg && tg.HapticFeedback) tg.HapticFeedback.notificationOccurred("success");
      loadRoles();
    } catch (e) {
      alert(e.message || "Ошибка");
    }
  }

  async function linkRoles() {
    try {
      const data = await api("/api/admin/roles/link", { method: "POST", body: {} });
      alert("Связано: " + (data.linked || 0));
      loadRoles();
    } catch (e) {
      alert(e.message || "Ошибка");
    }
  }

  async function doBroadcast() {
    const text = $("broadcast-text").value.trim();
    if (!text) {
      alert("Введите текст");
      return;
    }
    if (!confirm("Отправить рассылку всем гостям?")) return;
    try {
      const data = await api("/api/admin/broadcast", { method: "POST", body: { text } });
      $("broadcast-result").textContent = data.message || "Запущено";
      $("broadcast-text").value = "";
      if (tg && tg.HapticFeedback) tg.HapticFeedback.notificationOccurred("success");
    } catch (e) {
      $("broadcast-result").textContent = "Ошибка: " + (e.message || e);
      if (tg && tg.HapticFeedback) tg.HapticFeedback.notificationOccurred("error");
    }
  }

  async function adminFindGuest() {
    const q = $("admin-guest-q").value.trim();
    if (!q) return;
    try {
      const data = await api("/api/admin/guest", { method: "POST", body: { q } });
      const items = data.items || [];
      $("admin-guest-list").innerHTML = items.length
        ? items.map((g) =>
            '<div class="item"><div><div><b>' + escapeHtml(g.name || "Гость") +
            "</b></div><div class=\"muted\">" + escapeHtml(g.card_pretty || g.card) +
            " · " + pts(g.bonus) + " бон. · " + escapeHtml(g.level?.name || "") +
            "</div></div></div>"
          ).join("")
        : '<div class="empty-hint">Не найдено</div>';
    } catch (e) {
      $("admin-guest-list").innerHTML =
        '<div class="empty-hint">' + escapeHtml(e.message || "Ошибка") + "</div>";
    }
  }

  async function boot() {
    show("view-boot");
    const hasTg = !!(initData() || (tg && tg.initDataUnsafe && tg.initDataUnsafe.user));

    if (!hasTg && !params.get("demo")) {
      try {
        const h = await api("/api/health");
        renderGuest({
          name: "Превью",
          bonus: 0,
          spent: 0,
          visits: 0,
          stamp_count: 0,
          free_hookah_pending: 0,
          card: "------",
          card_pretty: "--- ---",
          level: { name: "Гость", cashback: 5, from: 0 },
          next_level: { name: "Свой", from: 15000, cashback: 7 },
          brand: { city: "Пермь", addr: "ул. Николая Островского, 93Д", phone: "" },
        });
        $("tabs").classList.remove("hidden");
        go("home");
        $("hello-name").textContent = "открой в Telegram";
        $("level-next").textContent =
          "API: " + (h.bot ? "@" + h.bot : "ok") + " · карта и бонусы — только из бота";
      } catch (e) {
        show("view-boot");
        document.querySelector("#view-boot .boot-sub").textContent =
          "API недоступен. Обнови бота на Bothost.";
        document.querySelector("#view-boot .spinner").style.display = "none";
      }
      return;
    }

    try {
      const me = await api("/api/me");
      state.me = me;
      state.role = me.role || "guest";
      state.assistant = me.assistant !== false;
      renderGuest(me.guest);
      $("tabs").classList.remove("hidden");
      if (state.role === "staff" || state.role === "admin" || state.role === "owner") {
        $("tab-staff").classList.remove("hidden");
      }
      if (state.role === "admin" || state.role === "owner") {
        $("tab-admin").classList.remove("hidden");
        const labels = { owner: "Владелец", admin: "Директор" };
        $("admin-role-pill").textContent = labels[state.role] || state.role;
      }
      const incomplete = me.guest && !me.guest.profile_complete && !me.guest.phone;
      if (incomplete && !(me.guest.name && me.guest.name.length > 1)) {
        $("reg-name").value = me.guest.name || (tg?.initDataUnsafe?.user?.first_name || "");
        go("reg");
      } else {
        go("home");
        loadHistory();
      }
    } catch (e) {
      console.error(e);
      const msg = (e && e.message) ? e.message : "ошибка API";
      renderGuest({
        name: "Гость",
        bonus: 0,
        spent: 0,
        visits: 0,
        stamp_count: 0,
        free_hookah_pending: 0,
        card: "------",
        card_pretty: "--- ---",
        level: { name: "Гость", cashback: 5, from: 0 },
        next_level: { name: "Свой", from: 15000, cashback: 7 },
        brand: { city: "Пермь", addr: "ул. Николая Островского, 93Д", phone: "" },
      });
      $("tabs").classList.remove("hidden");
      go("home");
      $("level-next").textContent = "Связь: " + msg;
      if (tg && tg.showAlert) {
        try {
          tg.showAlert("Не удалось загрузить карту: " + msg + "\nЗакрой Mini App и открой снова. Если снова ошибка — обнови бота (Git) на Bothost.");
        } catch (_) {}
      }
    }
  }

  async function register() {
    const body = {
      name: $("reg-name").value.trim(),
      last_name: $("reg-last").value.trim(),
      phone: $("reg-phone").value.trim(),
      bday: $("reg-bday").value || "",
      sopd: $("reg-sopd").checked,
    };
    if (!body.name) {
      alert("Укажите имя");
      return;
    }
    if (!$("reg-sopd").checked) {
      alert("Нужно принять политику обработки данных (СОПД)");
      return;
    }
    try {
      const data = await api("/api/register", { method: "POST", body });
      renderGuest(data.guest);
      if (tg && tg.HapticFeedback) tg.HapticFeedback.notificationOccurred("success");
      go("home");
    } catch (e) {
      alert(e.message || "Ошибка");
    }
  }

  function openSopd(from) {
    state._sopdFrom = from || "reg";
    $("sopd-body").innerHTML = SOPD_HTML;
    show("view-sopd");
  }

  // Staff
  async function findGuest() {
    const q = $("staff-q").value.trim();
    if (!q) return;
    try {
      const data = await api("/api/staff/guest", { method: "POST", body: { q: q, card: q } });
      state.staffGuest = data.guest;
      $("staff-guest").classList.remove("hidden");
      $("staff-form").classList.remove("hidden");
      $("staff-guest").innerHTML =
        "<b>" + escapeHtml(data.guest.name || "Гость") + "</b><br>" +
        "Карта <code>" + escapeHtml(data.guest.card_pretty || data.guest.card) + "</code><br>" +
        "Бонусы: " + pts(data.guest.bonus) + " · " + escapeHtml(data.guest.level?.name || "") +
        " · штампы " + (data.guest.stamp_count || 0) + "/7";
      $("staff-result").textContent = "";
    } catch (e) {
      alert(e.message || "Не найден");
    }
  }

  async function doCheckout() {
    if (!state.staffGuest) return;
    const total = parseInt($("staff-total").value || "0", 10);
    const use_pts = parseInt($("staff-pts").value || "0", 10);
    const hookah = $("staff-hookah").checked;
    const key = (crypto.randomUUID && crypto.randomUUID()) ||
      ("k" + Date.now() + Math.random().toString(16).slice(2));
    try {
      const data = await api("/api/staff/checkout", {
        method: "POST",
        headers: { "Idempotency-Key": key },
        body: {
          gid: state.staffGuest.id,
          total,
          use_pts,
          hookah,
          idempotency_key: key,
        },
      });
      $("staff-result").textContent =
        (data.replay ? "Повтор (уже проведено)\n" : "OK\n") +
        "Начислено +" + pts((data.earned || 0) + (data.extra || 0)) +
        "\nБаланс " + pts(data.guest?.bonus) +
        (data.why ? "\n" + data.why : "");
      if (tg && tg.HapticFeedback) tg.HapticFeedback.notificationOccurred("success");
      state.staffGuest = data.guest;
    } catch (e) {
      $("staff-result").textContent = "Ошибка: " + (e.message || e);
      if (tg && tg.HapticFeedback) tg.HapticFeedback.notificationOccurred("error");
    }
  }

  function tryScan() {
    if (tg && tg.showScanQrPopup) {
      tg.showScanQrPopup({ text: "Наведите на QR карты гостя" }, (text) => {
        const m = String(text || "").match(/(\d{6})/);
        if (m) {
          $("staff-q").value = m[1];
          findGuest();
          return true;
        }
        return false;
      });
    } else {
      alert("Сканер доступен в мобильном Telegram. Введите номер карты вручную.");
    }
  }

  // Events
  document.querySelectorAll("[data-go]").forEach((el) => {
    el.addEventListener("click", (e) => {
      e.preventDefault();
      go(el.dataset.go);
    });
  });
  $("btn-qr").addEventListener("click", openQr);
  $("qr-close").addEventListener("click", closeQr);
  $("qr-overlay").addEventListener("click", (e) => {
    if (e.target === $("qr-overlay")) closeQr();
  });
  $("btn-register").addEventListener("click", register);
  $("btn-sopd-open").addEventListener("click", (e) => {
    e.preventDefault();
    openSopd("reg");
  });
  $("btn-sopd-profile").addEventListener("click", () => openSopd("profile"));
  $("btn-sopd-back").addEventListener("click", () => {
    go(state._sopdFrom === "profile" ? "profile" : "reg");
  });
  $("btn-sopd-accept").addEventListener("click", () => {
    $("reg-sopd").checked = true;
    if (tg && tg.HapticFeedback) {
      try { tg.HapticFeedback.notificationOccurred("success"); } catch (_) {}
    }
    go(state._sopdFrom === "profile" ? "profile" : "reg");
  });
  $("btn-contact").addEventListener("click", () => {
    if (tg && tg.requestContact) {
      tg.requestContact((ok, res) => {
        if (!ok) return;
        try {
          const p = res?.responseUnsafe?.contact?.phone_number ||
            res?.contact?.phone_number;
          if (p) $("reg-phone").value = p.startsWith("+") ? p : "+" + p;
        } catch (_) {}
      });
    } else {
      alert("Запрос контакта доступен внутри Telegram");
    }
  });
  $("btn-find").addEventListener("click", findGuest);
  $("btn-checkout").addEventListener("click", doCheckout);
  $("btn-scan").addEventListener("click", tryScan);

  // Admin events
  document.querySelectorAll("[data-admin]").forEach((el) => {
    el.addEventListener("click", () => showAdminPanel(el.dataset.admin));
  });
  $("btn-refresh-stats").addEventListener("click", loadAdminStats);
  $("btn-role-grant").addEventListener("click", grantRole);
  $("btn-role-link").addEventListener("click", linkRoles);
  $("btn-broadcast").addEventListener("click", doBroadcast);
  $("btn-admin-find").addEventListener("click", adminFindGuest);

  // AI
  $("btn-ai-send").addEventListener("click", () => sendAi($("ai-input").value));
  $("ai-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      sendAi($("ai-input").value);
    }
  });
  document.querySelectorAll("#ai-chips .chip").forEach((chip) => {
    chip.addEventListener("click", () => sendAi(chip.dataset.q || chip.textContent));
  });

  boot();
})();
