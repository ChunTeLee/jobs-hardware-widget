# Jobs hardware-utilization widget — prototype

Interactive design prototype for a GPU/CPU usage widget on the Hugging Face
Jobs detail page (issue `huggingface-internal/moon-landing#17285`).
Live: https://chuntelee.github.io/jobs-hardware-widget/

## Start here

**Read `HANDOFF.md` before doing anything** — it has full project state,
architecture, current commit, open items, and the build/deploy workflow.
The `handoff/` folder has the project's design decisions and the
verification-loop skill.

## Non-negotiable working rules

- **Edit `build.py`, never `job-detail-prototype.html`** — the HTML is
  generated. Run `python build.py` to regenerate.
- **Run the verification loop every iteration.** Before declaring any
  change done, walk through every entry in `handoff/invariants.md` and run
  its check — not just the thing you changed. This project has a history
  of new fixes silently breaking previously-fixed things (smooth animation,
  the 12px gap). Install the skill: `handoff/verification-loop-SKILL.md`.
- **Keep the scrub step in `build.py`** — the repo is public; private job
  data must stay redacted.
- After a change: `python build.py` → commit → `git push origin main` →
  wait for GitHub Pages to rebuild → hard-refresh the live URL to verify.

## Collaboration style (the user is a HF product designer)

- Lead design reasoning from the **problem / user job-to-be-done**.
- **Argue back** when their reasoning is weak — steelman both sides.
- Prefer **minimal, self-explanatory** UI; replace elements rather than add.

See `handoff/project-memory.md` for the full settled-decisions list — don't
relitigate those without new information.
