import React from 'react';
import {
  AbsoluteFill,
  Series,
  interpolate,
  useCurrentFrame,
  Easing,
} from 'remotion';

/* ── timing ──────────────────────────────────────────────────────────── */
const INTRO = 120;
const SEC = 300;          // per-variant section (5s @ 60fps)
const OUTRO = 100;
export const TOTAL_FRAMES = INTRO + SEC * 3 + OUTRO;

const EXP = 26;           // expand tween length (~430ms — spec is 150ms; slowed for legibility)
const T_EXPAND = 80;      // section-relative frame the expand starts
const T_COLLAPSE = 215;

/* ── tokens (dark mode, from hw-widget-design skill) ─────────────────── */
const C = {
  page: '#030712',        // gray-950
  border: '#1f2937',      // gray-800
  content: '#111827',     // gray-900 (log area)
  label: '#8b949e',
  value: '#d1d5db',       // gray-300 = log body text
  faint: '#6b7280',
  indigo: '#6366f1',
  amber: '#f59e0b',
  track: 'rgba(110,118,129,0.10)',
};

/* ── deterministic mock series ───────────────────────────────────────── */
const N = 40;
const gen = (kind: 'gpu' | 'mem' | 'cpu'): number[] => {
  const a: number[] = [];
  for (let i = 0; i < N; i++) {
    if (kind === 'gpu') a.push(64 + 26 * Math.sin(i * 0.7) + 6 * Math.sin(i * 2.3));
    else if (kind === 'mem') a.push(Math.min(14 + i * 2.6, 86) + 2 * Math.sin(i * 1.7));
    else a.push(36 + 9 * Math.sin(i * 0.5 + 1) + 4 * Math.sin(i * 1.9));
  }
  return a;
};
const SERIES = { gpu: gen('gpu'), mem: gen('mem'), cpu: gen('cpu') };

type MetricDef = {
  key: keyof typeof SERIES;
  label: string;
  tag: string;
  full: string;
  short: string;
  color: string;
  mode: 'avg' | 'peak';
};
const METRICS: MetricDef[] = [
  { key: 'gpu', label: 'GPU', tag: 'AVG', full: '65%', short: '65%', color: C.indigo, mode: 'avg' },
  { key: 'mem', label: 'MEM', tag: 'PEAK', full: '43.1 / 48 GB', short: '90%', color: C.amber, mode: 'peak' },
  { key: 'cpu', label: 'CPU', tag: 'AVG', full: '36%', short: '36%', color: C.indigo, mode: 'avg' },
];

/* ── sparkline ───────────────────────────────────────────────────────── */
const Spark: React.FC<{ m: MetricDef; p: number }> = ({ m, p }) => {
  const s = SERIES[m.key];
  const W = 100, H = 30, PAD = 2;
  const X = (i: number) => (i / (N - 1)) * W;
  const Y = (v: number) => H - PAD - (v / 100) * (H - PAD * 2);
  const pts = s.map((v, i) => `${X(i)},${Y(v)}`).join(' ');
  const area = `M0,${H} L${s.map((v, i) => `${X(i)},${Y(v)}`).join(' L')} L${X(N - 1)},${H} Z`;
  const mean = s.reduce((a, b) => a + b, 0) / s.length;
  const peakV = Math.max(...s);
  const peakI = s.indexOf(peakV);
  return (
    <div
      style={{
        height: 20 * p,
        overflow: 'hidden',
        borderRadius: 6,
        background: C.track,
        opacity: p,
      }}
    >
      <svg
        width="100%"
        height={20}
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="none"
        style={{ display: 'block', transform: `scaleY(${p})`, transformOrigin: '50% 100%' }}
      >
        <path d={area} fill={m.color} opacity={0.14} />
        <polyline points={pts} fill="none" stroke={m.color} strokeWidth={1.5} vectorEffect="non-scaling-stroke" />
        {m.mode === 'avg' ? (
          <line x1={0} y1={Y(mean)} x2={W} y2={Y(mean)} stroke={m.color} strokeWidth={1} opacity={0.55} strokeDasharray="3 2" vectorEffect="non-scaling-stroke" />
        ) : (
          <circle cx={X(peakI)} cy={Y(peakV)} r={2.4} fill={m.color} />
        )}
      </svg>
    </div>
  );
};

/* ── tiny shared atoms ───────────────────────────────────────────────── */
const Dot: React.FC<{ color: string }> = ({ color }) => (
  <span style={{ width: 8, height: 8, borderRadius: 9999, background: color, flexShrink: 0 }} />
);
const labelStyle: React.CSSProperties = {
  fontSize: 12, color: C.label, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '.05em',
};
const valStyle: React.CSSProperties = {
  fontSize: 12, color: C.value, fontWeight: 500, fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap',
};
const Tag: React.FC<{ text: string; p: number }> = ({ text, p }) => (
  <span style={{ maxWidth: 44 * p, overflow: 'hidden', display: 'inline-flex', opacity: p }}>
    <span style={{ fontSize: 10, fontWeight: 600, letterSpacing: '.07em', color: C.label, transform: `translateY(${(1 - p) * 10}px)` }}>
      {text}
    </span>
  </span>
);

/* ── expand progress for a section-relative frame ────────────────────── */
const useProgress = (f: number): number => {
  if (f < T_EXPAND) return 0;
  if (f < T_EXPAND + EXP) {
    return interpolate(f, [T_EXPAND, T_EXPAND + EXP], [0, 1], { easing: Easing.out(Easing.cubic) });
  }
  if (f < T_COLLAPSE) return 1;
  if (f < T_COLLAPSE + EXP) {
    return interpolate(f, [T_COLLAPSE, T_COLLAPSE + EXP], [1, 0], { easing: Easing.in(Easing.cubic) });
  }
  return 0;
};

/* ── replica logs card ───────────────────────────────────────────────── */
const LOG_LINES = [
  '===== Job started at 2026-04-22 04:50:35 =====',
  'Downloading networkx (2.0MiB)',
  'Downloading sympy (6.0MiB)',
  'Downloading triton (148.4MiB)',
  'Fetching 23 files:   0%|          | 0/23',
  'Fetching 23 files:  35%|███▌      | 8/23',
  'Fetching 23 files: 100%|██████████| 23/23',
  'Loading checkpoint shards: 100%|██████████|',
  'Map: 100%|██████████| 1200/1200 [00:04<00:00]',
  '{"loss": 1.82, "lr": 2e-05, "epoch": 0.2}',
  '{"loss": 1.41, "lr": 2e-05, "epoch": 0.4}',
  '{"loss": 1.18, "lr": 1.6e-05, "epoch": 0.6}',
  '{"loss": 0.97, "lr": 1.1e-05, "epoch": 0.8}',
  '{"loss": 0.89, "lr": 5e-06, "epoch": 1.0}',
];
const LogsCard: React.FC<{ children?: React.ReactNode }> = ({ children }) => (
  <div
    style={{
      position: 'relative',
      width: 775, height: 470,
      border: `1px solid ${C.border}`, borderRadius: 8,
      background: C.content, overflow: 'visible',
      fontFamily: 'Segoe UI, system-ui, sans-serif',
    }}
  >
    <div
      style={{
        height: 36, display: 'flex', alignItems: 'center', padding: '0 12px',
        background: C.page, borderBottom: `1px solid ${C.border}`,
        borderTopLeftRadius: 8, borderTopRightRadius: 8,
        fontSize: 13, fontWeight: 600, color: '#e5e7eb',
      }}
    >
      Logs
    </div>
    <div style={{ padding: '10px 16px', fontFamily: 'Consolas, monospace', fontSize: 11, lineHeight: '21px' }}>
      {LOG_LINES.map((l, i) => (
        <div key={i} style={{ whiteSpace: 'pre', overflow: 'hidden' }}>
          <span style={{ color: C.faint }}>4/21, 9:5{i % 10}:12 PM   </span>
          <span style={{ color: C.value }}>{l}</span>
        </div>
      ))}
    </div>
    {children}
  </div>
);

/* ── V4 Corner Panel ─────────────────────────────────────────────────── */
const CornerPanel: React.FC<{ p: number }> = ({ p }) => (
  <div
    style={{
      position: 'absolute', top: 36, right: 0, width: 200,
      background: C.content,
      borderLeft: `1px solid ${C.border}`, borderBottom: `1px solid ${C.border}`,
      borderBottomLeftRadius: 8,
      padding: 10, display: 'flex', flexDirection: 'column', gap: 10 + 5 * p,
    }}
  >
    {METRICS.map((m) => (
      <div key={m.key} style={{ display: 'flex', flexDirection: 'column', gap: 5 * p + 1 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <Dot color={m.color} />
          <span style={labelStyle}>{m.label}</span>
          <span style={{ flex: 1 }} />
          <Tag text={m.tag} p={p} />
          <span style={valStyle}>{m.full}</span>
        </div>
        <Spark m={m} p={p} />
      </div>
    ))}
    {/* grabber handle floating 5px below the open edge */}
    <div style={{ position: 'absolute', left: '50%', bottom: -9, marginLeft: -12, width: 24, height: 4, borderRadius: 9999, background: C.border }} />
  </div>
);

/* ── V5 Floating Card ────────────────────────────────────────────────── */
const FloatingCard: React.FC<{ p: number }> = ({ p }) => (
  <div
    style={{
      position: 'absolute', top: 36 + 5, right: 5,
      width: interpolate(p, [0, 1], [96, 200]),
      background: C.page, border: `1px solid ${C.border}`, borderRadius: 12,
      boxShadow: '0 4px 14px rgba(0,0,0,.35)',
      padding: 10, display: 'flex', flexDirection: 'column', gap: 10 + 5 * p,
    }}
  >
    {METRICS.map((m) => (
      <div key={m.key} style={{ display: 'flex', flexDirection: 'column', gap: 5 * p + 1 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <Dot color={m.color} />
          <span style={labelStyle}>{m.label}</span>
          <span style={{ flex: 1 }} />
          <Tag text={m.tag} p={p} />
          <span style={{ position: 'relative', height: 16, width: interpolate(p, [0, 1], [30, m.key === 'mem' ? 84 : 32]) }}>
            <span style={{ ...valStyle, position: 'absolute', right: 0, opacity: 1 - p }}>{m.short}</span>
            <span style={{ ...valStyle, position: 'absolute', right: 0, opacity: p }}>{m.full}</span>
          </span>
        </div>
        <Spark m={m} p={p} />
      </div>
    ))}
  </div>
);

/* ── V6 Toolbar ──────────────────────────────────────────────────────── */
const Toolbar: React.FC<{ p: number }> = ({ p }) => {
  const fadeOut = interpolate(p, [0, 0.45], [1, 0], { extrapolateRight: 'clamp' });
  const fadeIn = interpolate(p, [0.35, 1], [0, 1], { extrapolateLeft: 'clamp' });
  const W = 348;
  const titleStyle: React.CSSProperties = { fontSize: 12, color: C.label, fontWeight: 400, whiteSpace: 'nowrap' };
  return (
    <div
      style={{
        position: 'absolute', top: 4, right: 12, width: W,
        height: interpolate(p, [0, 1], [28, 192]),
        overflow: 'hidden',
        borderRadius: interpolate(p, [0, 1], [8, 12]),
        background: `rgba(3,7,18,${p})`,
        border: `1px solid rgba(31,41,55,${p})`,
        boxShadow: `0 4px 14px rgba(0,0,0,${0.35 * p})`,
        boxSizing: 'border-box',
      }}
    >
      {/* collapsed layer: toolbar chips */}
      <div
        style={{
          position: 'absolute', inset: 0, display: 'flex', alignItems: 'center',
          gap: 14, padding: '0 12px', opacity: fadeOut,
        }}
      >
        <span style={titleStyle}>Hardware</span>
        {METRICS.map((m) => (
          <span key={m.key} style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
            <Dot color={m.color} />
            <span style={labelStyle}>{m.label}</span>
            <span style={valStyle}>{m.short}</span>
          </span>
        ))}
      </div>
      {/* expanded layer: popover panel */}
      <div
        style={{
          position: 'absolute', inset: 0, padding: 10,
          display: 'flex', flexDirection: 'column', gap: 10, opacity: fadeIn,
        }}
      >
        <span style={titleStyle}>Hardware</span>
        {METRICS.map((m) => (
          <div key={m.key} style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <Dot color={m.color} />
              <span style={labelStyle}>{m.label}</span>
              <span style={{ flex: 1 }} />
              <Tag text={m.tag} p={p} />
              <span style={valStyle}>{m.full}</span>
            </div>
            <Spark m={m} p={p} />
          </div>
        ))}
      </div>
    </div>
  );
};

/* ── one demo section ────────────────────────────────────────────────── */
const Section: React.FC<{
  index: number;
  name: string;
  blurb: string;
  Widget: React.FC<{ p: number }>;
}> = ({ index, name, blurb, Widget }) => {
  const f = useCurrentFrame();
  const p = useProgress(f);
  const inO = interpolate(f, [0, 18], [0, 1], { extrapolateRight: 'clamp' });
  const outO = interpolate(f, [SEC - 16, SEC], [1, 0], { extrapolateLeft: 'clamp' });
  const o = Math.min(inO, outO);
  const slide = interpolate(f, [0, 18], [24, 0], {
    extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic),
  });
  const stateLabel = p > 0.5 ? 'EXPANDED' : 'COLLAPSED';
  return (
    <AbsoluteFill style={{ background: C.page, opacity: o, fontFamily: 'Segoe UI, system-ui, sans-serif' }}>
      {/* left rail: caption */}
      <div style={{ position: 'absolute', left: 110, top: 320, width: 420, transform: `translateY(${slide}px)` }}>
        <div style={{ fontSize: 15, fontWeight: 600, letterSpacing: '.18em', color: C.faint }}>
          0{index} / 03
        </div>
        <div style={{ fontSize: 56, fontWeight: 700, color: '#f9fafb', marginTop: 14, lineHeight: 1.05 }}>
          {name}
        </div>
        <div style={{ fontSize: 21, color: C.label, marginTop: 18, lineHeight: 1.5 }}>{blurb}</div>
        <div
          style={{
            marginTop: 30, display: 'inline-flex', alignItems: 'center', gap: 10,
            fontSize: 13, fontWeight: 600, letterSpacing: '.14em', color: C.faint,
          }}
        >
          <span
            style={{
              width: 8, height: 8, borderRadius: 9999,
              background: p > 0.5 ? C.indigo : C.faint,
            }}
          />
          {stateLabel}
        </div>
      </div>
      {/* stage: replica logs card, scaled up for legibility */}
      <div style={{ position: 'absolute', right: 90, top: 165, transform: 'scale(1.55)', transformOrigin: 'top right' }}>
        <LogsCard>
          <Widget p={p} />
        </LogsCard>
      </div>
    </AbsoluteFill>
  );
};

/* ── intro / outro ───────────────────────────────────────────────────── */
const Intro: React.FC = () => {
  const f = useCurrentFrame();
  const o = Math.min(
    interpolate(f, [0, 20], [0, 1], { extrapolateRight: 'clamp' }),
    interpolate(f, [INTRO - 16, INTRO], [1, 0], { extrapolateLeft: 'clamp' })
  );
  const slide = interpolate(f, [0, 24], [22, 0], { extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic) });
  return (
    <AbsoluteFill
      style={{
        background: C.page, alignItems: 'center', justifyContent: 'center',
        opacity: o, fontFamily: 'Segoe UI, system-ui, sans-serif',
      }}
    >
      <div style={{ textAlign: 'center', transform: `translateY(${slide}px)` }}>
        <div style={{ fontSize: 15, fontWeight: 600, letterSpacing: '.22em', color: C.faint }}>
          HF JOBS · DESIGN EXPLORATION
        </div>
        <div style={{ fontSize: 72, fontWeight: 700, color: '#f9fafb', marginTop: 22 }}>
          Hardware Utilization Widget
        </div>
        <div style={{ fontSize: 24, color: C.label, marginTop: 18 }}>
          Three directions · nested in the logs container
        </div>
      </div>
    </AbsoluteFill>
  );
};

const Outro: React.FC = () => {
  const f = useCurrentFrame();
  const o = interpolate(f, [0, 20], [0, 1], { extrapolateRight: 'clamp' });
  return (
    <AbsoluteFill
      style={{
        background: C.page, alignItems: 'center', justifyContent: 'center',
        opacity: o, fontFamily: 'Segoe UI, system-ui, sans-serif',
      }}
    >
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 40, fontWeight: 700, color: '#f9fafb' }}>Try it live</div>
        <div style={{ fontSize: 23, color: C.indigo, marginTop: 16 }}>
          chuntelee.github.io/jobs-hardware-widget
        </div>
      </div>
    </AbsoluteFill>
  );
};

/* ── root ────────────────────────────────────────────────────────────── */
export const Demo: React.FC = () => (
  <AbsoluteFill style={{ background: C.page }}>
    <Series>
      <Series.Sequence durationInFrames={INTRO}>
        <Intro />
      </Series.Sequence>
      <Series.Sequence durationInFrames={SEC}>
        <Section index={1} name="Corner Panel" blurb="Carved into the logs card itself — borrows the card's borders, adds zero chrome." Widget={CornerPanel} />
      </Series.Sequence>
      <Series.Sequence durationInFrames={SEC}>
        <Section index={2} name="Floating Card" blurb="Docked at the logs' right edge — glance percentages, full detail on click." Widget={FloatingCard} />
      </Series.Sequence>
      <Series.Sequence durationInFrames={SEC}>
        <Section index={3} name="Toolbar" blurb="Lives in the logs header as quiet text — chrome appears only when opened." Widget={Toolbar} />
      </Series.Sequence>
      <Series.Sequence durationInFrames={OUTRO}>
        <Outro />
      </Series.Sequence>
    </Series>
  </AbsoluteFill>
);
