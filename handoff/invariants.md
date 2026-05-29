---
name: invariants
description: Standing user-stated expectations for the Jobs hardware-utilization widget. Read & verify EVERY entry before declaring iteration complete. See ~/.claude/skills/verification-loop/SKILL.md for the procedure.
metadata: 
  node_type: memory
  type: project
  originSessionId: 8e315ad4-b1cb-430c-b40c-de93d42e156c
---

# Invariants — Jobs hardware-utilization widget

Every entry is a user-stated expectation that has regressed at least once
in this project's history. Walk through ALL of them before declaring an
iteration complete. Don't shortcut by reasoning "my change shouldn't have
touched X."

---

### 1. V3 expand/collapse animation is smooth (height AND width)

- **What:** Toggling the V3 pill between collapsed and expanded must
  *visually animate* both width and height over ~300ms. Not instant.
- **Why:** User has had to re-state this three times across the session.
- **Established:** d8b21fe (after multiple regressions)
- **How to verify:**
  1. Ensure tab visibility: `document.visibilityState === "visible"` —
     otherwise rAF/transitions are throttled and you can't measure honestly.
  2. Click the chevron (or call `hwToggleV3()`).
  3. Watch the transition visually OR sample `getBoundingClientRect()` at
     t=0, 50, 100, 200, 300ms — values should change monotonically across
     the window.
  4. Best verification: screenshot at t=50 and t=250 mid-transition;
     both should show intermediate sizes.
- **Common ways it breaks:**
  - Replacing explicit pixel heights with `auto` (CSS can't transition auto)
  - Adding `interpolate-size: allow-keywords` while ALSO setting inline
    px via JS (the two fight each other)
  - Setting start/end inline values in the same synchronous JS tick
    without `requestAnimationFrame` (Chrome batches them)
  - Forgetting `void pill.offsetHeight` to force reflow between writes

### 1e. Live dot is 5px-right and 0px-vertically-offset from title

- **What:** When `state === 'running'`, the pulsing green dot's center
  must be exactly `5px` to the right of the title's right edge AND
  vertically centered with the title's text (±2px). Holds in **every
  state × every breakpoint × every variant** (V1, V2, V3 collapsed, V3
  expanded; sm/md/lg/2xl).
- **Why:** The first sweep at this checked only the horizontal gap and
  missed the lg-specific bug where `align-items:flex-start` (used to
  anchor the title during the FLIP animation) top-aligned the dot,
  putting its center 5px above the title's visual center.
- **Established:** this iteration. Earlier 4a (skill) checked x only.
- **How to verify (BOTH axes; run at lg + >lg in both states):**
  ```js
  hwSetState('running');
  await new Promise(r => setTimeout(r, 200));
  function probe() {
    var dot = document.querySelector('#hw-v3-live-badge > span');
    var title = document.querySelector('#hw-v3-pill .hw-v3-title');
    var d = dot.getBoundingClientRect(), t = title.getBoundingClientRect();
    return {
      x_gap: Math.round(d.left - t.right),                         // must be 5
      y_offset: Math.round((d.top+d.bottom)/2 - (t.top+t.bottom)/2) // must be 0±2
    };
  }
  // collapsed:
  probe();
  // toggle to expanded, sample again:
  hwToggleV3(); await new Promise(r => setTimeout(r, 400));
  probe();
  ```
  Both probes must satisfy `x_gap === 5 && Math.abs(y_offset) <= 2`.
- **Common ways it breaks:**
  - Pill uses `align-items:flex-start` (correct for title anchoring) but
    no compensating `margin-top` on the badge — dot floats to top of
    title's line-box. Add `margin-top: 5px` (for 16px line-height title
    + 6px dot).
  - Stale `margin-left:4px` (or any other) on `.hw-v3-head-live`.
  - Parent flex `gap` raised above 5 without a matching negative
    `margin-left` on the badge.
  - Dot size changed from 6 without re-tuning `margin-top`.

### 1d. Title stays anchored across expand/collapse (zero vertical shift)

- **What:** During the entire expand and collapse animation, the
  `Hardware Utilization` title's viewport `top` MUST stay at the same
  y-coordinate (±2px tolerance). It must not slam down to the pill's
  vertical centre when the class flips and then crawl back up as the
  height shrinks.
- **Why:** User-reported: "the collapsed content snaps to the bottom
  and moves up... very basic mistake." The title's content doesn't
  change between states — therefore its position must not change.
- **Established:** this iteration.
- **How to verify (mandatory before declaring any toggle change done):**
  ```js
  (async () => {
    var pill = document.getElementById('hw-v3-pill');
    var title = pill.querySelector('.hw-v3-title');
    var samples = [];
    hwToggleV3();
    for (var i = 0; i < 30; i++) {
      await new Promise(r => requestAnimationFrame(r));
      samples.push(Math.round(title.getBoundingClientRect().top));
    }
    return {
      min: Math.min(...samples), max: Math.max(...samples),
      range: Math.max(...samples) - Math.min(...samples)   // MUST be ≤ 2
    };
  })()
  ```
  Then run again to test collapse direction. Both ranges ≤ 2.
- **Common ways it breaks:**
  - `align-items:center` on the collapsed pill (centres title in the
    transient too-tall pill during collapse) — use `flex-start` instead.
  - `padding-top` differs between collapsed and expanded states.
  - JS changes `pill.style.top` between states (currently locked via
    `lockedTop = -(collapsedH + 10)` and used for BOTH states; don't
    regress that).
  - Inserting an element only present in one state ABOVE the title
    (would shift title down in that state).

### 1c. V3 fast-toggle survives rapid clicks (no stuck mid-state)

- **What:** Clicking the V3 chevron rapidly (faster than the .3s
  transition) must always land the pill in the FINAL intended state
  (either fully collapsed or fully expanded — matching the parity of
  click count) — never stuck mid-transition.
- **Why:** User flagged "didn't go all the way back" after fast
  collapse/expand on >lg.
- **Established:** d5c350d.
- **How to verify (manual, on visible tab):**
  - Click chevron 4 times in quick succession (~100ms apart). Pill
    should end in the SAME state it started (4 toggles = identity).
  - Click 3 times in quick succession. Pill should end in the
    OPPOSITE state (3 toggles = flip).
  - In both cases, no intermediate width/height locked inline.
- **Common ways it breaks:**
  - Forgetting to `cancelAnimationFrame` on the pending rAF id at the
    top of `hwToggleV3` — the previous rAF will fire AFTER the new
    toggle and overwrite start values
  - Forgetting to `removeEventListener` on the pending transitionend
    cleanup — both old and new cleanups fire, racing each other
  - Adding new async steps (timeouts, microtasks) inside `hwToggleV3`
    without making them cancelable too

### 1b'. V3 lg-NARROW (1024–1279): own row above logs, left-aligned

- **What:** At `1024 ≤ vw ≤ 1279`, the V3 pill takes its OWN vertical
  row above the logs container. Pill is left-aligned (left edge = logs
  left edge). 10px gap between pill bottom and logs top. The pill MUST
  NOT overlap the page-header metadata band (no dead space exists at
  this viewport because the Command field has wrapped into row-2 of
  the band).
- **Why:** User-reported at vw=1024 — the floating widget overlapped
  Env vars / Secrets text. "No empty space" for the widget to float into.
- **Established:** this iteration.
- **How to verify:**
  ```js
  var band = document.querySelector('.text-smd.flex.flex-wrap.gap-x-10');
  var pill = document.getElementById('hw-v3-pill');
  var card = document.getElementById('hw-logs-card');
  var b = band.getBoundingClientRect();
  var p = pill.getBoundingClientRect();
  var c = card.getBoundingClientRect();
  ({
    leftAligned: Math.round(p.left - c.left),    // must be 0
    gapToLogs:   Math.round(c.top - p.bottom),    // must be 10
    notOverlapsBand: p.top >= b.bottom            // must be true
  })
  ```
- **Common ways it breaks:**
  - Hiding the spacer at lg-narrow (logs collapse upward, no row reserved).
  - Anchoring `right:0` instead of `left:0`.
  - Setting `top:-(h+10)` via `lockLgFloat` (would intrude into band).

### 1b. V3 lg-WIDE collapsed (1280-1535): floats INSIDE header band row-2

- **What:** On `1024–1535px` viewports, the V3 collapsed pill is a child
  of `#hw-meta-band` (the page-header metadata flex-wrap row with
  Status / Created / Hardware / Image / Command / Env vars / Secrets).
  It sits as a flex-wrap peer of those fields, pushed to the right edge
  via `margin-left:auto`, filling the row-2 dead space WITHOUT
  introducing any new vertical space above logs.
  - Title `"Hardware Utilization"` visible at the start (left), chevron
    inline at the far right
  - 3 metric chips inline (no wrap), tight gap (10px pill, 5px chip)
  - Right edge **flush with band's right edge** (= logs' right edge)
  - **Pill parent === `#hw-meta-band`** (not `#hw-v3-layout`)
  - No spacer above logs (logs at natural position)
- **Why:** User's spec — "I don't want the widget to occupy another
  vertical space. It will be floating in the header container."
- **Established:** this iteration (supersedes previous "above logs" spec).
- **How to verify:**
  ```js
  var pill = document.getElementById('hw-v3-pill');
  var band = document.getElementById('hw-meta-band');
  var p = pill.getBoundingClientRect(), b = band.getBoundingClientRect();
  ({
    parent: pill.parentElement.id,                  // must be "hw-meta-band"
    rightAlign: Math.round(b.right - p.right),      // must be 0
    insideBand: p.top >= b.top && p.bottom <= b.bottom + 8,
    horizontal: p.width > p.height * 3,
    titleShown: pill.querySelector('.hw-v3-title').offsetHeight > 0
  })
  ```
- **Common ways it breaks:**
  - `attachV3()` not detecting lg range and dropping pill into
    `#hw-v3-layout` instead of `#hw-meta-band`
  - Base `position:absolute` not overridden by the lg-specific
    `position:static` rule (selector chain
    `#hw-meta-band > #hw-v3-pill.hw-v3-collapsed` matters)
  - Removing `margin-left:auto` (pill packs left after Secrets, leaving
    dead space on the right)
  - Forgetting to clear inline `right`/`width`/`height` from a >lg cycle
    when re-attaching at lg

### 2. V3 pill collapsed left edge is 10px past logs right edge on lg/4K

- **What:** On `≥1536px` viewports, the V3 collapsed pill floats in the
  page margin with a **10px gap** between the logs container's right edge
  and the pill's left edge. (Pill is NOT flush with logs; it sits in the
  page margin to the right of logs.)
- **Why:** User's final spec for the >lg layout. Rewound after a brief
  detour to a "flush" design and a "12px gap" design.
- **How to verify:**
  ```js
  var pill = document.getElementById('hw-v3-pill');
  var card = document.getElementById('hw-logs-card');
  Math.round(pill.getBoundingClientRect().left - card.getBoundingClientRect().right)
  // Must equal 10 (± 1px for subpixel rounding).
  ```
- **Companion behavior on expand (see also invariant #7):** the pill's
  RIGHT edge stays anchored at `logs.right + W_collapsed + 10`. Width
  grows from W_collapsed to 340, so the LEFT edge moves inward over
  logs while the right edge stays in the margin — overlay without shift.
- **Common ways it breaks:**
  - `lockLgAnchor` not setting inline `right:-(W+10)` (CSS fallback
    `right:0` would make the pill flush with logs instead)
  - Changing the `+10` constant without updating this entry

### 2b. Inter-metric vertical spacing in V3 collapsed = 6px

- **What:** On lg/4K collapsed pill, the vertical gap between the three
  metric rows (GPU, MEM, CPU) is the tight `gap:6px`, not the looser
  10px the first version had.
- **Why:** User flagged the row spacing as too big.
- **How to verify:** `getComputedStyle(document.querySelector('.hw-v3-collapsed .hw-v3-rows')).rowGap` → `"6px"`
- **Common ways it breaks:** any refactor of the `.hw-v3-rows` CSS

### 3. Logs container width is NOT compromised by the widget

- **What:** The logs card occupies its full container width at every
  breakpoint. The widget never reduces logs width — it lives in the
  margin (lg/4K) or above (sm/md).
- **Why:** Original spec requirement; user re-stated explicitly.
- **How to verify:**
  ```js
  var card = document.getElementById('hw-logs-card');
  var layout = document.getElementById('hw-v3-layout');
  // Logs card width should equal layout width on lg/4K
  card.getBoundingClientRect().width === layout.getBoundingClientRect().width
  ```
- **Common ways it breaks:**
  - Putting widget back into the flex flow on lg (as a row sibling) so it
    steals horizontal space
  - Adding padding-right to the logs container to make room

### 4. No empty space at the bottom of the widget in any state

- **What:** Widget height is content-driven; no trailing dead space below
  the last metric.
- **How to verify:**
  - Visual screenshot in collapsed AND expanded states; the border should
    end immediately after the last row's bottom padding.
  - Compare `pill.offsetHeight` against approximated content height.
- **Common ways it breaks:**
  - Setting explicit `height: <generous-px>` for animation purposes
  - Leaving `min-height` on the pill from a previous experiment

### 5. Logs main content area (header + log lines) is readable

- **What:** On lg/4K, the V3 collapsed pill overlays the **top-right
  corner** of the logs card (flush with right edge — see invariant #2).
  That overlap is intentional and acceptable. What matters: the logs
  HEADER ("Logs" title) and the visible log lines remain readable. The
  pill must not extend so far left that it covers a meaningful column of
  log content.
- **How to verify:**
  ```js
  var pill = document.getElementById('hw-v3-pill');
  var card = document.getElementById('hw-logs-card');
  var cardRect = card.getBoundingClientRect();
  var pillRect = pill.getBoundingClientRect();
  // Pill should be in the right portion of logs, not crossing the midpoint.
  pillRect.left > cardRect.left + cardRect.width * 0.5
  ```
- **Common ways it breaks:**
  - Pill width grows too large in collapsed state (should hug content)
  - Pill anchor flips back to `left:0` (would push right edge way out)

### 6. Widget chrome matches page chrome

- **What:** V3 pill border color = logs-card border color. V3 pill bg
  = page bg. "Hardware" title = page-header label style (text-xs /
  text-gray-500 / no uppercase / no letter-spacing tweak).
- **How to verify:**
  ```js
  var pill = document.getElementById('hw-v3-pill');
  var card = document.getElementById('hw-logs-card');
  var bodyBg = getComputedStyle(document.body).backgroundColor;
  var title = pill.querySelector('.hw-v3-title');
  ({
    borderMatch: getComputedStyle(pill).borderTopColor ===
                 getComputedStyle(card).borderTopColor,
    bgMatch: getComputedStyle(pill).backgroundColor === bodyBg,
    titleTransform: getComputedStyle(title).textTransform === 'none',
    titleSize: getComputedStyle(title).fontSize === '12px'
  })
  ```
- **Common ways it breaks:**
  - Hardcoding hex values instead of using Tailwind classes
    (`border-gray-200`, `bg-white dark:bg-gray-950`)
  - Reintroducing uppercase / letter-spacing on the title

### 7. lg expand grows INWARD without shifting

- **What:** On expand at lg/4K, the pill's right edge stays anchored;
  width grows leftward over the logs (overlay). The right edge does NOT
  move between collapsed and expanded.
- **How to verify:**
  ```js
  // Toggle, then compare right-edge x-coord before/after.
  // Right edges must be equal.
  ```
- **Common ways it breaks:**
  - Anchoring at `left` instead of `right` (changes growth direction)
  - Different `right` values for collapsed vs expanded states

### 8. Real HF Jobs states only (no fictional "Queued")

- **What:** Status options are RUNNING / COMPLETED / ERROR / CANCELLED.
  Never "Queued" — it doesn't exist in the HF Jobs API.
- **How to verify:**
  ```js
  [...document.querySelectorAll('.hw-pill')].map(p => p.textContent)
  // Must be exactly: ["Running", "Completed", "Error", "Cancelled"]
  ```
- **Common ways it breaks:**
  - Refactor that pulls from an older state list

### 9. Per-metric colour semantics (not a unified traffic light)

- **What:**
  - GPU Memory: ceiling scale (indigo < 80% / amber 80-94% / red ≥ 95%
    or Failed)
  - GPU Utilisation: INVERTED — low average flags wasted spend; high is
    neutral (indigo)
  - CPU: always neutral (never alarmed)
- **How to verify:** Toggle through each state and confirm gauge colours
  follow the per-metric rules. Watching `metricColor()` JS function is
  the authoritative source.
- **Common ways it breaks:**
  - Refactoring `metricColor()` to a single shared scale across metrics

---

## Verification report template

After running the loop, paste this into the end-of-turn summary:

```
Invariants verified:
1. V3 animation smooth ........ PASS / FAIL / UNCHECKED
2. 12px gap to logs ........... PASS / FAIL / UNCHECKED
3. Logs full width ............ PASS / FAIL / UNCHECKED
4. No empty space ............. PASS / FAIL / UNCHECKED
5. Logs not clipped ........... PASS / FAIL / UNCHECKED
6. Chrome matches page ........ PASS / FAIL / UNCHECKED
7. lg expand no right shift ... PASS / FAIL / UNCHECKED
8. Real HF states only ........ PASS / FAIL / UNCHECKED
9. Per-metric colours ......... PASS / FAIL / UNCHECKED
```
