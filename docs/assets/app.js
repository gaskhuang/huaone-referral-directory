(function () {
  "use strict";

  var MEMBERS = window.HUAONE_MEMBERS || [];
  var META = window.HUAONE_META || {};

  var elRows = document.getElementById("rows");
  var elChips = document.getElementById("chips");
  var elQ = document.getElementById("q");
  var elEmpty = document.getElementById("empty");
  var elCount = document.getElementById("resultCount");

  var state = { q: "", cat: "全部", open: null };

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function key(m) { return m.no + "-" + m.name + "-" + m.trade; }

  function haystack(m) {
    return [m.no, m.name, m.nickname, m.trade, m.company, m.category,
            m.basic, m.ideal, m.dream,
            (m.have || []).join(" "), (m.want || []).join(" "),
            (m.expertise || []).join(" ")].join(" ").toLowerCase();
  }

  MEMBERS.forEach(function (m) { m._hay = haystack(m); });

  /* ---------- header 資訊 ---------- */

  var src = document.getElementById("sourceLink");
  if (src && META.driveUrl) src.href = META.driveUrl;

  document.getElementById("statTotal").textContent = META.total || MEMBERS.length;
  document.getElementById("statComplete").textContent = META.complete || 0;
  document.getElementById("statCats").textContent = (META.categories || []).length;
  document.getElementById("statUpdated").textContent = (META.updated || "").slice(5).replace("-", "/");
  document.getElementById("footMeta").textContent =
    "資料同步自分會簡報雲端資料夾 · 最後更新 " + (META.updated || "");

  /* ---------- 分類 chips ---------- */

  function buildChips() {
    var counts = {};
    MEMBERS.forEach(function (m) { counts[m.category] = (counts[m.category] || 0) + 1; });
    var cats = Object.keys(counts).sort(function (a, b) { return counts[b] - counts[a]; });
    var html = chipHtml("全部", MEMBERS.length);
    cats.forEach(function (c) { html += chipHtml(c, counts[c]); });
    elChips.innerHTML = html;
  }

  function chipHtml(label, n) {
    return '<button class="chip' + (state.cat === label ? " is-active" : "") +
      '" data-cat="' + esc(label) + '">' + esc(label) +
      '<span class="count">' + n + "</span></button>";
  }

  /* ---------- 列表 ---------- */

  function tierBlock(cls, label, text) {
    if (!text) {
      return '<div class="tier ' + cls + '"><span class="tier-label">' + label +
        '</span><p class="tier-body" style="color:#a3a3a3;font-weight:600">簡報中尚未填寫</p></div>';
    }
    return '<div class="tier ' + cls + '"><span class="tier-label">' + label +
      '</span><p class="tier-body">' + esc(text) + "</p></div>";
  }

  function bulletBox(items, emptyText) {
    if (!items || !items.length) {
      return '<div class="bullet-box"><p class="muted-note" style="padding-left:0">' +
        emptyText + "</p></div>";
    }
    return '<div class="bullet-box">' +
      items.map(function (t) { return "<p>" + esc(t) + "</p>"; }).join("") + "</div>";
  }

  var ICON_SPARK = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 2.8a1 1 0 0 1 2 0l1 5.6a2 2 0 0 0 1.6 1.6l5.6 1a1 1 0 0 1 0 2l-5.6 1a2 2 0 0 0-1.6 1.6l-1 5.6a1 1 0 0 1-2 0l-1-5.6a2 2 0 0 0-1.6-1.6l-5.6-1a1 1 0 0 1 0-2l5.6-1a2 2 0 0 0 1.6-1.6z"></path></svg>';
  var ICON_USER = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m16 11 2 2 4-4"></path><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle></svg>';
  var ICON_CHEV = '<svg class="chev" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"></path></svg>';

  function detailHtml(m) {
    return '<tr class="row-detail"><td colspan="6">' +
      '<div class="detail-grid">' +
        "<div>" +
          '<div class="panel-title">' + ICON_SPARK + " BNI 三層精準引薦指標（I WILL）</div>" +
          '<div class="tiers">' +
            tierBlock("basic", "【一般引薦】做我生意／上下游合作", m.basic) +
            tierBlock("ideal", "【理想引薦】長期配合／指名合作對象", m.ideal) +
            tierBlock("dream", "【夢幻引薦】最想被引薦到的那個人", m.dream) +
          "</div>" +
        "</div>" +
        "<div class=\"side\">" +
          "<div>" +
            '<div class="panel-title muted">' + ICON_USER + " 我的專業</div>" +
            bulletBox(m.expertise, "簡報中尚未填寫專業簡介。") +
          "</div>" +
        "</div>" +
      "</div>" +
      '<div class="exchange">' +
        "<div><div class=\"panel-title muted\">本週我有（可以給出去的資源）</div>" +
          bulletBox(m.have, "本週未填寫。") + "</div>" +
        "<div><div class=\"panel-title muted\">本週我要（正在找的對象）</div>" +
          bulletBox(m.want, "本週未填寫。") + "</div>" +
      "</div>" +
      '<div class="detail-foot"><a class="slide-link" href="' + esc(m.slideUrl) +
        '" target="_blank" rel="noopener">開啟原始簡報 →</a></div>' +
      "</td></tr>";
  }

  function rowHtml(m) {
    var k = key(m);
    var open = state.open === k;
    var trade = m.trade
      ? '<span class="tag">' + esc(m.trade) + "</span>"
      : '<span class="pending">未填寫</span>';
    var company = m.company
      ? esc(m.company).replace(/\n/g, " · ")
      : '<span class="pending">未填寫</span>';
    var nick = m.nickname ? '<span class="nick">' + esc(m.nickname) + "</span>" : "";

    var html = '<tr class="row-main' + (open ? " is-open" : "") + '" data-key="' + esc(k) + '">' +
      '<td class="cell-no">' + esc(m.no) + "</td>" +
      '<td class="cell-name" data-label="姓名"><span class="star">★</span>' + esc(m.name) + nick + "</td>" +
      '<td data-label="專業別">' + trade + "</td>" +
      '<td class="cell-company" data-label="代表公司">' + company + "</td>" +
      '<td class="cell-cat" data-label="產業分類">' + esc(m.category) + "</td>" +
      '<td class="cell-chev">' + ICON_CHEV + "</td>" +
      "</tr>";

    return open ? html + detailHtml(m) : html;
  }

  function filtered() {
    var q = state.q.trim().toLowerCase();
    return MEMBERS.filter(function (m) {
      if (state.cat !== "全部" && m.category !== state.cat) return false;
      if (!q) return true;
      return m._hay.indexOf(q) !== -1;
    });
  }

  function render() {
    var list = filtered();
    elRows.innerHTML = list.map(rowHtml).join("");
    elEmpty.hidden = list.length > 0;
    elCount.textContent = "顯示 " + list.length + " / " + MEMBERS.length + " 位夥伴";
    Array.prototype.forEach.call(elChips.children, function (btn) {
      btn.classList.toggle("is-active", btn.dataset.cat === state.cat);
    });
  }

  /* ---------- 事件 ---------- */

  elChips.addEventListener("click", function (e) {
    var btn = e.target.closest(".chip");
    if (!btn) return;
    state.cat = btn.dataset.cat;
    state.open = null;
    render();
  });

  elRows.addEventListener("click", function (e) {
    var row = e.target.closest(".row-main");
    if (!row) return;
    var k = row.dataset.key;
    state.open = state.open === k ? null : k;
    render();
  });

  var t;
  elQ.addEventListener("input", function () {
    clearTimeout(t);
    t = setTimeout(function () {
      state.q = elQ.value;
      state.open = null;
      render();
    }, 120);
  });

  buildChips();
  render();
})();
