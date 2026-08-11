/* Исповедь Mini App — guest + staff */
(function () {
  const tg = window.Telegram && window.Telegram.WebApp;
  if (tg) {
    tg.ready();
    tg.expand();
    try { tg.setHeaderColor("#0c0c0e"); tg.setBackgroundColor("#0c0c0e"); } catch (_) {}
  }

  // API: ?api= | config.js | same origin on Bothost / any host serving /api
  const params = new URLSearchParams(location.search);
  function resolveApiBase() {
    if (params.get("api")) return params.get("api").replace(/\/$/, "");
    if (window.ISPOVED_API) return String(window.ISPOVED_API).replace(/\/$/, "");
    // same host as Mini App (https://ispoved.bothost.tech/app/ → origin)
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
    document.querySelectorAll(".tab").forEach((t) => {
      t.classList.toggle("active", t.dataset.go === viewId.replace("view-", ""));
    });
    // map home/promos/profile
    const map = { home: "home", promos: "promos", profile: "profile", staff: "staff" };
    const key = viewId.replace("view-", "");
    document.querySelectorAll(".tab").forEach((t) => {
      t.classList.toggle("active", t.dataset.go === key || (key === "home" && t.dataset.go === "home"));
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
          (v.why ? " · " + v.why : "") + "</div></div>" +
          "<div>" + right + "</div></div>"
        );
      }).join("");
      recent.innerHTML = items.slice(0, 3).map((v, i) => {
        const title = v.type === "visit" ? "Визит" : v.type || "Операция";
        return (
          '<div class="item" style="animation-delay:' + i * 0.03 + 's">' +
          "<div><div>" + title + "</div><div class=\"muted\">" + (v.at || "").slice(0, 16) +
          "</div></div><div>" + (v.earned ? "+" + pts(v.earned) : "") + "</div></div>"
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

  function go(name) {
    const map = {
      home: "view-home",
      history: "view-history",
      menu: "view-menu",
      promos: "view-promos",
      profile: "view-profile",
      staff: "view-staff",
      reg: "view-reg",
    };
    if (name === "history") loadHistory();
    if (name === "menu") loadMenu();
    show(map[name] || "view-home");
    if (["home", "promos", "profile", "staff"].includes(name)) {
      $("tabs").classList.remove("hidden");
    }
  }

  async function boot() {
    show("view-boot");
    const hasTg = !!(initData() || (tg && tg.initDataUnsafe && tg.initDataUnsafe.user));

    // Outside Telegram: show shell + status, no fake panic
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
      renderGuest(me.guest);
      $("tabs").classList.remove("hidden");
      if (state.role === "staff" || state.role === "admin" || state.role === "owner") {
        $("tab-staff").classList.remove("hidden");
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
          return true; // close
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

  boot();
})();
