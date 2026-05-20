"""
build.py — Live-page replica builder for the HF Jobs detail page.
Follows the live-page-replica skill workflow:
  1. Read rendered DOM (downloaded via Blob from browser)
  1a. Capture root shell (html/body classes) — applied in step 7
  2. Strip SvelteKit comment markers
  3. Download & patch compiled CSS (absolutize url() references)
  4. Absolutize src/href asset URLs
  5. Inject TWO hardware-utilization widget versions + a two-tier
     prototype control (version selector -> contextual state toggle)
  6. Splice before Logs section
  7. Assemble full document with source root shell
  8. Write index.html
"""

import re
import sys

LIVE_BASE = "https://huggingface.co"
DOM_FILE  = r"C:\Users\eric5\Downloads\page-main.html"
CSS_FILE  = r"C:\HuggingFace\Job Gauges\style.css"
OUT_FILE  = r"C:\HuggingFace\Job Gauges\job-detail-prototype.html"

# ── 1. Read rendered DOM ──────────────────────────────────────────────────────
print("Reading DOM...")
with open(DOM_FILE, encoding="utf-8") as f:
    main_html = f.read()
print(f"  DOM: {len(main_html):,} chars")

# ── 2. Strip SvelteKit comment markers ───────────────────────────────────────
print("Stripping SvelteKit markers...")
main_html = re.sub(r"<!--\[-->", "", main_html)
main_html = re.sub(r"<!--\]-->", "", main_html)
main_html = re.sub(r"<!--[a-z0-9]{4,12}-->", "", main_html)
main_html = re.sub(r"<!---->", "", main_html)

# ── 3. Absolutize src/href/action in main HTML ───────────────────────────────
print("Absolutizing asset URLs...")
def absify_attr(m):
    attr, quote, val = m.group(1), m.group(2), m.group(3)
    if val.startswith(("http://", "https://", "#", "data:", "mailto:", "//")):
        return m.group(0)
    if val.startswith("/"):
        return f'{attr}={quote}{LIVE_BASE}{val}{quote}'
    return m.group(0)

main_html = re.sub(r'(src|href|action)=(["\'])([^"\']+)\2', absify_attr, main_html)

def absify_srcset(m):
    fixed = []
    for part in m.group(1).split(","):
        tokens = part.strip().split()
        if tokens and tokens[0].startswith("/"):
            tokens[0] = LIVE_BASE + tokens[0]
        fixed.append(" ".join(tokens))
    return 'srcset="' + ", ".join(fixed) + '"'

main_html = re.sub(r'srcset="([^"]+)"', absify_srcset, main_html)

# ── 3b. Scrub private content (this build is published publicly) ─────────────
print("Scrubbing private content...")
_AVATAR = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' "
           "viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='16' "
           "fill='%23475160'/%3E%3C/svg%3E")
_scrub = 0

# 0. SvelteKit hydration payload — data-props carries the ENTIRE job object
#    (script, token, avatars, IDs) as encoded JSON. The static replica never
#    hydrates, so blanking it is harmless and removes the whole leak vector.
main_html, n = re.subn(r'data-props="[^"]*"', 'data-props=""', main_html)
_scrub += n

# 1. Real training script embedded in the LOCAL_FILES_ENCODED env var value
main_html, n = re.subn(
    r'(LOCAL_FILES_ENCODED=)[^<]*',
    r'\1demo.py &lt;redacted for public preview&gt;',
    main_html)
_scrub += n

# 2. Personal access token settings ID
main_html, n = re.subn(
    r'href="[^"]*settings/tokens/[0-9a-f]+"', 'href="#"', main_html)
_scrub += n

# 3. Account avatars (API + CDN) -> neutral placeholder
main_html, n = re.subn(
    r'(src|srcset)="[^"]*(?:api/users/[^"/]+/avatar|cdn-avatars\.huggingface\.co)[^"]*"',
    r'\1="' + _AVATAR + '"', main_html)
_scrub += n
print(f"  Scrubbed {_scrub} private reference(s)")

# ── 3c. Add hooks so the job-state toggle can drive the header Status ─────────
main_html, n1 = re.subn(
    r'<div class="h-9 w-1 flex-none rounded-r-full bg-green-600"></div>',
    '<div id="hw-status-bar" class="h-9 w-1 flex-none rounded-r-full bg-green-600"></div>',
    main_html, count=1)
main_html, n2 = re.subn(
    r'(<p class="text-xs">Status</p>\s*<div) (class="flex items-center gap-1 text-green-600">)',
    r'\1 id="hw-status-label" \2',
    main_html, count=1)
print(f"  Header status hooks: bar={n1} label={n2}")

# ── 3d. Tag the Logs card so V3 (rail) can dock inside it ─────────────────────
main_html, c1 = re.subn(
    r'<div class="flex min-h-\[300px\] flex-1 flex-col overflow-hidden rounded-lg border border-gray-200">',
    '<div id="hw-logs-card" class="flex min-h-[300px] flex-1 flex-col overflow-hidden rounded-lg border border-gray-200" style="position:relative">',
    main_html, count=1)
main_html, c2 = re.subn(
    r'<div class="text-smd shrink-0 border-b border-gray-200 bg-white px-3 py-1.5"><h2 class="font-semibold">Logs</h2></div>',
    '<div id="hw-logs-header" class="text-smd shrink-0 border-b border-gray-200 bg-white px-3 py-1.5"><h2 class="font-semibold">Logs</h2></div>',
    main_html, count=1)
main_html, c3 = re.subn(
    r'<div class="flex-1 overflow-y-auto bg-gray-50 dark:bg-gray-900">',
    '<div id="hw-logs-body" class="flex-1 overflow-y-auto bg-gray-50 dark:bg-gray-900" style="transition:padding-right .25s ease">',
    main_html, count=1)
print(f"  Logs card hooks: card={c1} header={c2} body={c3}")

# ── 4. Patch CSS: rewrite relative url() to absolute ─────────────────────────
print("Patching CSS url() references...")
with open(CSS_FILE, encoding="utf-8", errors="replace") as f:
    css = f.read()

def fix_css_url(m):
    quote = m.group(1) or ""
    val   = m.group(2)
    if val.startswith(("http://", "https://", "data:", "//")):
        return m.group(0)
    if val.startswith("/"):
        return f"url({quote}{LIVE_BASE}{val}{quote})"
    return m.group(0)

css = re.sub(r"url\((['\"]?)([^'\")\s]+)\1\)", fix_css_url, css)
with open(CSS_FILE, "w", encoding="utf-8") as f:
    f.write(css)
print(f"  CSS patched: {len(css):,} chars")

# ── 5. Build the two widget versions + two-tier control ──────────────────────
print("Building widget versions + control...")

# Billing-page gauge track style, reused verbatim for both versions
TRACK = ("h-[6px] overflow-hidden rounded-full bg-gray-200/80 ring-1 "
         "ring-gray-200/40 dark:bg-gray-800 dark:ring-gray-800")

def gauges(prefix, style):
    """Three gauges, IDs namespaced by version prefix.
    style='bar'  -> billing-style flat fill bar
    style='spark'-> time-series sparkline
    Both share the same header (name + AVG/PEAK tag + value)."""
    def one(metric, label):
        if style == 'bar':
            viz = f'''<div class="{TRACK}">
            <div id="{prefix}-{metric}-bar" style="height:100%;border-radius:9999px;width:0%;transition:width .5s ease,background-color .5s ease;"></div>
          </div>'''
        else:
            viz = f'''<div class="hw-spark-track">
            <svg id="{prefix}-{metric}-svg" width="100%" height="30" viewBox="0 0 100 30" preserveAspectRatio="none" style="display:block;"></svg>
          </div>'''
        return f'''
        <div style="flex:1;min-width:200px;max-width:340px;">
          <div style="display:flex;align-items:baseline;justify-content:space-between;margin-bottom:5px;">
            <span class="text-xs text-gray-500">{label}</span>
            <span style="display:flex;align-items:baseline;gap:6px;">
              <span id="{prefix}-{metric}-agg" style="font-size:9px;font-weight:600;letter-spacing:.07em;text-transform:uppercase;color:#8b949e;"></span>
              <span id="{prefix}-{metric}-val" class="text-xs font-medium text-gray-700 dark:text-gray-300" style="font-variant-numeric:tabular-nums;">&mdash;</span>
            </span>
          </div>
          {viz}
        </div>'''
    return (one("gpu-util", "GPU Utilization")
          + one("gpu-mem",  "GPU Memory")
          + one("cpu-util", "CPU Utilization"))

def badges(prefix):
    """Live dot + context note, namespaced by version prefix."""
    return f'''<span id="{prefix}-live-badge" style="display:none;align-items:center;gap:5px;">
        <span style="position:relative;display:inline-flex;width:8px;height:8px;">
          <span style="position:absolute;display:inline-flex;width:100%;height:100%;border-radius:9999px;background:#22c55e;opacity:.75;animation:hwPing 1.5s cubic-bezier(0,0,.2,1) infinite;"></span>
          <span style="position:relative;display:inline-flex;width:8px;height:8px;border-radius:9999px;background:#22c55e;"></span>
        </span>
        <span style="font-size:11px;color:#22c55e;font-weight:500;">Live</span>
      </span>
      <span id="{prefix}-context-note" style="font-size:11px;color:#6e7681;font-style:italic;"></span>'''

# Version 1 — inline row, flat bar gauge (billing style)
V1 = f'''
<div id="hw-v1-wrap">
  <div class="border-t border-gray-200 px-4 py-3 dark:border-gray-800">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
      <span class="text-gray-400 dark:text-gray-500" style="text-transform:uppercase;letter-spacing:.05em;font-size:11px;font-weight:500;">Hardware Utilization</span>
      {badges("hw-v1")}
    </div>
    <div style="display:flex;flex-wrap:wrap;align-items:center;gap:32px;">
      {gauges("hw-v1", "bar")}
    </div>
  </div>
</div>'''

# Version 2 — Inline row, time-series sparkline (the trend row reviewers liked)
V2 = f'''
<div id="hw-v2-wrap" style="display:none;">
  <div class="border-t border-gray-200 px-4 py-3 dark:border-gray-800">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
      <span class="text-gray-400 dark:text-gray-500" style="text-transform:uppercase;letter-spacing:.05em;font-size:11px;font-weight:500;">Hardware Utilization</span>
      {badges("hw-v2")}
    </div>
    <div style="display:flex;flex-wrap:wrap;align-items:center;gap:32px;">
      {gauges("hw-v2", "spark")}
    </div>
  </div>
</div>'''

# Version 3 — Collapsible rail docked inside the logs card (right edge).
# JS relocates #hw-v3-rail into the logs card on activate; it is a sibling
# of the scrolling logs body, so it stays put while logs scroll.
def _rail_metric(metric, label):
    return f'''
    <div class="hw-rail-row" data-metric="{metric}">
      <div class="hw-rail-label">{label}</div>
      <div class="hw-rail-agg-val">
        <span id="hw-v3-{metric}-agg" class="hw-rail-agg"></span>
        <span id="hw-v3-{metric}-val" class="hw-rail-val">&mdash;</span>
      </div>
      <div class="hw-rail-viz">
        <div class="hw-rail-spark hw-spark-track">
          <svg id="hw-v3-{metric}-svg" width="100%" height="28" viewBox="0 0 100 28" preserveAspectRatio="none" style="display:block;"></svg>
        </div>
        <div id="hw-v3-{metric}-blip" class="hw-rail-blip"></div>
      </div>
    </div>'''

V3 = f'''
<div id="hw-v3-wrap" style="display:none;">
  <div id="hw-v3-rail" class="hw-rail-collapsed">
    <div class="hw-rail-head">
      <span class="hw-rail-title">Hardware</span>
      <button onclick="hwToggleRail()" id="hw-v3-toggle" class="hw-rail-toggle" title="Expand"><svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="10 4 6 8 10 12"/></svg></button>
    </div>
    {_rail_metric("gpu-util", "GPU Util")}
    {_rail_metric("gpu-mem",  "GPU Memory")}
    {_rail_metric("cpu-util", "CPU Util")}
    <div class="hw-rail-foot">{badges("hw-v3")}</div>
  </div>
</div>'''

# Version 4 — Sticky floating pill (HUD), bottom-right of viewport.
def _pill_chip(metric, label):
    return f'''
    <div class="hw-pill-chip" data-metric="{metric}">
      <span id="hw-v4-{metric}-dot" class="hw-pill-dot"></span>
      <span class="hw-pill-label">{label}</span>
      <span id="hw-v4-{metric}-val" class="hw-pill-val">&mdash;</span>
    </div>'''

V4 = f'''
<div id="hw-v4-wrap" style="display:none;">
  <div id="hw-v4-pill">
    {_pill_chip("gpu-util", "GPU")}
    <div class="hw-pill-sep"></div>
    {_pill_chip("gpu-mem",  "MEM")}
    <div class="hw-pill-sep"></div>
    {_pill_chip("cpu-util", "CPU")}
    <span class="hw-pill-live">{badges("hw-v4")}</span>
  </div>
</div>'''

# Two-tier prototype control: version selector (primary) -> state toggle
# (secondary, collapsed until a version is chosen).
CONTROL = '''
<div id="hw-control"
     style="position:fixed;top:14px;right:20px;z-index:9999;width:380px;
            background:rgba(15,17,23,0.94);border:1px solid #30363d;
            border-radius:12px;padding:12px;backdrop-filter:blur(10px);
            box-shadow:0 8px 28px rgba(0,0,0,.45);
            font-family:ui-sans-serif,system-ui,sans-serif;">

  <div style="font-size:10px;font-weight:600;letter-spacing:.08em;
              color:#6e7681;text-transform:uppercase;margin-bottom:7px;">
    Widget version
  </div>

  <!-- Segmented control: mutually-exclusive version choice -->
  <div style="display:flex;background:#161b22;border:1px solid #30363d;
              border-radius:8px;padding:3px;gap:3px;">
    <button onclick="hwSetVersion('v1')" id="hw-ver-v1" class="hw-seg" style="flex:1;">V1 Bar</button>
    <button onclick="hwSetVersion('v2')" id="hw-ver-v2" class="hw-seg" style="flex:1;">V2 Trend</button>
    <button onclick="hwSetVersion('v3')" id="hw-ver-v3" class="hw-seg" style="flex:1;">V3 Rail</button>
    <button onclick="hwSetVersion('v4')" id="hw-ver-v4" class="hw-seg" style="flex:1;">V4 Pill</button>
  </div>

  <!-- Contextual state toggle: hidden/collapsed until a version is active -->
  <div id="hw-state-tier">
    <div style="border-top:1px solid #30363d;margin:11px 0 9px;"></div>
    <div style="font-size:10px;font-weight:600;letter-spacing:.08em;
                color:#6e7681;text-transform:uppercase;margin-bottom:7px;">
      Job state
    </div>
    <div style="display:flex;flex-wrap:wrap;gap:5px;">
      <button onclick="hwSetState('running')"   id="hw-st-running"   class="hw-pill">Running</button>
      <button onclick="hwSetState('completed')" id="hw-st-completed" class="hw-pill">Completed</button>
      <button onclick="hwSetState('failed')"    id="hw-st-failed"    class="hw-pill">Error</button>
      <button onclick="hwSetState('cancelled')" id="hw-st-cancelled" class="hw-pill">Cancelled</button>
    </div>
  </div>
</div>'''

STYLE = '''
<style>
  @keyframes hwPing { 75%,100% { transform:scale(1.8); opacity:0; } }
  @keyframes hwSpin { to { transform:rotate(360deg); } }
  .hw-spin { animation:hwSpin 1s linear infinite; transform-origin:50% 50%; }
  .hw-seg {
    padding:6px 6px; border:none; border-radius:6px; cursor:pointer;
    font-size:11px; white-space:nowrap; background:transparent; color:#8b949e;
    transition:background .15s,color .15s;
  }
  .hw-seg:hover { color:#e6edf3; }
  .hw-seg.active { background:#1f6feb; color:#fff; font-weight:600; }
  .hw-pill {
    padding:5px 11px; border:1px solid #30363d; border-radius:9999px;
    cursor:pointer; font-size:11px; background:#161b22; color:#8b949e;
    transition:background .15s,color .15s,border-color .15s;
  }
  .hw-pill:hover { color:#e6edf3; border-color:#475160; }
  .hw-pill.active { background:#238636; border-color:#238636; color:#fff; font-weight:600; }
  .hw-spark-track {
    height:30px; border-radius:6px; overflow:hidden;
    background:rgba(110,118,129,0.10);
  }
  :where(.dark) .hw-spark-track { background:rgba(110,118,129,0.14); }
  #hw-state-tier {
    max-height:0; opacity:0; overflow:hidden;
    transition:max-height .28s ease, opacity .2s ease;
  }
  #hw-state-tier.open { max-height:200px; opacity:1; }

  /* ── V3 rail (docks inside the logs card) ─────────────────────────────── */
  #hw-v3-rail {
    box-sizing:border-box; display:flex; flex-direction:column; gap:10px;
    transition:width .25s ease, padding .25s ease;
    font-family:ui-sans-serif,system-ui,sans-serif;
  }
  #hw-v3-rail.hw-rail-collapsed { width:48px;  padding:8px 4px; align-items:center; }
  #hw-v3-rail.hw-rail-expanded  { width:280px; padding:10px 14px; }
  .hw-rail-head { display:flex; align-items:center; justify-content:space-between; width:100%; min-height:18px; }
  .hw-rail-collapsed .hw-rail-title { display:none; }
  .hw-rail-title { font-size:10px; text-transform:uppercase; letter-spacing:.06em; color:#8b949e; font-weight:600; }
  .hw-rail-toggle { background:transparent; border:none; color:#8b949e; cursor:pointer; padding:2px; border-radius:4px; display:inline-flex; }
  .hw-rail-toggle:hover { background:rgba(139,148,158,.15); color:#e6edf3; }
  .hw-rail-collapsed .hw-rail-toggle svg { transform:rotate(180deg); }
  .hw-rail-row { width:100%; display:flex; flex-direction:column; gap:3px; }
  .hw-rail-label { font-size:10px; color:#8b949e; font-weight:500; }
  .hw-rail-collapsed .hw-rail-label { display:none; }
  .hw-rail-agg-val { display:flex; align-items:baseline; justify-content:space-between; gap:6px; }
  .hw-rail-collapsed .hw-rail-agg-val { justify-content:center; }
  .hw-rail-agg { font-size:9px; font-weight:600; letter-spacing:.07em; text-transform:uppercase; color:#8b949e; }
  .hw-rail-collapsed .hw-rail-agg { display:none; }
  .hw-rail-val { font-size:11px; color:#e6edf3; font-weight:500; font-variant-numeric:tabular-nums; white-space:nowrap; }
  .hw-rail-viz { position:relative; }
  .hw-rail-spark { height:28px; }
  .hw-rail-collapsed .hw-rail-spark { display:none; }
  .hw-rail-blip { height:3px; border-radius:2px; background:#6e7681; margin-top:2px; }
  .hw-rail-expanded .hw-rail-blip { display:none; }
  .hw-rail-foot { margin-top:auto; min-height:14px; }
  .hw-rail-collapsed .hw-rail-foot { display:none; }

  /* ── V4 sticky pill (HUD, bottom-right of viewport) ───────────────────── */
  #hw-v4-pill {
    position:fixed; bottom:24px; right:24px; z-index:9998;
    display:flex; align-items:center; gap:12px;
    background:rgba(22,27,34,0.95); border:1px solid #30363d;
    border-radius:9999px; padding:8px 16px;
    box-shadow:0 8px 28px rgba(0,0,0,.55); backdrop-filter:blur(8px);
    font-family:ui-sans-serif,system-ui,sans-serif;
  }
  .hw-pill-chip { display:flex; align-items:center; gap:6px; }
  .hw-pill-dot { width:8px; height:8px; border-radius:9999px; background:#6e7681; flex-shrink:0; }
  .hw-pill-label { font-size:10px; color:#8b949e; font-weight:600; text-transform:uppercase; letter-spacing:.05em; }
  .hw-pill-val { font-size:11px; color:#e6edf3; font-weight:500; font-variant-numeric:tabular-nums; }
  .hw-pill-sep { width:1px; height:14px; background:#30363d; }
  .hw-pill-live { margin-left:2px; }
</style>'''

SCRIPT = '''
<script>
(function () {
  // Which render style each version uses
  var VSTYLE = { 'hw-v1':'bar', 'hw-v2':'spark', 'hw-v3':'rail', 'hw-v4':'pill' };
  var PREFIXES = ['hw-v1', 'hw-v2', 'hw-v3', 'hw-v4'];
  var railExpanded = false;
  var FULL = 40;            // full-run sample count (x-axis denominator)
  var currentState = 'completed';
  var currentVersion = 'v1';
  var liveTimer = null;

  // Per-metric semantics: which aggregate matters, and how to scale/format.
  var META = {
    'gpu-util': { agg:'AVG',  scale:100, fmt:function(v){ return Math.round(v) + '%'; } },
    'gpu-mem':  { agg:'PEAK', scale:48,  fmt:function(v){ return v.toFixed(1) + ' / 48 GB'; } },
    'cpu-util': { agg:'AVG',  scale:100, fmt:function(v){ return Math.round(v) + '%'; } }
  };

  function clamp(v, lo, hi) { return Math.min(Math.max(v, lo), hi); }
  function mean(a) { return a.reduce(function(s,x){return s+x;},0) / a.length; }
  function peak(a) { return Math.max.apply(null, a); }

  // Per-metric colour semantics. Colour escalates only toward a condition
  // the user should ACT on — which differs by metric:
  //   GPU memory : high = OOM risk  -> ceiling scale (high is bad)
  //   GPU util   : high = the goal  -> inverted (LOW avg = wasted spend)
  //   CPU util   : relational tell  -> never an alarm (neutral)
  var INDIGO = '#6366f1', AMBER = '#f59e0b', RED = '#ef4444';
  function metricColor(metric, value, name) {
    var pct = value / META[metric].scale * 100;
    if (metric === 'gpu-mem') {
      if (name === 'failed') return RED;        // OOM prime suspect on a crash
      if (pct >= 95) return RED;                // at the ceiling
      if (pct >= 80) return AMBER;              // approaching the ceiling
      return INDIGO;
    }
    if (metric === 'gpu-util') {
      // Instantaneous values dip on every sawtooth trough — only the
      // *average* (completed/failed) carries the "idle GPU" signal.
      if (name === 'running') return INDIGO;
      if (pct < 15) return RED;                 // GPU mostly idle = wasted spend
      if (pct < 40) return AMBER;               // under-utilised
      return INDIGO;                            // healthy / well-saturated
    }
    return INDIGO;                              // cpu-util: never alarmed
  }

  // ── Mock series generators (plausible shapes, not real data) ──────────────
  function gen(kind, n) {
    var a = [], i, v;
    for (i = 0; i < n; i++) {
      if (kind === 'gpu-util') {
        // sawtooth: GPU spikes then starves on the data loader
        v = 64 + 26 * Math.sin(i * 0.7) + (Math.random()*14 - 7);
        a.push(clamp(v, 22, 97));
      } else if (kind === 'gpu-mem') {
        // ramp then plateau near the ceiling
        v = Math.min(7 + i * 1.25, 42.4) + (Math.random()*1.4 - 0.7);
        a.push(clamp(v, 4, 47.9));
      } else { // cpu-util
        v = 36 + 9 * Math.sin(i * 0.5 + 1) + (Math.random()*12 - 6);
        a.push(clamp(v, 14, 60));
      }
    }
    return a;
  }
  // Failed run: steeper memory climb, cut off ~55% through (the cliff).
  function genFail(kind) {
    var n = 22, a = gen(kind, n);
    if (kind === 'gpu-mem') {
      for (var i = 0; i < n; i++) a[i] = clamp(6 + i * 2.05 + (Math.random()*1.2-0.6), 4, 47.9);
    }
    return a;
  }
  // Cancelled run: a normal run cut short by the user — partial, healthy
  // shape (no OOM ramp), just stops where they hit cancel.
  function genCancel(kind) { return gen(kind, 26); }

  var SERIES = {
    completed: {
      'gpu-util': gen('gpu-util', FULL),
      'gpu-mem':  gen('gpu-mem',  FULL),
      'cpu-util': gen('cpu-util', FULL)
    },
    failed: {
      'gpu-util': genFail('gpu-util'),
      'gpu-mem':  genFail('gpu-mem'),
      'cpu-util': genFail('cpu-util')
    },
    cancelled: {
      'gpu-util': genCancel('gpu-util'),
      'gpu-mem':  genCancel('gpu-mem'),
      'cpu-util': genCancel('cpu-util')
    },
    running: {  // seeded warm window, then rolled live
      'gpu-util': gen('gpu-util', FULL),
      'gpu-mem':  (function(){ var a=[]; for(var i=0;i<FULL;i++) a.push(clamp(20+Math.random()*4,18,30)); return a; })(),
      'cpu-util': gen('cpu-util', FULL)
    }
  };

  // ── Sparkline renderer ────────────────────────────────────────────────────
  // Builds an SVG: soft area + trend line, plus either a dashed MEAN line
  // (AVG metrics) or a dot at the PEAK point (PEAK metrics). A short series
  // simply doesn't span the full width — the empty tail = "it stopped".
  function renderSpark(prefix, metric, series, color, mode) {
    var svg = document.getElementById(prefix + '-' + metric + '-svg');
    if (!svg) return;
    var W = 100, H = 30, PAD = 2, scale = META[metric].scale;

    if (!series || series.length === 0) {            // no data: flat baseline
      svg.innerHTML = '<line x1="0" y1="' + (H-PAD) + '" x2="' + W +
        '" y2="' + (H-PAD) + '" stroke="#6e7681" stroke-width="1" ' +
        'stroke-dasharray="2 3" vector-effect="non-scaling-stroke"/>';
      return;
    }

    var n = series.length;
    var X = function (i) { return (i / (FULL - 1)) * W; };
    var Y = function (v) { return H - PAD - (v / scale) * (H - PAD * 2); };

    var pts = series.map(function (v, i) { return X(i) + ',' + Y(v); }).join(' ');
    var area = 'M0,' + (H) + ' L' +
      series.map(function (v, i) { return X(i) + ',' + Y(v); }).join(' L') +
      ' L' + X(n - 1) + ',' + H + ' Z';

    var marker = '';
    if (mode === 'PEAK') {
      var pv = peak(series), pi = series.indexOf(pv);
      marker = '<circle cx="' + X(pi) + '" cy="' + Y(pv) + '" r="2.4" ' +
               'fill="' + color + '" vector-effect="non-scaling-stroke"/>';
    } else if (mode === 'AVG') {
      var mv = mean(series), my = Y(mv);
      marker = '<line x1="0" y1="' + my + '" x2="' + X(n - 1) + '" y2="' + my +
               '" stroke="' + color + '" stroke-width="1" opacity="0.55" ' +
               'stroke-dasharray="3 2" vector-effect="non-scaling-stroke"/>';
    } else if (mode === 'LIVE') {
      var lv = series[n - 1];
      marker = '<circle cx="' + X(n - 1) + '" cy="' + Y(lv) + '" r="2.4" ' +
               'fill="' + color + '"/>';
    }

    svg.innerHTML =
      '<path d="' + area + '" fill="' + color + '" opacity="0.14"/>' +
      '<polyline points="' + pts + '" fill="none" stroke="' + color +
      '" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round" ' +
      'vector-effect="non-scaling-stroke"/>' + marker;
  }

  // Flat fill bar (billing style) — used by V1 & V2.
  function renderBar(prefix, metric, pctOfScale, color) {
    var b = document.getElementById(prefix + '-' + metric + '-bar');
    if (!b) return;
    b.style.width = clamp(pctOfScale, 0, 100) + '%';
    b.style.backgroundColor = color;
  }

  // ── Paint one version for the current state ───────────────────────────────
  // Aggregation logic (AVG/PEAK tag + value + colour) is shared; only the
  // visualisation differs: bar for V1/V2, sparkline for V3.
  function paint(prefix, name) {
    var style = VSTYLE[prefix];
    var badge = document.getElementById(prefix + '-live-badge');
    var note  = document.getElementById(prefix + '-context-note');
    if (badge) badge.style.display = (name === 'running') ? 'flex' : 'none';
    if (note)  note.textContent = '';   // state-echo removed (header owns status)

    ['gpu-util', 'gpu-mem', 'cpu-util'].forEach(function (m) {
      var aggEl = document.getElementById(prefix + '-' + m + '-agg');
      var valEl = document.getElementById(prefix + '-' + m + '-val');
      var meta  = META[m];
      var s     = SERIES[name][m];

      var aggText = '', valText, color, pct, sparkMode, sparkSeries = s;

      if (name === 'running') {
        // Live: instantaneous reading, no aggregate label.
        var cur = s[s.length - 1];
        color = metricColor(m, cur, 'running');
        valText = meta.fmt(cur); pct = cur / meta.scale * 100;
        sparkMode = 'LIVE';
      } else {
        // completed / failed / cancelled: the aggregate for this metric over
        // the run (partial for failed/cancelled). Cancelled is neutral grey —
        // the user stopped it, nothing went wrong, so never amber/red.
        var stat = (meta.agg === 'PEAK') ? peak(s) : mean(s);
        color = (name === 'cancelled') ? '#6e7681' : metricColor(m, stat, name);
        aggText = meta.agg;
        valText = meta.fmt(stat); pct = stat / meta.scale * 100;
        sparkMode = meta.agg;
      }

      if (aggEl) aggEl.textContent = aggText;
      if (valEl) valEl.textContent = valText;
      if (style === 'bar')   renderBar(prefix, m, pct, color);
      else if (style === 'spark') renderSpark(prefix, m, sparkSeries, color, sparkMode);
      else if (style === 'rail') {
        // Sparkline for expanded mode; blip colour drives the collapsed cue.
        renderSpark(prefix, m, sparkSeries, color, sparkMode);
        var blip = document.getElementById(prefix + '-' + m + '-blip');
        if (blip) blip.style.backgroundColor = color;
      }
      else if (style === 'pill') {
        var dot = document.getElementById(prefix + '-' + m + '-dot');
        if (dot) dot.style.backgroundColor = color;
      }
    });
  }

  function tick() {
    ['gpu-util', 'gpu-mem', 'cpu-util'].forEach(function (m) {
      var a = SERIES.running[m], last = a[a.length - 1], nx;
      if (m === 'gpu-util')      nx = clamp(last + (Math.random()*22 - 11), 30, 96);
      else if (m === 'gpu-mem')  nx = clamp(last + (Math.random()*1.6 - 0.7), 18, 30);
      else                       nx = clamp(last + (Math.random()*16 - 8),  20, 64);
      a.push(nx); a.shift();
    });
    PREFIXES.forEach(function (p) { paint(p, 'running'); });
  }

  // ── Header Status cell — driven by the same job-state toggle ──────────────
  function svgIcon(inner, cls) {
    return '<svg xmlns="http://www.w3.org/2000/svg" aria-hidden="true" ' +
      'focusable="false" role="img" width="1em" height="1em" ' +
      'preserveAspectRatio="xMidYMid meet" viewBox="0 0 32 32"' +
      (cls ? ' class="' + cls + '"' : '') + '>' + inner + '</svg>';
  }
  var ICON = {
    completed: svgIcon('<path d="M13 24l-9-9l1.414-1.414L13 21.171L26.586 7.586L28 9L13 24z" fill="currentColor"></path>'),
    failed:    svgIcon('<path d="M24 9.4L22.6 8L16 14.6L9.4 8L8 9.4L14.6 16L8 22.6L9.4 24L16 17.4L22.6 24L24 22.6L17.4 16L24 9.4z" fill="currentColor"></path>'),
    cancelled: svgIcon('<path d="M24 9.4L22.6 8L16 14.6L9.4 8L8 9.4L14.6 16L8 22.6L9.4 24L16 17.4L22.6 24L24 22.6L17.4 16L24 9.4z" fill="currentColor"></path>'),
    running:   svgIcon('<path d="M16 3a13 13 0 1 0 13 13h-2.6A10.4 10.4 0 1 1 16 5.6z" fill="currentColor"></path>', 'hw-spin')
  };
  var STATUS = {
    running:   { txt:'Running',   tc:'text-blue-600',  bc:'bg-blue-600'  },
    completed: { txt:'Completed', tc:'text-green-600', bc:'bg-green-600' },
    failed:    { txt:'Error',     tc:'text-red-600',   bc:'bg-red-600'   },
    cancelled: { txt:'Cancelled', tc:'text-gray-500',  bc:'bg-gray-400'  }
  };
  function setHeader(name) {
    var s = STATUS[name]; if (!s) return;
    var bar = document.getElementById('hw-status-bar');
    var lbl = document.getElementById('hw-status-label');
    if (bar) bar.className = 'h-9 w-1 flex-none rounded-r-full ' + s.bc;
    if (lbl) {
      lbl.className = 'flex items-center gap-1 ' + s.tc;
      lbl.innerHTML = ICON[name] + ' ' + s.txt;
    }
  }

  function applyState(name) {
    currentState = name;
    setHeader(name);
    if (liveTimer) { clearInterval(liveTimer); liveTimer = null; }
    PREFIXES.forEach(function (p) { paint(p, name); });
    if (name === 'running') { liveTimer = setInterval(tick, 1800); }
    ['running','completed','failed','cancelled'].forEach(function (s) {
      var el = document.getElementById('hw-st-' + s);
      if (el) el.classList.toggle('active', s === name);
    });
  }

  window.hwSetState = function (n) { applyState(n); };

  // V3 rail docks inside the logs card. Move it in/out of the card on switch.
  function attachRail() {
    var rail = document.getElementById('hw-v3-rail');
    var card = document.getElementById('hw-logs-card');
    var head = document.getElementById('hw-logs-header');
    if (!rail || !card) return;
    if (rail.parentElement !== card) card.appendChild(rail);
    var hH = head ? head.offsetHeight : 36;
    rail.style.position = 'absolute';
    rail.style.top = hH + 'px';
    rail.style.right = '0';
    rail.style.bottom = '0';
    rail.style.borderLeft = '1px solid rgba(48,54,61,.7)';
    rail.style.background = 'rgba(13,17,23,0.78)';
    rail.style.backdropFilter = 'blur(4px)';
  }
  function detachRail() {
    var rail = document.getElementById('hw-v3-rail');
    var wrap = document.getElementById('hw-v3-wrap');
    if (!rail || !wrap) return;
    if (rail.parentElement !== wrap) wrap.appendChild(rail);
    rail.style.position = rail.style.top = rail.style.right = rail.style.bottom = '';
    rail.style.borderLeft = rail.style.background = rail.style.backdropFilter = '';
  }
  function syncLogsPad() {
    var body = document.getElementById('hw-logs-body');
    if (!body) return;
    if (currentVersion === 'v3') {
      body.style.paddingRight = (railExpanded ? 280 : 48) + 'px';
    } else {
      body.style.paddingRight = '0px';
    }
  }

  window.hwToggleRail = function () {
    railExpanded = !railExpanded;
    var rail = document.getElementById('hw-v3-rail');
    var btn  = document.getElementById('hw-v3-toggle');
    if (rail) rail.className = railExpanded ? 'hw-rail-expanded' : 'hw-rail-collapsed';
    if (btn)  btn.title = railExpanded ? 'Collapse' : 'Expand';
    syncLogsPad();
    applyState(currentState);
  };

  window.hwSetVersion = function (v) {
    currentVersion = v;
    ['v1', 'v2', 'v3', 'v4'].forEach(function (k) {
      var w = document.getElementById('hw-' + k + '-wrap');
      if (w) w.style.display = (k === v) ? '' : 'none';
      var b = document.getElementById('hw-ver-' + k);
      if (b) b.classList.toggle('active', k === v);
    });
    if (v === 'v3') attachRail(); else detachRail();
    syncLogsPad();
    // Reveal the contextual state toggle now that a version is active
    document.getElementById('hw-state-tier').classList.add('open');
    applyState(currentState);
  };

  document.addEventListener('DOMContentLoaded', function () {
    hwSetVersion('v1');
    hwSetState('completed');
  });
})();
</script>'''

HARDWARE_BLOCK = CONTROL + V1 + V2 + V3 + V4 + STYLE + SCRIPT

# ── 6. Find injection point and splice ────────────────────────────────────────
print("Finding injection point...")
LOGS_MARKER = '<div id="hw-logs-card"'
inject_pos = main_html.find(LOGS_MARKER)
if inject_pos == -1:
    print("ERROR: Could not find logs marker. Aborting.")
    sys.exit(1)
print(f"  Injection point found at pos {inject_pos:,}")
main_html = main_html[:inject_pos] + HARDWARE_BLOCK + main_html[inject_pos:]

# ── 7. Assemble full HTML document (with source root shell — Step 1a) ─────────
print("Assembling final HTML...")
full_html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Chunte/69e85341cd8c002f31e0166c · Jobs · Hugging Face</title>

  <!-- Source compiled CSS — absolutized, no Tailwind CDN -->
  <link rel="stylesheet" href="style.css" />

  <!-- Google Fonts (dynamically injected on source page) -->
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link rel="stylesheet"
        href="https://fonts.googleapis.com/css2?family=Source+Sans+Pro:ital,wght@0,200;0,300;0,400;0,600;0,700;0,900;1,200;1,300;1,400;1,600;1,700;1,900&family=IBM+Plex+Mono:wght@400;500;600&display=swap" />

  <!-- KaTeX (loaded by source) -->
  <link rel="stylesheet"
        href="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.12.0/katex.min.css" />
</head>
<body class="flex flex-col min-h-dvh bg-white dark:bg-gray-950 text-black JobPage">
  <div class="flex min-h-dvh flex-col">
    <main>
      {main_html}
    </main>
  </div>
</body>
</html>"""

# ── 8. Write output ───────────────────────────────────────────────────────────
with open(OUT_FILE, "w", encoding="utf-8") as f:
    f.write(full_html)

print(f"\nDone. Written: {OUT_FILE}")
print(f"  Size: {len(full_html)//1024:,} KB ({len(full_html):,} chars)")
