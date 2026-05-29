---
name: hw-widget-design
description: Locked design standards for the Jobs hardware-utilization widget (Chunte's prototype). Apply BEFORE proposing any visual change — spacing, padding, gaps, colours, breakpoint behaviours, animation pattern. Stops the back-and-forth where small spacing / padding / chrome tweaks regress because they were never written down. Trigger this whenever the user asks for any visual tweak to V1/V2/V3 widgets in `C:\HuggingFace\Job Gauges` (or the deployed `chuntelee.github.io/jobs-hardware-widget` prototype), and BEFORE editing `build.py` for any layout/spacing change.
---

# Hardware-utilization widget — design standards

These are the **frozen** design decisions for the Jobs hardware-utilization
widget prototype. They aren't open for re-litigation. If you're tempted to
change a value below, first re-read the user's collaboration style in
`memory/feedback_design_collaboration.md` and the verification-loop skill.

When the user says "the spacing looks off" or "the padding doesn't match",
your first move is to check whether the actual values match this document
— and if they don't, *that's* the bug. Don't guess new numbers.

---

## 0. Rhythm tokens (THE single source of truth for spacing)

Every gap/padding in the widget MUST resolve to ONE of these tokens.
If you find yourself wanting "12px because it looks better," stop —
either retune the token (and update this table + audit every site)
or accept the rhythm token. Single drifting values are how the
"uneven spacing" complaint repeats.

| Token | Value | Where it applies |
|---|---|---|
| **H-MAJOR** | 20px | Pill flex `gap`; rows-container `gap` (chip↔chip and title↔chip) |
| **H-MINOR** | 14px | Pill horizontal padding (L=14, R=14 narrow; R=6 wide exception) |
| **V-MAJOR** | 10px | Pill column-flex `gap` (head↔rows, row↔row); pill top+bottom padding |
| **V-INNER** | 5px | row column gap (row-head↔sparkline); title↔dot |
| **CHIP** | 6px | row-head internal gap (dot↔label↔val) |
| **DOT-TITLE** | 5px | live dot offset (both x AND y) |

The **only** allowed exceptions:
- lg-wide pill right padding = 6 instead of 14 (chevron must sit close
  to logs.right — documented in section 7).
- expanded pill bottom-padding token is V-MAJOR (10) NOT 12. If you see
  12, that's a drift, fix it.

**Audit before declaring any spacing change done.** Run the rhythm
audit snippet from the verification-loop skill (Layout / spacing
section). It must pass with TOKEN=V-MAJOR for vertical surfaces and
TOKEN=H-MAJOR for horizontal surfaces. Any surface that drifts gets
named and fixed — don't ship "close enough."

## 1. Spacing rhythm (the rule that catches people out most)

The widget pill has **two** flex containers nested inside each other, and
their gaps must match or the rhythm looks broken:

| Container                            | Property         | Value |
|--------------------------------------|------------------|-------|
| `#hw-v3-pill`                        | `gap`            | **20px** |
| `.hw-v3-rows` (inside pill)          | `gap`            | **20px** |
| `.hw-v3-row` (single chip)           | `gap`            | 6px |
| `.hw-v3-row-head` (dot/label/val)    | `gap`            | 6px |

**Why 20=20:** The pill's flex items are `[title][live-badge?][rows][toggle]`
with `gap:20`. The rows container's flex items are
`[chip][chip][chip]` with `gap:20`. If those two numbers differ, the eye
sees an asymmetric rhythm — e.g. "title → chip 1" looks tighter (or
looser) than "chip 1 → chip 2". The user *will* notice. Both 20.

**No tightening one without the other.** If you reduce one, reduce both.

**`min-width:80px` on chips is a mobile-only carryover** — it must be
explicitly overridden in the lg block (`min-width:0` on both `.hw-v3-row`
and `.hw-v3-row-head`). If you leave the mobile rule applying at lg,
each chip is forced to ≥80px even when content is narrower, which adds
invisible trailing space inside the chip. That trailing space then ADDS
to the chip-to-chip flex gap, so chip→chip looks wider than title→chip
even though both gaps are CSS-equal. (User-reported regression; the
asymmetry is invisible from CSS inspection alone — measure
`chip.right - val.right` to confirm trailing == 0.)

## 2. Padding (collapsed AND expanded must match horizontally)

| State     | Padding (top right bottom left) |
|-----------|---------------------------------|
| Collapsed | `8px  6px  8px  14px` |
| Expanded  | `12px 6px  12px 14px` |

- **Left/right are identical across states** (14L / 6R). The right edge is
  asymmetric: only 6px because the chevron sits at the right and pulling
  the chevron close to the border is the goal. The chevron also gets
  `margin-left:-12px` to sit close to the CPU chip.
- **Vertical is allowed to differ** (8 collapsed / 12 expanded) — the
  expanded form has stacked sparklines and wants more breathing room.

If the user complains "padding doesn't match", they almost always mean
**horizontal**. Match L/R; vertical can change.

## 3. Chrome (border, background, title typography)

- **Border:** Tailwind `border border-gray-200 dark:border-gray-800` —
  same colour as the logs-card border. Never hardcode hex.
- **Background:** Tailwind `bg-white dark:bg-gray-950` — matches the page
  background. Same.
- **Title:** `<p class="text-xs text-gray-500">Hardware Utilization</p>` —
  matches the page-header metadata labels (Status / Created / Hardware /
  Image / etc.). No uppercase, no letter-spacing, no font-weight tweak.
- **Border-radius:** 12px on the pill.
- **Shadow:** `0 4px 14px rgba(0,0,0,.35)` (subtle, lifts pill above page).

## 4. Colours (per-metric, NOT a traffic light)

The escalation rule is per-metric. **Never** unify into a single shared
scale.

| Metric          | Default | Amber                    | Red                                |
|-----------------|---------|--------------------------|------------------------------------|
| **GPU Memory**  | indigo `#6366f1` | 80–94%      | ≥95% OR job=Error (OOM signal)     |
| **GPU Util**    | indigo (running) | AVG <40%   | AVG <15% (wasted spend, *low* bad) |
| **CPU Util**    | indigo (always)  | —          | — (CPU is a relational tell only)  |

- GPU Util is **inverted**: low is the alarm because high = healthy use.
- CPU never goes amber/red. It's neutral context only.
- Running state never goes red (live values bounce; only avg/peak alarm).
- Never green. Green would moralise "normal load" as "good."

## 4a. Live indicator (running state only)

- **No "Live" text.** The word was dropped — the pulsing green dot
  speaks for itself.
- **Dot size:** 6×6 px, green `#22c55e`, with a ping animation halo.
- **Gap from title:** **5 px** (dot left-edge to title right-edge). Holds
  across **all breakpoints** and **all variants** (V1 / V2 / V3 collapsed
  / V3 expanded).
- **Visible only when** `state === 'running'`. Hidden display:none
  otherwise.
- **How to verify (BOTH axes — single-axis check missed an lg
  alignment bug):** measure x-gap AND y-offset in every context with
  state=running:
  ```js
  var d = document.querySelector('#hw-v3-live-badge > span').getBoundingClientRect();
  var t = document.querySelector('#hw-v3-pill .hw-v3-title').getBoundingClientRect();
  ({
    x_gap:    Math.round(d.left - t.right),                          // must be 5
    y_offset: Math.round((d.top+d.bottom)/2 - (t.top+t.bottom)/2)    // must be 0 ±2
  })
  ```
  Run in collapsed AND expanded for V3, plus V1 and V2. All must pass
  both assertions. Checking only `x_gap` is incomplete and lets the
  dot float above the title's text center.
- **Common ways it breaks:** leftover `margin-left` on `.hw-v3-head-live`
  (was 4px historically); the badge's own internal `gap` from when "Live"
  text was a sibling; head/pill flex gap accidentally bumped above 5
  without a compensating negative `margin-left` on the badge in lg's
  display-contents context (currently `-15px` to offset the pill's 20px
  gap).

## 5. Aggregation tags (the muted micro-tag)

| Metric          | Aggregate | Tag display |
|-----------------|-----------|-------------|
| GPU Memory      | PEAK      | `PEAK` (3-letter, uppercase, muted grey, 9px, +.07em letter-spacing) |
| GPU Utilisation | AVG       | `AVG` |
| CPU Utilisation | AVG       | `AVG` |

The tag prefixes the value (e.g. `PEAK 42.4 / 48 GB`). On Running state,
tags are hidden and a `Live` badge appears (running shows instantaneous
value, no aggregation).

## 6. Job state vocabulary (only HF's real states)

`RUNNING` / `COMPLETED` / `ERROR` / `CANCELLED`. Never "Queued" — there
is no Queued stage in the HF Jobs API. Cancelled = partial run, neutral
grey, **no red** (the user stopped it; nothing went wrong).

The widget MUST NOT echo the job's lifecycle status — the page header
owns Status. Widgets show *what their numbers mean*, not *what state the
job is in*. (Exception: the prototype's job-state toggle drives the
replicated header Status cell for preview coherence.)

## 7. Responsive behaviour (V3 only — V1/V2 stay inline above logs)

V3 is the responsive pill anchored to the logs container. The pill is
ALWAYS `position:absolute` inside `#hw-v3-layout` (a flex wrapper around
the logs card). It never lives in the page-header DOM. It never lives
in the logs-card DOM.

| Viewport (Tailwind)         | Collapsed                                              | Expanded                                                                                          |
|-----------------------------|--------------------------------------------------------|---------------------------------------------------------------------------------------------------|
| **sm < 768**                | Full-width row above logs, horizontal chips            | Same width, grows downward into logs (overlay)                                                    |
| **md 768–1023**             | Same float-into-band treatment as lg-wide: horizontal row floating with inline `top:-(h+10)`; right edge flush with logs.right; 10px gap to logs. At 768 the band wraps to 3 rows (Secrets is alone on row-3) so the pill floats in row-3's right dead space. | Same top, same width; height grows. Overlays logs top. |
| **lg-narrow 1024–1279**    | Horizontal row above logs, **left-aligned** to logs.left. Pill takes its own vertical row (spacer reserves height). Logs are pushed down by ~pillH + 10. Inline `top:0`. | Same top + same width; height grows. Overlays the top of logs (logs visually slide under the pill). |
| **lg-wide 1280–1535**       | Horizontal row floating with inline `top:-(h+10)` so the pill's top intrudes into the page-header band's row-2 dead space; right edge flush with logs.right; 10px visible gap to logs | **Same top, same width** — only height grows. Pill grows downward, overlaying logs top. NEVER drops to logs.top, NEVER shrinks horizontally. |
| **2xl ≥1536** (4K-class)    | Vertical pill floating in the right page margin, 10px past logs.right; width = max-content captured by `lockLgAnchor()`; right edge `-(W+10)` | Right edge stays in margin (`right:-(W+10)`); width grows from W → 340px, pulling LEFT edge into logs — overlay without right-edge shift |

**lg-narrow vs lg-wide — why split:** at 1024–1279, the page-header's
Command field wraps to row-2 of the band, consuming most of that row.
Less than the pill's width remains as dead space, so the floating-into-
header trick used at lg-wide would overlap Env vars / Secrets text. At
lg-narrow the pill therefore takes its own row above logs (left-aligned,
spacer reserves vertical room). At lg-wide the Command field fits on
row-1; row-2 is mostly empty; the pill floats into that dead space
(right-aligned, no extra vertical space).

**lg-wide don'ts:**
- Don't reparent the pill into the page-header DOM. That was tried and
  rejected — the pill should not be coded inside the header group.
- Don't show the spacer (`.hw-v3-spacer { display:none }` at lg-wide) —
  logs sit at their natural position; the pill floats over the
  band/logs boundary.
- Don't reset `top:0` on expand. Lock `top: -(collapsedH + 10)` across
  BOTH states; only height animates.

**lg-narrow don'ts:**
- Don't anchor right. Anchor LEFT (`left:0; right:auto`).
- Don't try to intrude into the band — there's no dead space there.
- Don't hide the spacer; it reserves the vertical row.

**Key JS hooks:**
- `lockLgAnchor(pill)` — 2xl only; sets inline `right:-(W+10)` and
  `width:W` so the pill floats in the right margin and width is a length
  (transitions need length→length).
- `lockLgFloat(pill)` — lg only; sets inline `top:-(h+10)` so the pill's
  top intrudes upward into the header band.
- `pill.dataset.collapsedW` / `collapsedH` — captured on first attach;
  the FLIP animation reuses them so collapsed/expanded share an anchor.

## 7a. Content-anchoring rule (the most basic mistake to avoid)

**Any element that exists in BOTH the collapsed and expanded state must
stay at the same viewport `top` across every frame of the transition —
not just at the start and end.**

In practice for V3 this means the **title** ("Hardware Utilization") and
any other unchanged element (`Live` badge when present, chevron icon)
must not slide vertically during the height animation.

The class of mistake this catches: when the pill is mid-animation, its
inner flex layout has *already* flipped to its target state, but the
height is still locked to the SOURCE state's value. If `align-items` is
`center` on the pill, the title gets vertically centered in a 207-tall
pill that's about to shrink to 35 — i.e. it teleports ~90px down at t=0,
then "rises" back during the animation. The user sees the title slam to
the bottom of the pill and crawl back up. Basic, ugly, very visible.

**Mandatory rules:**
1. `align-items` MUST be `flex-start` on the collapsed pill, NOT `center`.
   (In column-flex expanded mode, default `stretch` is fine.)
2. `padding-top` MUST be identical between collapsed and expanded states
   so the title's `y` is identical at the final frame of expand and the
   first frame of collapse. Bottom/horizontal padding may differ.
3. The same rule applies to width: any element existing in both states
   must keep the same x. Don't change pill `width` during the toggle.

**How to verify (mandatory before declaring a toggle change done):**
Sample `title.getBoundingClientRect().top` every animation frame for the
full transition. The sample array must be effectively constant (≤2px
variance from end-state across all frames). If any frame differs by more
than 2px, the title is shifting — the toggle is broken.

```js
// Sample helper — paste into preview eval after change
(async () => {
  var pill = document.getElementById('hw-v3-pill');
  var title = pill.querySelector('.hw-v3-title');
  var samples = [];
  hwToggleV3();
  for (var i = 0; i < 30; i++) {
    await new Promise(r => requestAnimationFrame(r));
    samples.push(Math.round(title.getBoundingClientRect().top));
  }
  return {min: Math.min(...samples), max: Math.max(...samples), range: Math.max(...samples) - Math.min(...samples)};
})()
// range must be ≤ 2
```

## 8. Expand/collapse animation (FLIP, not naïve transition)

All breakpoints animate by measuring `getBoundingClientRect()` before and
after the state change, locking the pill to the START dimensions, then
on the NEXT `requestAnimationFrame` setting END dimensions. CSS transition
runs length→length. `transitionend` cleanup clears inline height (so
content drives) but keeps width/top locked (so the pill stays anchored).

**Race fix is mandatory.** Module-scope `v3PendingRAF` and
`v3PendingCleanup`; cancel/remove on every toggle entry. Without this,
rapid clicks leave the pill stuck mid-state.

## 9. The two non-negotiable invariants

These have regressed multiple times — read `memory/invariants.md` (per
project) before every iteration:

1. **The logs container is never narrower because of the widget.** Widget
   lives in the page margin (2xl), floats above (lg), or wraps above
   (md/sm). Never as a flex peer that steals horizontal space.
2. **The pill grows INWARD on expand at 2xl** (right edge stays anchored
   in the margin). Don't shift the right edge between states.

---

## How to use this skill

1. **Before any visual edit**, read this file end-to-end.
2. Map the user's complaint to a row in one of the tables above. If the
   live CSS doesn't match the table, the table wins — fix the CSS.
3. If the complaint is about something not covered here, propose the fix
   AND propose an entry to add to this file. Don't add silently.
4. After the fix ships, run the verification-loop skill against
   `memory/invariants.md` — these design standards are the *spec*;
   invariants are the *regressions-prone* subset and need explicit checks.
5. Update `memory/invariants.md` only when the user explicitly relaxes or
   changes a standing expectation. Update this file when the spec itself
   moves.
