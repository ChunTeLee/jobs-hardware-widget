# HANDOFF — Jobs hardware-utilization widget prototype

> Read this first when picking the project up on a new device. It is the
> single source of truth for project state, architecture, decisions, and
> what to do next.

## What this project is

An interactive **design prototype** for a GPU/CPU usage widget on the
Hugging Face Jobs detail page (GitHub issue
`huggingface-internal/moon-landing#17285`). It is a static replica of the
real HF Jobs page (`huggingface.co/jobs/Chunte/69e85341cd8c002f31e0166c`)
with an injected hardware-utilization widget in three layout variants the
user is comparing.

- **Live preview:** https://chuntelee.github.io/jobs-hardware-widget/
- **Repo:** https://github.com/ChunTeLee/jobs-hardware-widget (public)
- **Owner:** ChunTeLee (product designer at Hugging Face)

## Current state (as of this handoff)

- Latest deployed commit: see `git log -1` — was `9e49253` at handoff time.
- All three widget versions work; V3 is the one under active iteration.
- The build pipeline (`build.py`) is now **portable** — paths are relative
  to the script, and a scrubbed `page-main.html` is committed, so
  `python build.py` works immediately after a clone.

### Open / unverified items

Two invariants could not be machine-verified at handoff because the test
browser tab was hidden (Chrome throttles rAF + CSS transitions on hidden
tabs). **Verify these visually on the live site first thing:**

1. **V3 expand/collapse animation is smooth** — toggle the V3 pill, the
   width+height should animate over ~300ms, not snap.
2. **12px gap between V3 pill and logs stays 12px after toggle cycles** —
   on a ≥1536px viewport, expand then collapse the pill a few times; the
   gap to the logs container must remain 12px (a fix for drift shipped in
   commit `9e49253` but needs a real visual confirmation).

## New-device setup

```bash
# 1. Clone
git clone https://github.com/ChunTeLee/jobs-hardware-widget.git
cd jobs-hardware-widget

# 2. Rebuild (portable — no external files needed)
python build.py
#   reads:  page-main.html (scrubbed DOM, committed) + style.css
#   writes: job-detail-prototype.html

# 3. Preview locally
python -m http.server 3456
#   open http://localhost:3456/job-detail-prototype.html

# 4. Deploy: commit + push to main; GitHub Pages rebuilds in ~1-2 min
git add job-detail-prototype.html build.py
git commit -m "..."
git push origin main
```

### Install the skills + memory (so the new Claude session has context)

The `handoff/` folder contains the project's Claude context. On the new
device, copy these into the Claude config dir (`~/.claude/`):

- `handoff/verification-loop-SKILL.md`
  → `~/.claude/skills/verification-loop/SKILL.md`
- `handoff/invariants.md`
  → the project's `memory/invariants.md`
- `handoff/project-memory.md`
  → the project's `memory/` (design decisions + collaboration style)

Or simply tell the new Claude session: "Read HANDOFF.md and the `handoff/`
folder to get up to speed."

## Architecture

### Files in the repo

| File | Role |
|---|---|
| `build.py` | The build pipeline. Edit this, not the HTML output. |
| `page-main.html` | Scrubbed rendered DOM of the real HF Jobs page (the replica source). |
| `style.css` | Mirrored compiled CSS from HF, with absolutized `url()`s. |
| `job-detail-prototype.html` | **Generated** output. Don't hand-edit. |
| `index.html` | Redirect to `job-detail-prototype.html` for the bare Pages URL. |
| `HANDOFF.md` / `handoff/` | This handoff package. |

### How `build.py` works

1. Reads the rendered DOM (`page-main.html`).
2. Strips SvelteKit comment markers.
3. Absolutizes `src`/`href` so assets resolve from `huggingface.co`.
4. **Scrubs private data** (Svelte `data-props` payload, env-var script,
   token ID, avatars) — keep this step; the repo is public.
5. Tags the logs card and wraps it in `#hw-v3-layout` (a flex container
   so the V3 pill can be a layout sibling).
6. Builds the three widget versions + the prototype control panel, and
   splices them in before the logs section.
7. Mirrors the page's root shell (`<html>`/`<body>` classes) so page
   background + dark mode resolve correctly.
8. Writes `job-detail-prototype.html`.

### The three widget versions (prototype `WIDGET VERSION` toggle)

- **V1 — Bar row:** inline row above logs, flat billing-style bar gauges.
- **V2 — Trend row:** inline row above logs, time-series sparklines.
- **V3 — Pill:** responsive widget anchored to the logs container — the
  one under active iteration.

### V3 responsive behavior (Tailwind breakpoints)

| Viewport | Collapsed | Expanded |
|---|---|---|
| mobile <768 | full-width row above logs | full-width, grows down (overlay) |
| laptop 768–1535 | horizontal row above logs, right-aligned | full-width, grows down (overlay) |
| 4K-class ≥1536 | vertical pill floating in the right page margin, 12px from logs | grows leftward over logs; right edge anchored (no shift) |

V3 expand/collapse uses a **FLIP animation** (`hwToggleV3`): measure start
size → apply state → measure end size → lock to start → `requestAnimation
Frame` → set end → CSS transition runs → on `transitionend`, lock width to
an explicit px (NOT `max-content`, which drifts) and clear height.

### Prototype controls

Bottom-right floating panel: a `WIDGET VERSION` segmented control (V1/V2/V3)
and a `JOB STATE` toggle (Running / Completed / Error / Cancelled). The
state toggle also drives the replicated header Status cell.

## Working method (IMPORTANT)

Use the **`verification-loop` skill** every iteration. Before declaring any
change done, walk through every entry in `memory/invariants.md` and run its
check — not just the thing you changed. This project has a history of each
new fix silently breaking a previously-fixed thing (smooth animation got
removed ~3×, the 12px gap drifted). The ledger exists to stop that.

The user is a product designer. They want:
- Design reasoning that starts from the **problem / user job-to-be-done**.
- To be **argued with** when their reasoning is weak — steelman both sides.
- **Minimal, self-explanatory** UI — replace elements rather than add.

See `handoff/project-memory.md` for the full settled-decisions list.

## Deploy verification

After `git push origin main`, GitHub Pages rebuilds. Poll:

```bash
gh api repos/ChunTeLee/jobs-hardware-widget/pages/builds/latest
```

Wait for `status: built` with the new commit hash, then hard-refresh the
live URL (append `?v=N` to bypass cache) and verify.
