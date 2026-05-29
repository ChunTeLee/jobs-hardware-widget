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
| **md 768–1023**             | 420px row above logs, right-aligned                    | Same anchor, grows down                                                                           |
| **lg 1024–1535**            | Horizontal row floating with inline `top:-(h+10)` so the pill's top intrudes into the page-header band's row-2 dead space; right edge flush with logs.right; 10px visible gap to logs | **Same top, same width** — only height grows. Pill grows downward, overlaying logs top. NEVER drops to logs.top, NEVER shrinks horizontally. |
| **2xl ≥1536** (4K-class)    | Vertical pill floating in the right page margin, 10px past logs.right; width = max-content captured by `lockLgAnchor()`; right edge `-(W+10)` | Right edge stays in margin (`right:-(W+10)`); width grows from W → 340px, pulling LEFT edge into logs — overlay without right-edge shift |

**lg-specific don'ts:**
- Don't reparent the pill into `#hw-meta-band` (the page-header band).
  That was tried and rejected — the pill should not be coded inside the
  header group.
- Don't add a spacer (`.hw-v3-spacer { display:none }` on lg) — logs sit
  at their natural position; the pill floats over the band/logs boundary.
- Don't reset `top:0` on expand. Lock `top: -(collapsedH + 10)` across
  BOTH states; only height animates.

**Key JS hooks:**
- `lockLgAnchor(pill)` — 2xl only; sets inline `right:-(W+10)` and
  `width:W` so the pill floats in the right margin and width is a length
  (transitions need length→length).
- `lockLgFloat(pill)` — lg only; sets inline `top:-(h+10)` so the pill's
  top intrudes upward into the header band.
- `pill.dataset.collapsedW` / `collapsedH` — captured on first attach;
  the FLIP animation reuses them so collapsed/expanded share an anchor.

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
