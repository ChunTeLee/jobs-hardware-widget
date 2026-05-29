---
name: verification-loop
description: >
  Catch silent regressions against the user's standing invariants. Use this
  whenever you're about to declare a multi-step or iterative task complete —
  especially during UI/UX work where each new fix risks breaking something
  the user already accepted. The loop reads `memory/invariants.md` (a
  per-project ledger of user-stated expectations), runs the verification
  check for every entry, and reports drift BEFORE you ship. New invariants
  get added the moment the user states one; existing ones get updated when
  the user explicitly relaxes or changes them — never silently. Trigger
  this whenever the user has had to repeat themselves, when a "polish"
  edit touches structure, or when iteration has produced two-step-forward-
  one-step-back churn.
---

# Verification Loop — guarding against silent regression

## Why this exists

In iterative work, every fix to a new issue can silently break a previously-
fixed one. The agent's tunnel vision on the current request causes regressions
to ship unnoticed. The user then has to re-report the same problem — wasting
their attention and eroding trust.

This is most acute in UI/UX work where:
- A new visual fix touches CSS that another fix depended on
- Animation gets accidentally rid of when adding/removing explicit dimensions
- Layout invariants (gaps, widths, alignment) drift as related styles change
- Visual changes aren't caught by tests, lints, or compilation

The cure: **maintain an explicit ledger of user-stated invariants and run
through it before declaring done.**

## Two-Part System

### Part 1 — `memory/invariants.md` (the per-project ledger)

A plain-markdown file listing every standing user expectation. Each entry:

```
### <one-line name of the invariant>

- **What:** <the user-facing property that must hold, stated as a check>
- **Why:** <which user request established this>
- **Established:** <commit hash / date>
- **How to verify:**
  - <concrete check — JS query, computed-style, screenshot region, manual eye>
- **Common ways it breaks:**
  - <regression vectors you've actually seen, so future-you knows where to look>
```

Keep entries focused on **durable, user-facing properties**. Don't bloat
the ledger with implementation choices the user didn't insist on.

### Part 2 — The verification pass

Before declaring a task complete / pushing / closing the turn, walk through
EVERY entry in `invariants.md`:

1. Read its "How to verify" step.
2. Execute it (JS query in browser, screenshot diff, computed-style read, etc.).
3. Note **PASS / FAIL / UNCHECKED** for each.
4. **If any FAIL:** fix it before proceeding. Don't ship the regression.
5. **If UNCHECKED:** state that explicitly to the user — don't pretend.

The single most important rule: **don't shortcut by reasoning "the change I
made shouldn't have touched that."** That's the exact assumption that ships
regressions. Run the check.

## When to add a new invariant

- User says "this should always..." / "never..." / "don't touch X"
- User has had to repeat the same correction (clear signal: this matters
  to them, you've already missed it once)
- A subtle visual property the user confirmed (color, spacing, animation
  smoothness, font) that's at risk from any future structural edit
- The user pushed back on a tradeoff and you chose a side — record the
  choice so it doesn't quietly flip back later

## When to update or retire an invariant

- The user explicitly changes the constraint → update the "What" line,
  note the change with a new date
- The invariant becomes irrelevant (e.g., the component was removed) →
  delete with a one-line note about why, in the commit message
- **Never silently retire an invariant** by just removing the check. If
  you stop checking, surface that decision to the user.

## Verification techniques by class

### Animation / transition smoothness

JS measurement is unreliable in two ways:
- **Hidden tabs throttle rAF and transitions** — `document.visibilityState`
  must be `"visible"` for animation timing to be honest. If you're testing
  via a browser MCP and the tab isn't focused, all your samples will show
  the start or end values frozen.
- **Synchronous JS reads of `offsetWidth/Height` during a transition return
  the *current animated value*** — taking one sample tells you nothing about
  whether the property is animating. You need multiple samples across time
  to see whether values are interpolating.

Reliable checks:
- Take screenshots at ~50ms intervals through the transition window and
  diff them, or visually confirm intermediate frames.
- Or: ask the user to verify (acknowledge you can't reliably measure).
- If you must JS-measure: ensure tab is visible, sample at >= 3 points
  during the expected transition window, look for monotonic change.

### Layout / spacing

- Use `getBoundingClientRect()` to measure gaps between elements:
  `nextElement.top - prevElement.bottom`.
- Take screenshots in collapsed AND expanded states; compare to last known
  good screenshot.
- Read `getComputedStyle(el).gap / margin / padding` of containers.

**Always check BOTH axes when checking element-to-element alignment.**
A single-axis assertion like "dot is 5px right of title" passes even
when the dot is floating above the title baseline. The class of bug
that hides under one-axis checks:

- Parent flex container uses `align-items: flex-start` (e.g. to anchor
  one element during animation) → small siblings top-align to the
  taller sibling's line-box top, ~half their height-difference above
  the visual center.
- Parent uses `align-items: baseline` but one child has no text baseline
  (icon-only spans default to bottom-edge baseline) → icon hangs below
  text.

Canonical 2D check pattern for "X sits 5px right of Y, vertically
centered with Y":

```js
var dr = X.getBoundingClientRect(), tr = Y.getBoundingClientRect();
var x_gap = Math.round(dr.left - tr.right);                          // expected horizontal
var y_offset = Math.round((dr.top+dr.bottom)/2 - (tr.top+tr.bottom)/2); // 0±2
// assert x_gap === expected && Math.abs(y_offset) <= 2
```

Apply this whenever an invariant says "next to" / "beside" / "X px from
Y" — not just "X px gap" — and run it in every state (collapsed,
expanded, hovered, focused) where both elements are visible.

**Heuristic when adding a "next to" invariant:** if the verifier reads
only one axis, it's incomplete. Add the orthogonal axis assertion or
the bug will ship.

### Colors / typography

- `getComputedStyle(el).color / backgroundColor / borderColor / fontSize /
  fontWeight / textTransform / letterSpacing` against captured baseline.
- Compare two elements: "X must match Y's style" — read both and assert.

### Existence / structure

- `document.querySelector(...) !== null`
- For "must not exist": `=== null`

## Workflow

```
At task start (multi-step or iterative work):
  - Read memory/invariants.md (create if missing).
  - Note which ones are at risk given the planned change.

During work:
  - Whenever the user states a standing expectation: add/update an entry.
  - Whenever you find yourself thinking "this seems important but I might
    forget": add an entry.

Before "declaring done" / committing:
  1. Re-read invariants.md.
  2. For each entry, run the check.
  3. Report PASS / FAIL / UNCHECKED inline.
  4. If FAIL: fix and re-verify. If you can't, flag it.
  5. Commit invariants.md alongside code if it changed.

In end-of-turn summary:
  - Either: "All N invariants PASS." (concise, default)
  - Or: list failures / uncheckables explicitly.

When the user reports a regression:
  1. Add it as an invariant if not already present.
  2. Fix it.
  3. Strengthen its verification check so the next round catches it.
```

## What this skill is NOT

- A full test suite. Invariants are user-stated expectations, not all the
  things that should be true.
- A replacement for asking clarifying questions. If a planned change might
  break an invariant, ask first — don't just hope the loop catches it.
- A guarantee. Browser quirks (hidden tabs not animating), environment
  noise, and stale checks will let things through. Stay alert.

## Common regression patterns to know about

Documented from real iteration history — these are the moves most likely
to silently break invariants:

| You're changing... | At risk of breaking... |
|---|---|
| Removing explicit `height: 280px` to fix "empty space at bottom" | Smooth height animation (height transitions don't run on `auto`) |
| Adding `interpolate-size` to enable `auto` animation | Other inline-px transitions you control via FLIP (fights your values) |
| Replacing fixed `width: 148px` with `width: max-content` | Gap calculations that assumed the fixed width — left edge moves |
| Switching `<span>` to `<p>` for "matches page header style" | Vertical spacing if default `<p>` margin isn't reset |
| Changing one element's `border`/`bg` to "match the page" | Other elements that previously inherited from this one |
| Adding `overflow: hidden` to clip a transition | Other content that needs to overflow (tooltips, focus rings) |
| Refactoring CSS to use Tailwind classes instead of inline rules | Specificity changes — inline-style edits stop working |

## File location

- This SKILL.md lives at `~/.claude/skills/verification-loop/SKILL.md`
  and is project-agnostic.
- The per-project ledger lives at `<project-memory>/invariants.md`,
  i.e. wherever the project's memory directory is. Add a one-line pointer
  in `MEMORY.md` so future sessions find it.
