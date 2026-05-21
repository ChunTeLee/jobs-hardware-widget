# Project memory — design decisions & collaboration style

> Copy this into the project's Claude `memory/` directory on the new device.
> It captures how the user works and the decisions already settled, so they
> are not relitigated.

## Who / what

The user is a product designer at Hugging Face (the "Chunte" account whose
Jobs page is the subject). Working on the Jobs hardware-utilization gauge
widget — GitHub issue `huggingface-internal/moon-landing#17285`.

## Collaboration style

- Wants design reasoning to start from a **problem / user job-to-be-done**,
  not from the feature.
- Explicitly asks to be **argued with** when their reasoning is weak. Push
  back with specifics, steelman both sides, then synthesize — don't just
  agree.
- Prefers **minimal, self-explanatory** UI indicators: a muted micro-tag
  over a legend/tooltip/icon. When adding a visual, prefer *replacing* an
  element over *adding* one (same footprint, more meaning).
- **How to apply:** for any design proposal, lead with the problem, give a
  recommendation + the main tradeoff, expect and welcome counter-argument.

## Settled design decisions (do not relitigate without new info)

- **Job states:** Real HF Jobs `status.stage` values (verified in
  huggingface_hub docs) are RUNNING, COMPLETED, ERROR, CANCELED
  ("Cancelled" in UI). There is **NO "Queued" stage** — it was an invented
  mock state and was removed. Prototype states: Running / Completed /
  Error / Cancelled. Cancelled = partial run, neutral grey, no red (the
  user stopped it; nothing went wrong).
- **No status echo:** sub-components must NOT echo the job's lifecycle
  status — the page header owns Status. Widgets show *what their numbers
  mean*, not *what state the job is in*. (The prototype's job-state toggle
  does drive the replicated header Status cell, so the preview stays
  coherent.)
- **Per-metric aggregation:** GPU/CPU **Utilisation → AVG** (peak util is
  meaningless, ~100% always); GPU **Memory → PEAK** (near-OOM is the
  actionable signal). Shown as a 3-letter uppercase muted tag (`AVG`/
  `PEAK`) prefixing the value.
- **Sparkline replaces the flat bar** (not in addition). Failed runs: the
  sparkline stops at the cliff — the empty tail is the crash signal, no
  explanatory text. Running: live instantaneous value, no agg tag, "Live"
  badge.
- **Three layout variants** behind a prototype toggle:
  - V1 = inline row + flat bar gauge
  - V2 = inline row + time-series sparkline (the "trend" row reviewers liked)
  - V3 = responsive pill anchored to the logs container (under active
    iteration)
- **Per-metric colour, NOT a shared traffic-light.** Colour escalates only
  toward a condition the user should ACT on:
  - GPU **Memory** = OOM ceiling scale (indigo <80% → amber 80–94% → red
    ≥95%, forced red on Failed)
  - GPU **Utilisation** = inverted (high is the goal; flag LOW average —
    amber <40%, red <15% = wasted spend; running stays neutral)
  - CPU = always neutral (relational tell, never alarmed)
  - Default neutral is HF indigo, never green (green would moralise normal
    load).
- **RAM (CPU memory)** deliberately excluded from v1 (the issue scoped
  GPU+CPU; 3 metrics stays scannable) — but it is the top v2 candidate:
  host-RAM OOM is the one failure mode the current widget cannot explain.
- **Public preview:** GitHub repo `ChunTeLee/jobs-hardware-widget`, live at
  https://chuntelee.github.io/jobs-hardware-widget/ . `build.py` scrubs
  private job data (Svelte `data-props` payload, env-var script, token ID,
  avatars) before publishing — keep that step.

## Process

Use the **verification-loop skill** every iteration (see
`verification-loop-SKILL.md`). Before declaring any change done, walk
through every entry in `invariants.md` and run its check. This project has
a documented history of each new fix silently breaking a previously-fixed
thing — the invariant ledger exists to stop that.
