#!/usr/bin/env node
/*
 * dom_harness.js - run a tracker page's inline scripts in Node against a fake browser
 * and record what the page writes into the DOM. Used to prove a conversion renders
 * exactly like the original, and as a smoke test ("does the page throw?").
 *
 *   node dom_harness.js page.html                 -> prints a JSON report
 *   node dom_harness.js page.html --snaps out.json -> also saves values passed to __snap(name, value)
 *
 * Report: {errors:[...], writes:{key:value}, snaps:{...}}
 * Not a real browser: it records innerHTML/textContent/value/etc. writes on elements found by id,
 * selector or created by the page; it does not lay out or paint. External <script src> files are
 * NOT loaded (Chart and friends are stubbed); scripts marked data-vendor are skipped.
 */
const vm = require("vm");
const fs = require("fs");
const path = require("path");

const file = process.argv[2];
const snapIdx = process.argv.indexOf("--snaps");
const snapOut = snapIdx > 0 ? process.argv[snapIdx + 1] : null;
const html = fs.readFileSync(file, "utf8");
const baseDir = path.dirname(path.resolve(file));

const writes = {};
const errors = [];
const snaps = {};
const RECORDED = new Set(["innerHTML", "outerHTML", "textContent", "innerText", "value", "src", "href", "className", "title"]);

// ---------- universal stub: callable, constructible, any property, never throws
function stub(name, cacheable) {
  const store = Object.create(null);
  const fn = function () {};
  return new Proxy(fn, {
    get(t, k) {
      if (k === Symbol.toPrimitive) return (hint) => (hint === "number" ? 0 : "");
      if (k === Symbol.iterator) return function* () {};
      if (k === "then") return undefined; // not a promise
      if (k === "toString" || k === "valueOf") return () => "";
      if (k === "length") return k in store ? store[k] : 0;
      if (k in store) return store[k];
      if (typeof k === "symbol") return undefined;
      if (k === "style" || k === "dataset" || k === "classList") {
        store[k] = stub(name + "." + k);
        return store[k];
      }
      return stub(name + "." + k);
    },
    set(t, k, v) {
      store[k] = v;
      if (typeof k === "string" && RECORDED.has(k)) writes[name + "." + k] = String(v);
      return true;
    },
    apply() { return stub(name + "()"); },
    construct() { return stub("new " + name); },
    has() { return true; },
  });
}

// ---------- parse scripts out of the HTML
const scriptRe = /<script\b([^>]*)>([\s\S]*?)<\/script\s*>/gi;
const scripts = [];
let m;
while ((m = scriptRe.exec(html))) {
  const attrs = m[1] || "";
  scripts.push({
    attrs,
    code: m[2],
    src: /\bsrc\s*=/.test(attrs),
    vendor: /\bdata-vendor\b/.test(attrs),
    app: /\bdata-tracker-app\b/.test(attrs),
    type: ((attrs.match(/\btype\s*=\s*["']?([^"'\s>]+)/i) || [])[1] || "").toLowerCase(),
  });
}

// ---------- fake document / window
const elCache = new Map();
function cached(key) {
  if (!elCache.has(key)) elCache.set(key, stub(key));
  return elCache.get(key);
}
let createCount = 0;
let readyState = "loading";
const listeners = { document: {}, window: {} };
function addL(target) {
  return function (type, fn) { (listeners[target][type] = listeners[target][type] || []).push(fn); };
}
const context = {};
function execScript(code, label) {
  try {
    vm.runInContext(code, context, { filename: label });
  } catch (e) {
    errors.push(label + ": " + (e && e.message ? e.message : String(e)));
  }
}
function makeScriptEl() {
  return { tagName: "SCRIPT", text: "", textContent: "", setAttribute() {}, src: "" };
}
function append(child) {
  if (child && child.tagName === "SCRIPT") execScript(child.text || child.textContent || "", "injected-script");
  return child;
}
const body = new Proxy(stub("body"), {
  get(t, k) {
    if (k === "appendChild") return append;
    if (k === "insertBefore") return (c) => append(c);
    return t[k];
  },
});
const appBlocks = scripts.filter((s) => s.app).map((s) => ({ textContent: s.code, text: s.code }));
const document = {
  get readyState() { return readyState; },
  body,
  head: body,
  documentElement: stub("html"),
  getElementById: (id) => cached("#" + id),
  querySelector: (sel) => cached("q(" + sel + ")"),
  querySelectorAll: (sel) => {
    if (/data-tracker-app/.test(sel)) return appBlocks;
    if (/\.snapdate\b/.test(sel)) return [cached("snapdate")];
    return [];
  },
  getElementsByClassName: () => [],
  getElementsByTagName: (t) => (String(t).toLowerCase() === "body" ? [body] : []),
  createElement: (tag) => (String(tag).toLowerCase() === "script" ? makeScriptEl() : stub("new:" + tag + "#" + ++createCount)),
  createTextNode: () => stub("text"),
  createDocumentFragment: () => stub("frag"),
  addEventListener: addL("document"),
  removeEventListener() {},
  write: (s) => errors.push("document.write used (not supported after conversion): " + String(s).slice(0, 60)),
  title: "",
  cookie: "",
};
const storage = () => {
  const m = new Map();
  return { getItem: (k) => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, String(v)), removeItem: (k) => m.delete(k), clear: () => m.clear() };
};
const ChartStub = stub("Chart");

Object.assign(context, {
  document,
  console: { log() {}, info() {}, warn() {}, debug() {}, error: (...a) => errors.push("console.error: " + a.map(String).join(" ").slice(0, 300)) },
  setTimeout, clearTimeout, setInterval: () => 0, clearInterval() {},
  requestAnimationFrame: (f) => setTimeout(() => f(0), 0),
  cancelAnimationFrame() {},
  queueMicrotask,
  localStorage: storage(),
  sessionStorage: storage(),
  navigator: { userAgent: "node-harness", language: "en-US", clipboard: stub("clipboard") },
  location: { href: "file://" + file, search: "", hash: "", pathname: "/index.html", reload() {} },
  history: stub("history"),
  matchMedia: () => ({ matches: false, addListener() {}, addEventListener() {}, removeListener() {} }),
  getComputedStyle: () => stub("computedStyle"),
  addEventListener: addL("window"),
  removeEventListener() {},
  alert() {}, confirm: () => true, prompt: () => null,
  Chart: ChartStub,
  ResizeObserver: function () { return { observe() {}, disconnect() {} }; },
  IntersectionObserver: function () { return { observe() {}, disconnect() {} }; },
  MutationObserver: function () { return { observe() {}, disconnect() {} }; },
  Intl, URL, URLSearchParams, TextEncoder, TextDecoder, structuredClone,
  __snap: (name, value) => {
    try { snaps[name] = { ok: true, value: JSON.parse(JSON.stringify(value)), unsafe: unsafeReason(value) }; }
    catch (e) { snaps[name] = { ok: false, error: String(e.message) }; }
  },
  fetch: (url) => {
    const p = path.join(baseDir, String(url).split("?")[0]);
    const ok = fs.existsSync(p);
    return Promise.resolve({
      ok, status: ok ? 200 : 404,
      json: () => Promise.resolve(JSON.parse(fs.readFileSync(p, "utf8"))),
      text: () => Promise.resolve(fs.readFileSync(p, "utf8")),
    });
  },
});
context.window = context;
context.self = context;
context.globalThis = context;
vm.createContext(context);

// JSON round-trip loses functions, undefined, NaN/Infinity, Dates, Maps, class instances, holes
function unsafeReason(v, seen = new Set(), p = "$") {
  if (v === null) return null;
  const t = typeof v;
  if (t === "function") return p + " is a function";
  if (t === "undefined") return p + " is undefined";
  if (t === "bigint" || t === "symbol") return p + " is a " + t;
  if (t === "number") return Number.isFinite(v) ? null : p + " is " + v;
  if (t !== "object") return null;
  if (seen.has(v)) return p + " is a circular reference";
  seen.add(v);
  if (Array.isArray(v)) {
    for (let i = 0; i < v.length; i++) {
      if (!(i in v)) return p + "[" + i + "] is a hole";
      const r = unsafeReason(v[i], seen, p + "[" + i + "]");
      if (r) return r;
    }
    return null;
  }
  const proto = Object.getPrototypeOf(v);
  // plain object = its prototype is some realm's Object.prototype (whose own prototype is null)
  if (proto !== null && Object.getPrototypeOf(proto) !== null) return p + " is a " + ((v.constructor && v.constructor.name) || "non-plain object");
  for (const k of Object.keys(v)) {
    const r = unsafeReason(v[k], seen, p + "." + k);
    if (r) return r;
  }
  return null;
}

// ---------- run like a browser: inline scripts in order, then DOMContentLoaded, then load
function fire(target, type) {
  for (const fn of listeners[target][type] || []) {
    try { fn.call(target === "window" ? context : document, { type, target: document, preventDefault() {} }); }
    catch (e) { errors.push(type + " handler: " + e.message); }
  }
}
scripts.forEach((s, i) => {
  if (s.src || s.vendor || s.app) return;
  if (s.type && !["text/javascript", "application/javascript", "module"].includes(s.type)) return;
  execScript(s.code, "inline-script-" + (i + 1));
});
const settle = (ms) => new Promise((r) => setTimeout(r, ms));
(async () => {
  await settle(20);
  readyState = "interactive";
  fire("document", "DOMContentLoaded");
  fire("window", "DOMContentLoaded");
  await settle(150);
  readyState = "complete";
  fire("window", "load");
  if (typeof context.onload === "function") { try { context.onload({ type: "load" }); } catch (e) { errors.push("onload: " + e.message); } }
  await settle(250);
  if (snapOut) fs.writeFileSync(snapOut, JSON.stringify(snaps));
  // exit only after stdout is flushed (large reports are otherwise truncated on pipes)
  process.stdout.write(JSON.stringify({ errors, writes, snapCount: Object.keys(snaps).length }), () => process.exit(0));
})();
