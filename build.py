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

import os
import re
import sys

# Portable paths — everything lives next to this script, so the repo is
# self-contained and `python build.py` works on any device after a clone.
LIVE_BASE = "https://huggingface.co"
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DOM_FILE  = os.path.join(BASE_DIR, "page-main.html")
CSS_FILE  = os.path.join(BASE_DIR, "style.css")
OUT_FILE  = os.path.join(BASE_DIR, "job-detail-prototype.html")

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

# ── 3d. Tag the Logs card and wrap it in #hw-v3-layout (sibling slot for V3) ─
main_html, c1 = re.subn(
    r'<div class="flex min-h-\[300px\] flex-1 flex-col overflow-hidden rounded-lg border border-gray-200">',
    '<div id="hw-logs-card" class="flex min-h-[300px] flex-1 flex-col overflow-hidden rounded-lg border border-gray-200">',
    main_html, count=1)

def _find_matching_close_div(html, open_pos):
    """Find the index right after the </div> that matches the <div...> at open_pos."""
    i = open_pos + 1
    depth = 1
    while i < len(html):
        no = html.find('<div', i)
        nc = html.find('</div>', i)
        if nc == -1: return -1
        if no != -1 and no < nc:
            depth += 1
            i = no + 4
        else:
            depth -= 1
            i = nc + 6
            if depth == 0: return i
    return -1

_card_open = main_html.find('<div id="hw-logs-card"')
_card_end  = _find_matching_close_div(main_html, _card_open) if _card_open != -1 else -1
if _card_open == -1 or _card_end == -1:
    print("ERROR: could not locate logs card bounds for V3 layout wrap.")
    sys.exit(1)
main_html = (main_html[:_card_open]
             + '<div id="hw-v3-layout" class="hw-v3-layout">'
             + '<div id="hw-v3-spacer" class="hw-v3-spacer" style="display:none"></div>'
             + main_html[_card_open:_card_end]
             + '</div>'
             + main_html[_card_end:])

# Page container has overflow-hidden which would clip the lg pill that
# sits in the margin to the right of logs. Add an inline style override.
main_html, c_over = re.subn(
    r'<div class="container flex flex-1 flex-col gap-4 overflow-hidden py-4">',
    '<div class="container flex flex-1 flex-col gap-4 overflow-hidden py-4" style="overflow:visible">',
    main_html, count=1)
print(f"  Logs card hooks: card={c1} wrapped-in-v3-layout=1 page-overflow={c_over}")

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
    """Live dot only (no text), namespaced by version prefix. The dot is
    a small (6x6) pulsing green indicator shown only when the job is
    running. Sits 5px from the title — see context-specific overrides."""
    return f'''<span id="{prefix}-live-badge" style="display:none;align-items:center;">
        <span style="position:relative;display:inline-flex;width:6px;height:6px;">
          <span style="position:absolute;display:inline-flex;width:100%;height:100%;border-radius:9999px;background:#22c55e;opacity:.75;animation:hwPing 1.5s cubic-bezier(0,0,.2,1) infinite;"></span>
          <span style="position:relative;display:inline-flex;width:6px;height:6px;border-radius:9999px;background:#22c55e;"></span>
        </span>
      </span>
      <span id="{prefix}-context-note" style="font-size:11px;color:#6e7681;font-style:italic;"></span>'''

# Version 1 — inline row, flat bar gauge (billing style)
V1 = f'''
<div id="hw-v1-wrap">
  <div class="border-t border-gray-200 px-4 py-3 dark:border-gray-800">
    <div style="display:flex;align-items:center;gap:5px;margin-bottom:12px;">
      <p class="text-xs text-gray-500">Hardware Utilization</p>
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
    <div style="display:flex;align-items:center;gap:5px;margin-bottom:12px;">
      <p class="text-xs text-gray-500">Hardware Utilization</p>
      {badges("hw-v2")}
    </div>
    <div style="display:flex;flex-wrap:wrap;align-items:center;gap:32px;">
      {gauges("hw-v2", "spark")}
    </div>
  </div>
</div>'''

# Version 3 — Responsive "Hardware" pill anchored to the log container.
# Collapsed = compact pill in real layout next to / above the logs:
#   lg  -> vertical stack to the right of the logs card (sibling)
#   md  -> horizontal row above logs, right-aligned
#   sm  -> horizontal row above logs, full screen width
# Expanded = the same pill but larger, overlay over the logs (logs unchanged),
# vertical stack of 3 metrics with sparklines on every breakpoint.
# JS moves #hw-v3-pill into #hw-v3-layout (sibling of logs card) on activate.
def _v3_row(metric, label):
    return f'''
      <div class="hw-v3-row" data-metric="{metric}">
        <div class="hw-v3-row-head">
          <span id="hw-v3-{metric}-dot" class="hw-v3-dot"></span>
          <span class="hw-v3-row-label">{label}</span>
          <span class="hw-v3-row-spacer"></span>
          <span id="hw-v3-{metric}-agg" class="hw-v3-agg"></span>
          <span id="hw-v3-{metric}-val" class="hw-v3-val">&mdash;</span>
        </div>
        <div class="hw-v3-spark hw-spark-track">
          <svg id="hw-v3-{metric}-svg" width="100%" height="30" viewBox="0 0 100 30" preserveAspectRatio="none" style="display:block;"></svg>
        </div>
      </div>'''

V3 = f'''
<div id="hw-v3-wrap" style="display:none;">
  <div id="hw-v3-pill" class="hw-v3-collapsed border border-gray-200 bg-white dark:bg-gray-950" onclick="hwToggleV3(event)">
    <div class="hw-v3-head">
      <p class="text-xs text-gray-500 hw-v3-title">Hardware Utilization</p>
      <span class="hw-v3-head-live">{badges("hw-v3")}</span>
      <button onclick="hwToggleV3(event)" id="hw-v3-toggle" class="hw-v3-toggle" title="Expand">
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" class="hw-v3-chevron">
          <polyline points="4 6 8 10 12 6"/>
        </svg>
      </button>
    </div>
    <div class="hw-v3-rows">
      {_v3_row("gpu-util", "GPU")}
      {_v3_row("gpu-mem",  "MEM")}
      {_v3_row("cpu-util", "CPU")}
    </div>
  </div>
</div>'''

# Two-tier prototype control: version selector (primary) -> state toggle
# (secondary, collapsed until a version is chosen).
CONTROL = '''
<div id="hw-control"
     style="position:fixed;bottom:14px;right:20px;z-index:9999;width:380px;
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
    <button onclick="hwSetVersion('v3')" id="hw-ver-v3" class="hw-seg" style="flex:1;">V3 Pill</button>
    <button onclick="hwSetVersion('v2')" id="hw-ver-v2" class="hw-seg" style="flex:1;">V2 Trend</button>
    <button onclick="hwSetVersion('v1')" id="hw-ver-v1" class="hw-seg" style="flex:1;">V1 Bar</button>
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

  /* ── V3 responsive pill (anchored to the log container) ───────────────── */
  /* The pill is ALWAYS position:absolute against #hw-v3-layout, so it     */
  /* never steals horizontal space from the logs container. On sm/md a    */
  /* spacer reserves vertical room above the logs for the collapsed pill; */
  /* expansion grows the pill over the top of logs (overlay) without      */
  /* shifting the logs because the spacer's height stays the same.        */
  /* On lg the pill floats in the page margin to the right of logs, and  */
  /* expanding pulls it back leftward to overlay the top-right of logs.   */
  .hw-v3-layout {
    display:flex; flex-direction:column; gap:8px;
    position:relative; flex:1 1 auto; min-height:0;
  }
  .hw-v3-spacer {
    order:0; flex-shrink:0; width:100%; height:60px;
  }
  @media (min-width:1536px) {
    .hw-v3-spacer { display:none; }
  }
  .hw-v3-layout > #hw-logs-card { order:1; }
  #hw-v3-pill {
    position:absolute; z-index:20; top:0; right:0;
    box-sizing:border-box; overflow:hidden;
    /* Border + background come from Tailwind classes on the element
       (border-gray-200 / bg-white dark:bg-gray-950) so the widget
       inherits the page's chrome (matches the logs card border and
       page background). */
    border-radius:12px; padding:8px 14px;
    box-shadow:0 4px 14px rgba(0,0,0,.35);
    cursor:pointer; user-select:none;
    display:flex; flex-direction:column; gap:10px;
    transition:top    .3s cubic-bezier(0.4,0,0.2,1),
               right  .3s cubic-bezier(0.4,0,0.2,1),
               left   .3s cubic-bezier(0.4,0,0.2,1),
               width  .3s cubic-bezier(0.4,0,0.2,1),
               height .3s cubic-bezier(0.4,0,0.2,1),
               padding .25s ease;
  }
  /* COLLAPSED · mobile (default) — full-width row above logs, horizontal */
  #hw-v3-pill.hw-v3-collapsed { width:100%; height:auto; }
  .hw-v3-collapsed .hw-v3-head { display:none; }
  .hw-v3-collapsed .hw-v3-rows {
    display:flex; flex-direction:row; align-items:center;
    gap:16px; flex-wrap:wrap;
  }
  .hw-v3-collapsed .hw-v3-row {
    flex:1 1 auto; min-width:80px; display:flex; flex-direction:row;
    align-items:center; gap:6px;
  }
  .hw-v3-collapsed .hw-v3-row-head {
    display:flex; align-items:center; gap:6px; flex:1; min-width:0;
  }
  .hw-v3-collapsed .hw-v3-row-spacer { display:none; }
  .hw-v3-collapsed .hw-v3-agg { display:none; }
  .hw-v3-collapsed .hw-v3-spark { display:none; }
  /* The md+ width:420 rule that used to live here was removed: at md
     (768-1023) the pill now uses the same content-hugging horizontal
     chrome as lg-wide (set in the 768-1535 shared block below). */
  /* COLLAPSED · 4K-class (Tailwind 2xl, ≥1536) — vertical, narrow,
     FLOATS in the right page margin. Right edge anchored 160px past logs'
     right edge; same anchor as expanded so on expand the widget grows
     leftward INTO logs without the right edge shifting. */
  @media (min-width:1536px) {
    /* 4K-class: pill FLOATS in the page margin with a 10px gap to the
       right of the logs container. JS (lockLgAnchor) measures the
       collapsed width W and sets inline `right:-(W+10)` and `width:Wpx`
       so the right anchor is in the margin AND the width is a length
       (animatable). The CSS values below are fallbacks the inline
       overrides — they don't determine the actual position. */
    #hw-v3-pill.hw-v3-collapsed {
      right:0; left:auto; width:max-content; padding:10px 12px;
    }
    .hw-v3-collapsed .hw-v3-head { display:flex; align-items:center; gap:8px; justify-content:space-between; }
    .hw-v3-collapsed .hw-v3-rows { flex-direction:column; align-items:stretch; gap:6px; }
    .hw-v3-collapsed .hw-v3-row { flex-direction:row; justify-content:space-between; gap:14px; }
  }
  /* COLLAPSED · md/lg/xl (Tailwind md+lg+xl, 768–1535) — SHARED pill
     chrome: horizontal layout, content-hug width, ordering, chip
     styling. md (768–1023) gets the same polished chrome as lg-wide.
     The container anchor (left vs right, float-into-band vs own-row)
     is set by the breakpoint-specific blocks BELOW. */
  @media (min-width:768px) and (max-width:1535.98px) {
    #hw-v3-pill.hw-v3-collapsed {
      flex-direction:row;
      /* CRITICAL: flex-start, NOT center. With center, when the pill is
         mid-shrink during collapse (height locked to 207 while layout
         has flipped to row), the title would be vertically centered in
         a 207-tall row — i.e. ~95px below its resting position — and
         then "rise" 86px during the height animation. Content that
         exists in BOTH states must stay at the same viewport y. */
      align-items:flex-start;
      width:max-content;
      /* Pill internal gap matches the chip-to-chip gap so title→chip and
         chip→chip look identical. */
      gap:20px;
      /* padding-top MUST match the expanded padding-top below (both 10px)
         so the title sits at the same y in both states — zero shift. */
      padding:10px 6px 10px 14px;
      /* Container anchor (right:0 for wide lg float, left:0 for narrow
         lg own-row) is set in the breakpoint-specific blocks below. */
    }
    /* Pull the chevron closer to CPU so the right-side dead space is
       small without affecting the title→chip and chip→chip rhythm. */
    .hw-v3-collapsed #hw-v3-toggle { margin-left:-12px; }
    /* Metrics inline, no wrap. Uniform 20px chip gap (GPU↔MEM↔CPU). */
    .hw-v3-collapsed .hw-v3-rows {
      flex-direction:row; flex-wrap:nowrap; gap:20px; align-items:center;
    }
    /* Override the mobile-base `min-width:80px` — at lg the chips must hug
       their content (no trailing dead space inside the chip), otherwise
       the chip-to-chip gap appears larger than title-to-chip even when
       the CSS `gap` is equal. */
    .hw-v3-collapsed .hw-v3-row {
      flex:none; flex-direction:row; gap:6px;
      min-width:0;
    }
    .hw-v3-collapsed .hw-v3-row-head {
      flex:none; min-width:0;
    }
    /* Flatten head into pill flex flow; head-live also display:contents so
       hidden badges/notes don't contribute phantom gaps. Hide
       context-note completely (always empty in lg-compact form). Set
       explicit order on each VISIBLE item so spacing is even (the empty
       context-note span otherwise inherits order:0 and adds a 14px gap
       before the title). */
    .hw-v3-collapsed .hw-v3-head { display:contents; }
    .hw-v3-collapsed .hw-v3-head-live { display:contents; }
    .hw-v3-collapsed #hw-v3-context-note { display:none !important; }
    .hw-v3-collapsed .hw-v3-title { order:1; }
    .hw-v3-collapsed #hw-v3-live-badge {
      order:2;
      /* Pill gap is 20; pull the dot left by 15 so it sits 5px from the
         title. The downstream gap (badge→chips) stays at 20. */
      margin-left:-15px;
      /* The pill's `align-items: flex-start` (needed to anchor the title
         during the FLIP animation) top-aligns every flex item. The 6×6
         dot would otherwise sit at the top of the 16-tall title's
         line-box, ~5px above the title's visual centre. Nudge it down
         so the dot's centre matches the title's text centre. */
      margin-top:5px;
    }
    .hw-v3-collapsed .hw-v3-rows { order:3; }
    .hw-v3-collapsed .hw-v3-toggle { order:4; }
  }
  /* lg-NARROW (1024–1279) — Command field wraps to row-2 of the header
     band, leaving no dead space for the pill. So the pill takes its own
     row above logs, anchored LEFT, with a 10px visible gap to logs.
     A spacer reserves vertical room (logs are pushed down, unlike the
     wide-lg case where the pill intrudes into header dead space).
     JS sets `top:0` (sits in spacer slot) and clears any negative top
     left over from a wide-lg cycle. */
  @media (min-width:1024px) and (max-width:1279.98px) {
    .hw-v3-layout { gap:10px; }
    .hw-v3-spacer { display:block; }      /* reserves vertical room */
    #hw-v3-pill.hw-v3-collapsed { left:0; right:auto; }
    #hw-v3-pill.hw-v3-expanded  { left:0; right:auto; }
    /* lg-wide uses 14L / 6R + chevron margin-left:-12 to minimise the
       right-side dead space (pill is anchored to logs.right; user wants
       the chevron close to the logs edge). At lg-narrow the pill sits
       on its own left-aligned row, so use SYMMETRIC 14L / 14R padding
       and drop the chevron pull-in. */
    #hw-v3-pill.hw-v3-collapsed {
      padding:10px 14px;
    }
    #hw-v3-pill.hw-v3-expanded {
      padding:10px 14px 12px 14px;
    }
    .hw-v3-collapsed #hw-v3-toggle { margin-left:0; }
  }
  /* FLOAT-INTO-BAND ranges — md (768-1023) AND lg-wide (1280-1535).
     At both, the header band has enough dead space on its trailing row
     for the pill to float into. Pill is anchored RIGHT (flush with
     logs' right edge), with inline `top:-(h+10)` set by lockLgFloat so
     its top intrudes upward into the band. Logs sit at their natural
     top — no spacer reserved. (1024-1279 is the gap between these two:
     there the Command field wraps and consumes the dead space, so the
     pill takes its own row above logs — see the lg-NARROW block above.) */
  @media (min-width:768px) and (max-width:1023.98px),
         (min-width:1280px) and (max-width:1535.98px) {
    .hw-v3-layout { gap:0; }
    .hw-v3-spacer { display:none; }
    #hw-v3-pill.hw-v3-collapsed { right:0; left:auto; }
  }
  /* >lg / 4K-class running-state polish: dot is 6×6 from badges() now,
     no Live text to hide. Just tighten the head gap to 5px. */
  @media (min-width:1536px) {
    .hw-v3-collapsed .hw-v3-head { gap:5px; }
  }
  /* EXPANDED — overlay; vertical stack with sparklines (logs unchanged).
     Width capped at 420px so the expanded card doesn't stretch the full
     width of logs on mobile/md/lg; max-width:100% clamps on narrow
     screens. >lg overrides to 340 below. */
  #hw-v3-pill.hw-v3-expanded {
    right:0; width:420px; max-width:100%; padding:12px 14px;
  }
  @media (min-width:1536px) {
    #hw-v3-pill.hw-v3-expanded {
      /* Inline `right:-(W+10)` from lockLgAnchor persists across cycles
         (cleanup doesn't clear it). The right edge stays in the margin
         (10px past logs); only the width grows from W to 340px, pulling
         the LEFT edge into logs — overlay without right-edge shift. */
      left:auto;
      width:340px;
    }
  }
  /* lg (1024–1535): expanded keeps the same right edge AND the same
     floating top as collapsed. JS sets inline top/width/height. Don't
     let the base 420px width override JS's collapsedW. Padding matches
     the collapsed horizontal padding (14px L / 6px R) so the border
     doesn't visually shift between states. */
  @media (min-width:768px) and (max-width:1535.98px) {
    /* JS controls width on md+lg (locks collapsedW across both states).
       Don't let the legacy 420px rule override. Padding is set per
       sub-range below. */
    #hw-v3-pill.hw-v3-expanded { width:auto; }
  }
  @media (min-width:1024px) and (max-width:1279.98px) {
    /* lg-narrow expanded — symmetric L/R AND vertical: every vertical
       surface is 10px (top padding, bottom padding, row→row gap). */
    #hw-v3-pill.hw-v3-expanded { padding:10px 14px; }
  }
  @media (min-width:768px) and (max-width:1023.98px),
         (min-width:1280px) and (max-width:1535.98px) {
    /* md AND lg-wide expanded — asymmetric L/R (right minimal because
       pill is anchored to logs.right), but vertical surfaces all 10px. */
    #hw-v3-pill.hw-v3-expanded { padding:10px 6px 10px 14px; }
  }
  .hw-v3-expanded .hw-v3-head {
    /* No margin-bottom: the pill's column-flex gap (10px) is the SINGLE
       vertical-rhythm token. Any margin here would add to the gap and
       break the head→rows distance vs row→row equality. */
    display:flex; align-items:center; gap:5px; justify-content:flex-start;
  }
  .hw-v3-expanded .hw-v3-rows {
    /* gap MUST equal the pill's top+bottom padding (10) so the vertical
       rhythm (top padding → head → row gaps → bottom padding) is one
       single value — no eye-detectable asymmetry. */
    display:flex; flex-direction:column; gap:10px;
  }
  /* Match V2's spacing between metric title and sparkline (margin-bottom:5px). */
  .hw-v3-expanded .hw-v3-row { flex-direction:column; gap:5px; }
  .hw-v3-expanded .hw-v3-row-head {
    display:flex; align-items:center; gap:8px; justify-content:flex-start;
  }
  .hw-v3-expanded .hw-v3-row-spacer { flex:1; }
  .hw-v3-expanded .hw-v3-agg { display:inline; }
  .hw-v3-expanded .hw-v3-spark { display:block; }
  /* Shared chrome */
  /* hw-v3-title now uses the page-header label style (text-xs +
     text-gray-500 Tailwind classes on the <p>). Keep .hw-v3-title as
     a marker class only — no extra typographic overrides except a
     no-wrap rule so the pill widens to fit the title on one line. */
  .hw-v3-title { margin:0; white-space:nowrap; }
  .hw-v3-head-live { margin-left:0; }
  .hw-v3-toggle {
    margin-left:auto; background:transparent; border:none;
    color:#8b949e; cursor:pointer; padding:2px; border-radius:4px;
    display:inline-flex;
  }
  .hw-v3-toggle:hover { background:rgba(139,148,158,.15); color:#e6edf3; }
  /* Explicit `rotate(0deg)` base (not unset / not `none`) is REQUIRED
     for the transition to interpolate. Browsers don't animate from
     `transform: none` to `transform: rotate(...)`; the value jumps
     instantly to the end, making the chevron snap/flip rather than
     rotate smoothly. The eye reads the snap as a position shift.

     `will-change: transform` promotes the chevron to its own compositor
     layer so parent reflows (e.g. when `applyState` repaints sparklines
     or shows/hides the live badge after a job-state toggle) don't
     reset the chevron's CSS transition tracking. Without this, the
     first expand/collapse after a state change can snap instantly. */
  .hw-v3-chevron {
    transform: rotate(0deg);
    transition: transform .25s ease;
    transform-origin: 50% 50%;
    will-change: transform;
  }
  .hw-v3-expanded .hw-v3-chevron { transform:rotate(180deg); }
  .hw-v3-dot { width:8px; height:8px; border-radius:9999px; background:#6e7681; flex-shrink:0; }
  .hw-v3-row-label {
    font-size:10px; color:#8b949e; font-weight:600;
    text-transform:uppercase; letter-spacing:.05em;
  }
  .hw-v3-agg {
    font-size:9px; font-weight:600; letter-spacing:.07em;
    text-transform:uppercase; color:#8b949e;
  }
  .hw-v3-val {
    font-size:11px; color:#e6edf3; font-weight:500;
    font-variant-numeric:tabular-nums; white-space:nowrap;
  }
  .hw-v3-spark { height:30px; }
</style>'''

SCRIPT = '''
<script>
(function () {
  // Which render style each version uses
  var VSTYLE = { 'hw-v1':'bar', 'hw-v2':'spark', 'hw-v3':'pill' };
  var PREFIXES = ['hw-v1', 'hw-v2', 'hw-v3'];
  var v3Expanded = false;
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
      else if (style === 'pill') {
        // Dot drives the colour cue in collapsed mode; sparkline is rendered
        // always but only visible (via CSS) when the pill is expanded.
        var dot = document.getElementById(prefix + '-' + m + '-dot');
        if (dot) dot.style.backgroundColor = color;
        renderSpark(prefix, m, sparkSeries, color, sparkMode);
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

  // 4K-class only: measure the pill's natural collapsed width and lock
  // both inline width (length, so transitions animate) AND inline right
  // (= -(w + 10), so the pill's LEFT edge sits 10px past the logs' right
  // edge — i.e. in the page margin, with a 10px gap to logs).
  function lockLgAnchor(pill) {
    if (!matchMedia('(min-width: 1536px)').matches) {
      pill.style.right = '';
      pill.style.width = '';
      return;
    }
    var prevTrans = pill.style.transition;
    pill.style.transition = 'none';
    pill.style.right = '';
    pill.style.width = 'max-content';
    void pill.offsetWidth;
    var w = pill.offsetWidth;
    pill.dataset.collapsedW = w;
    pill.style.width = w + 'px';
    pill.style.right = -(w + 10) + 'px';   // 10px gap into the page margin
    void pill.offsetWidth;
    pill.style.transition = prevTrans;
  }

  // lg-NARROW (1024-1279) only: pill is position:absolute over a spacer
  // that reserves its collapsed height. Layout gap = 10px → the gap
  // between pill bottom and logs top = 10px IF spacer height = pill height.
  // At lg-WIDE the pill floats into header dead space; no spacer needed.
  function syncLgSpacer() {
    var pill = document.getElementById('hw-v3-pill');
    var spacer = document.getElementById('hw-v3-spacer');
    if (!pill || !spacer) return;
    if (isLgNarrow()) {
      void pill.offsetHeight;
      spacer.style.height = pill.offsetHeight + 'px';
    } else {
      spacer.style.height = '';
    }
  }

  // Anchored-pill range: md (768–1023) + lg (1024–1535). All these
  // viewports use the same polished horizontal chrome and the same
  // FLIP toggle path.
  function isLgRange() {
    return matchMedia('(min-width: 768px) and (max-width: 1535.98px)').matches;
  }
  // Float-into-band: pill is anchored RIGHT to logs.right, with
  // inline `top:-(h+10)` so its top intrudes upward into the header
  // band's trailing-row dead space. Applies at md (768–1023) AND
  // lg-wide (1280–1535). The gap range (1024–1279) is lg-narrow.
  function isLgWide() {
    return matchMedia('(min-width: 768px) and (max-width: 1023.98px)').matches
        || matchMedia('(min-width: 1280px) and (max-width: 1535.98px)').matches;
  }
  // Own-row above logs: pill is anchored LEFT, takes its own row
  // (spacer reserves vertical room) because Command wraps into the
  // header band's row-2 here, leaving no dead space.
  function isLgNarrow() {
    return matchMedia('(min-width: 1024px) and (max-width: 1279.98px)').matches;
  }

  // lg-WIDE only (1280–1535): pill floats ABOVE logs by 10px (visible
  // gap) but its top edge intrudes UPWARD into the header band's row-2
  // dead space, so no extra vertical space is reserved. Inline
  // `top: -(h + 10)` (relative to #hw-v3-layout = logs.top).
  // At lg-NARROW, the pill sits at top:0 of its own spacer slot — no
  // negative top is applied.
  function lockLgFloat(pill) {
    if (isLgWide()) {
      var prevTrans = pill.style.transition;
      pill.style.transition = 'none';
      pill.style.top = '';
      void pill.offsetHeight;
      var h = pill.offsetHeight;
      pill.style.top = -(h + 10) + 'px';
      void pill.offsetHeight;
      pill.style.transition = prevTrans;
    } else if (isLgNarrow()) {
      // Own-row layout: pill sits at top of its layout slot. Clear any
      // negative top carried over from a wide-lg cycle.
      pill.style.top = '0px';
    }
    // md/sm/>lg manage their own anchoring elsewhere.
  }

  // V3 pill is a flex child of #hw-v3-layout (which wraps the logs card).
  // Move it into the layout on activate so it participates in real layout.
  function attachV3() {
    var pill   = document.getElementById('hw-v3-pill');
    var layout = document.getElementById('hw-v3-layout');
    var spacer = document.getElementById('hw-v3-spacer');
    if (!pill || !layout) return;
    // Clear inline carryover before reinsert
    pill.style.width = '';
    pill.style.height = '';
    pill.style.right = '';
    pill.style.top = '';
    if (pill.parentElement !== layout) layout.insertBefore(pill, layout.firstChild);
    if (spacer) spacer.style.display = '';
    // Ensure collapsed state for the measurement
    pill.classList.add('hw-v3-collapsed');
    pill.classList.remove('hw-v3-expanded');
    v3Expanded = false;
    lockLgAnchor(pill);
    lockLgFloat(pill);
    syncLgSpacer();
  }
  function detachV3() {
    var pill   = document.getElementById('hw-v3-pill');
    var wrap   = document.getElementById('hw-v3-wrap');
    var spacer = document.getElementById('hw-v3-spacer');
    if (!pill || !wrap) return;
    pill.classList.remove('hw-v3-expanded');
    pill.classList.add('hw-v3-collapsed');
    v3Expanded = false;
    pill.style.right = '';
    pill.style.width = '';
    pill.style.height = '';
    if (pill.parentElement !== wrap) wrap.appendChild(pill);
    if (spacer) spacer.style.display = 'none';
  }

  // FLIP-style animation: measure current dims, apply new state, measure
  // target dims, lock to start, then on next frame set end. CSS transition
  // animates between length values.
  //
  // Fast-toggle race: if the user clicks before the previous transition
  // finishes, the previous toggle's pending rAF and cleanup listener can
  // overwrite or short-circuit the new toggle, leaving the pill stuck mid-
  // state. Track them in module-scope vars and cancel/detach on every new
  // entry so only the most recent toggle has effect.
  var v3PendingRAF = null;
  var v3PendingCleanup = null;
  window.hwToggleV3 = function (ev) {
    if (ev) ev.stopPropagation();
    var pill = document.getElementById('hw-v3-pill');
    var btn  = document.getElementById('hw-v3-toggle');
    if (!pill) return;

    // Cancel any pending pieces from the previous toggle so they don't
    // race with this one.
    if (v3PendingRAF !== null) { cancelAnimationFrame(v3PendingRAF); v3PendingRAF = null; }
    if (v3PendingCleanup) { pill.removeEventListener('transitionend', v3PendingCleanup); v3PendingCleanup = null; }

    // lg (1024–1535): collapsed pill floats above logs (negative top, lifted
    // into header band's dead space). On expand it STAYS at the same top and
    // same width; only height grows, so the pill grows DOWNWARD and overlays
    // the top of logs without dropping or shrinking horizontally.
    if (isLgRange()) {
      var lgStartH = pill.offsetHeight;
      var lgStartW = pill.offsetWidth;
      // Capture collapsed dims on first expand (anchor for both states)
      if (!v3Expanded) {
        pill.dataset.collapsedW = lgStartW;
        pill.dataset.collapsedH = lgStartH;
      }
      var lockedW = +pill.dataset.collapsedW || lgStartW;
      var lockedH = +pill.dataset.collapsedH || lgStartH;
      // lg-WIDE: pill floats above logs at top:-(h+10), intruding into
      //          header band's row-2 dead space.
      // lg-NARROW: pill sits in its own row above logs, top:0 of the
      //          layout slot (spacer reserves the vertical room).
      // BOTH states (collapsed/expanded) share the same lockedTop so the
      // title's y stays constant across the animation.
      var lockedTop = isLgWide() ? -(lockedH + 10) : 0;

      v3Expanded = !v3Expanded;
      pill.classList.toggle('hw-v3-expanded', v3Expanded);
      pill.classList.toggle('hw-v3-collapsed', !v3Expanded);
      if (btn) btn.title = v3Expanded ? 'Collapse' : 'Expand';
      applyState(currentState);

      // Measure target height with new class applied, width locked
      pill.style.width = lockedW + 'px';
      pill.style.height = 'auto';
      pill.style.top = lockedTop + 'px';
      void pill.offsetHeight;
      var lgEndH = v3Expanded ? pill.offsetHeight : lockedH;

      // Lock to start height so transition has a length→length to animate
      pill.style.height = lgStartH + 'px';
      void pill.offsetHeight;

      v3PendingRAF = requestAnimationFrame(function () {
        v3PendingRAF = null;
        pill.style.height = lgEndH + 'px';
      });

      v3PendingCleanup = function (e) {
        if (e.target !== pill || e.propertyName !== 'height') return;
        // Keep width + top locked; clear inline height to let content drive.
        pill.style.height = '';
        pill.removeEventListener('transitionend', v3PendingCleanup);
        v3PendingCleanup = null;
      };
      pill.addEventListener('transitionend', v3PendingCleanup);
      return;
    }

    var isLg = matchMedia('(min-width: 1536px)').matches;
    // Read the CURRENT animated dims (mid-transition gives the interpolated
    // value, which is what we want as the FLIP start).
    var startH = pill.offsetHeight;
    var startW = pill.offsetWidth;

    // Remember collapsed width on lg so we can animate back to it later.
    if (isLg && !v3Expanded) pill.dataset.collapsedW = startW;

    v3Expanded = !v3Expanded;
    pill.classList.toggle('hw-v3-expanded', v3Expanded);
    pill.classList.toggle('hw-v3-collapsed', !v3Expanded);
    if (btn) btn.title = v3Expanded ? 'Collapse' : 'Expand';
    applyState(currentState);

    // Measure target dimensions with the new state applied.
    pill.style.height = 'auto';
    pill.style.width  = '';
    var endH = pill.offsetHeight;
    var endW = isLg
      ? (v3Expanded ? 340 : (+pill.dataset.collapsedW || pill.offsetWidth))
      : pill.offsetWidth;

    // Lock back to START dimensions (no transition fires yet — same values).
    pill.style.height = startH + 'px';
    if (isLg) pill.style.width = startW + 'px';
    void pill.offsetHeight;

    // On the next animation frame, set END dimensions. The browser sees a
    // length→length change and runs the CSS transition smoothly.
    v3PendingRAF = requestAnimationFrame(function () {
      v3PendingRAF = null;
      pill.style.height = endH + 'px';
      if (isLg) pill.style.width = endW + 'px';
    });

    // Cleanup after transition: clear inline height so the pill returns to
    // content-sized height (no empty space). On lg, LOCK inline width to an
    // explicit pixel value — leaving it as CSS `width: max-content` can
    // resolve to a slightly different value than what we transitioned to,
    // which makes the 10px gap between pill and logs drift after each cycle.
    v3PendingCleanup = function (e) {
      if (e.target !== pill || e.propertyName !== 'height') return;
      pill.style.height = '';
      if (isLg) {
        pill.style.width = (v3Expanded ? 340 : (+pill.dataset.collapsedW || pill.offsetWidth)) + 'px';
      } else {
        pill.style.width = '';
      }
      pill.removeEventListener('transitionend', v3PendingCleanup);
      v3PendingCleanup = null;
    };
    pill.addEventListener('transitionend', v3PendingCleanup);
  };

  window.hwSetVersion = function (v) {
    currentVersion = v;
    ['v1', 'v2', 'v3'].forEach(function (k) {
      var w = document.getElementById('hw-' + k + '-wrap');
      if (w) w.style.display = (k === v) ? '' : 'none';
      var b = document.getElementById('hw-ver-' + k);
      if (b) b.classList.toggle('active', k === v);
    });
    // hw-v3-wrap is only a mount slot — the pill is moved into
    // #hw-v3-layout by attachV3. Keeping the wrap display:block leaves an
    // empty flex child in the page container, which still consumes one
    // `gap-4` (16px) of vertical gap above AND below itself, doubling the
    // header→logs gap. Keep it permanently hidden.
    var v3wrap = document.getElementById('hw-v3-wrap');
    if (v3wrap) v3wrap.style.display = 'none';
    if (v === 'v3') attachV3(); else detachV3();
    // Reveal the contextual state toggle now that a version is active
    document.getElementById('hw-state-tier').classList.add('open');
    applyState(currentState);
  };

  document.addEventListener('DOMContentLoaded', function () {
    hwSetVersion('v3');
    hwSetState('completed');
  });

  // Re-home the V3 pill on resize so crossing the lg/>lg boundary moves it
  // between the metadata band (lg collapsed) and the logs layout slot.
  var v3ResizeTimer = null;
  window.addEventListener('resize', function () {
    if (currentVersion !== 'v3') return;
    if (v3ResizeTimer) clearTimeout(v3ResizeTimer);
    v3ResizeTimer = setTimeout(function () {
      if (!v3Expanded) attachV3();   // only safe to re-home when collapsed
    }, 120);
  });
})();
</script>'''

HARDWARE_BLOCK = CONTROL + V1 + V2 + V3 + STYLE + SCRIPT

# ── 6. Find injection point and splice ────────────────────────────────────────
print("Finding injection point...")
LOGS_MARKER = '<div id="hw-v3-layout"'
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
