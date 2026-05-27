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

### 2. V3 pill right edge is FLUSH with logs container right edge on lg/4K

- **What:** On `≥1536px` viewports, the V3 pill's right edge is flush with
  the logs container's right edge (overlay at top-right; pill does NOT
  exceed the log container into the page margin). Applies in both
  collapsed and expanded states.
- **Why:** User originally wanted a 12px gap with the pill floating in the
  margin; then changed the requirement to "align right edge with log right
  edge" (pill overlays instead of floats outside).
- **Established / changed:** updated this iteration (see commit).
- **How to verify:**
  ```js
  var pill = document.getElementById('hw-v3-pill');
  var card = document.getElementById('hw-logs-card');
  Math.round(pill.getBoundingClientRect().right - card.getBoundingClientRect().right)
  // Must equal 0 (give or take 1px for subpixel rounding).
  ```
- **Common ways it breaks:**
  - Inline `right` override that doesn't equal 0 (lockLgAnchor used to
    set `right:-(12+w)` — that's been removed; don't re-introduce it)
  - CSS `right:-Npx` on the breakpoint rule (push pill into margin)

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
