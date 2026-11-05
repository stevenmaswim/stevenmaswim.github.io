// Live demo: the order-book engine, unchanged, running in the browser.
//
// Pyodide (CPython compiled to WebAssembly) loads only when the visitor
// clicks "Boot the engine". The engine files and bridge.py are fetched from
// this site and written into Pyodide's file system, then imported normally.

(function () {
  const root = document.getElementById("demo");
  if (!root) return;

  const PYODIDE = "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/";
  const BASE = new URL(root.dataset.base, location.href);
  const FILES = [
    "orderbook/__init__.py",
    "orderbook/book.py",
    "orderbook/engine.py",
    "orderbook/models.py",
    "bridge.py",
  ];

  const $ = (id) => document.getElementById(id);
  const boot = $("demo-boot");
  const ui = $("demo-ui");
  const ladder = $("ladder");
  const tape = $("tape");
  const stats = $("demo-stats");
  const status = $("demo-status");
  const form = $("order-form");
  const flowBtn = $("demo-flow");

  let bridge = null;
  let flow = null;
  let lastTrade = 0;

  const fmt = (p) => p.toFixed(2);
  const say = (msg) => { status.textContent = msg; };

  function loadScript(src) {
    return new Promise((resolve, reject) => {
      const s = document.createElement("script");
      s.src = src;
      s.onload = resolve;
      s.onerror = () => reject(new Error("could not load " + src));
      document.head.appendChild(s);
    });
  }

  async function start() {
    boot.disabled = true;
    try {
      boot.textContent = "Loading Python...";
      await loadScript(PYODIDE + "pyodide.js");
      const py = await loadPyodide({ indexURL: PYODIDE });

      boot.textContent = "Loading the engine...";
      py.FS.mkdirTree("/home/pyodide/orderbook");
      for (const f of FILES) {
        const res = await fetch(new URL(f, BASE));
        if (!res.ok) throw new Error("could not fetch " + f);
        py.FS.writeFile("/home/pyodide/" + f, await res.text());
      }
      bridge = py.pyimport("bridge");
      bridge.warm_up(400);

      boot.hidden = true;
      $("demo-note").hidden = true;
      ui.hidden = false;
      render();
      say("Engine running. 400 random orders are already in the book. Place your own, or start random flow.");
    } catch (err) {
      boot.disabled = false;
      boot.textContent = "Try again";
      say("Could not start the engine: " + err.message);
    }
  }

  function row(side, price, qty, cum, max) {
    const pct = Math.max(2, (cum / max) * 100);
    return `<div class="lv ${side}"><span class="bar" style="width:${pct}%"></span>` +
           `<span class="px">${fmt(price)}</span><span class="qty">${qty}</span></div>`;
  }

  function cumulative(levels) {
    let total = 0;
    return levels.map(([p, q]) => [p, q, (total += q)]);
  }

  function render() {
    const s = JSON.parse(bridge.state(8));
    const asks = cumulative(s.asks);
    const bids = cumulative(s.bids);
    const max = Math.max(1, ...asks.map((a) => a[2]), ...bids.map((b) => b[2]));
    const spread = s.best_bid != null && s.best_ask != null ? fmt(s.best_ask - s.best_bid) : "n/a";

    ladder.innerHTML =
      asks.slice().reverse().map(([p, q, c]) => row("ask", p, q, c, max)).join("") +
      `<div class="mid">spread ${spread}</div>` +
      bids.map(([p, q, c]) => row("bid", p, q, c, max)).join("");

    tape.innerHTML = s.trades.map(([id, p, q]) =>
      `<li class="${id > lastTrade ? "new" : ""}"><span>#${id}</span><span>${fmt(p)}</span><span>${q}</span></li>`
    ).join("");
    if (s.trades.length) lastTrade = s.trades[0][0];

    stats.textContent = `${s.orders.toLocaleString()} orders · ${s.trade_count.toLocaleString()} trades`;
    if (!form.price.value && s.best_bid != null) form.price.value = fmt(s.best_bid);
  }

  function place(event) {
    event.preventDefault();
    const side = form.side.value;
    const kind = form.kind.value;
    const qty = parseInt(form.qty.value, 10);
    const price = kind === "LIMIT" ? parseFloat(form.price.value) : null;
    const r = JSON.parse(bridge.submit(side, kind, qty, price));
    if (r.error) {
      say("The engine rejected it: " + r.error);
    } else {
      const fills = r.fills.length
        ? `filled ${r.filled} in ${r.fills.length} trade${r.fills.length > 1 ? "s" : ""} at ${r.fills.map((f) => fmt(f[0])).join(", ")}`
        : "no match yet";
      const rest = r.remaining > 0 && kind === "LIMIT" ? `; ${r.remaining} resting in the book` : "";
      say(`Order #${r.id} (${side} ${kind} ${qty}${price != null ? " @ " + fmt(price) : ""}): ${fills}${rest}.`);
    }
    render();
  }

  function toggleFlow() {
    if (flow) {
      clearInterval(flow);
      flow = null;
      flowBtn.textContent = "Start random flow";
      return;
    }
    flowBtn.textContent = "Stop random flow";
    flow = setInterval(() => {
      if (document.hidden) return;
      for (let i = 0; i < 3; i++) bridge.random_order();
      render();
    }, 400);
  }

  function reset() {
    if (flow) toggleFlow();
    bridge.reset();
    bridge.warm_up(400);
    lastTrade = 0;
    form.price.value = "";
    render();
    say("Fresh engine, 400 random orders in the book.");
  }

  form.kind.addEventListener("change", () => {
    form.price.disabled = form.kind.value === "MARKET";
  });
  boot.addEventListener("click", start);
  form.addEventListener("submit", place);
  flowBtn.addEventListener("click", toggleFlow);
  $("demo-reset").addEventListener("click", reset);

  // A link to #demo-run boots the engine straight away.
  if (location.hash === "#demo-run") start();
})();
