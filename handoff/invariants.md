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

### 2. Gap between V3 pill and logs container = 12px on lg/4K

- **What:** On `≥1536px` viewports, the V3 collapsed pill sits exactly
  12px to the right of the logs container's right edge. Not 20px, not 39px.
- **Why:** User flagged a widened gap as "unwantedly changed" after a
  width/anchor refactor.
- **Established:** during the polish iteration where width:148 → max-content
- **How to verify:**
  ```js
  var pill = document.getElementById('hw-v3-pill');
  var card = document.getElementById('hw-logs-card');
  Math.round(pill.getBoundingClientRect().left - card.getBoundingClientRect().right)
  // Must equal 12 (give or take 1px for subpixel rounding).
  ```
- **Common ways it breaks:**
  - Switching `width` from a fixed length to `max-content`/`auto` while
    leaving `right` anchored at a fixed offset → left edge floats
  - Removing the JS `lockLgAnchor` step that measures content width and
    sets a matching `right` value
  - Changes to `padding` on the pill that shift the inner content width
    without re-anchoring

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

### 5. Logs container is fully visible (not partially clipped by widget)

- **What:** The widget is overlay only when EXPANDED; collapsed widget
  must never cover log content. On lg/4K it floats in the margin (not
  overlapping logs at all).
- **How to verify:**
  ```js
  var pill = document.getElementById('hw-v3-pill');
  var card = document.getElementById('hw-logs-card');
  // Collapsed: pill should be entirely to the right of logs
  pill.getBoundingClientRect().left >= card.getBoundingClientRect().right
  ```
- **Common ways it breaks:**
  - `right` anchor changes between states (right edge shifts on toggle —
    user rejected this earlier)

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
