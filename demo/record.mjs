/**
 * Records a REAL interaction demo of the prototype: drives the actual
 * job-detail-prototype.html in Chrome with genuine mouse events (so the
 * real hover states + GSAP animations fire), an injected visible cursor,
 * and captures 1920x1080 @ 60fps straight to MP4. No intro, no outro.
 *
 * Run: node record.mjs   (from demo/)
 */
import puppeteer from 'puppeteer-core';
import { PuppeteerScreenRecorder } from 'puppeteer-screen-recorder';
import ffmpegPath from 'ffmpeg-static';
import { spawn } from 'node:child_process';
import http from 'node:http';

const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const URL = 'http://localhost:3456/job-detail-prototype.html';
const OUT = '../widget-demo.mp4';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const easeInOutCubic = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

/* ── ensure the local server is up ───────────────────────────────────── */
const serverAlive = () =>
  new Promise((res) => {
    const req = http.get(URL, (r) => { r.resume(); res(true); });
    req.on('error', () => res(false));
    req.setTimeout(1500, () => { req.destroy(); res(false); });
  });

let serverProc = null;
if (!(await serverAlive())) {
  serverProc = spawn('python', ['-m', 'http.server', '3456'], {
    cwd: 'C:/HuggingFace/Job Gauges',
    stdio: 'ignore',
  });
  for (let i = 0; i < 20 && !(await serverAlive()); i++) await sleep(250);
}

/* ── browser ─────────────────────────────────────────────────────────── */
const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: true,
  args: ['--window-size=1936,1180', '--hide-scrollbars', '--force-device-scale-factor=1'],
});
const page = await browser.newPage();
await page.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 1 });
await page.goto(URL, { waitUntil: 'networkidle2', timeout: 60000 });
await page.waitForSelector('#hw-v4-pill', { timeout: 30000 });
await sleep(1200); // fonts, gsap, initial attach settle

/* ── inject a visible cursor + click ripple ──────────────────────────── */
await page.evaluate(() => {
  const cur = document.createElement('div');
  cur.id = 'demo-cursor';
  cur.style.cssText =
    'position:fixed;left:0;top:0;z-index:2147483647;pointer-events:none;width:22px;height:30px;';
  cur.innerHTML =
    '<svg width="22" height="30" viewBox="0 0 22 30" xmlns="http://www.w3.org/2000/svg">' +
    '<path d="M2 1 L2 23 L7.5 18 L11 27 L14.6 25.4 L11.2 16.8 L19 16.4 Z" ' +
    'fill="#fff" stroke="#111" stroke-width="1.4" stroke-linejoin="round"/></svg>' +
    '<div style="position:absolute;left:1px;top:1px;filter:blur(3px);opacity:.35;z-index:-1">' +
    '<svg width="22" height="30" viewBox="0 0 22 30"><path d="M2 1 L2 23 L7.5 18 L11 27 L14.6 25.4 L11.2 16.8 L19 16.4 Z" fill="#000"/></svg></div>';
  document.body.appendChild(cur);
  window.__setCursor = (x, y) => {
    cur.style.transform = `translate(${x}px, ${y}px)`;
  };
  window.__ripple = (x, y) => {
    const r = document.createElement('div');
    r.style.cssText =
      `position:fixed;left:${x - 14}px;top:${y - 14}px;width:28px;height:28px;` +
      'border:2.5px solid rgba(99,102,241,.9);border-radius:9999px;z-index:2147483646;' +
      'pointer-events:none;animation:demoPing .45s ease-out forwards;';
    document.body.appendChild(r);
    setTimeout(() => r.remove(), 500);
  };
  const st = document.createElement('style');
  st.textContent =
    '@keyframes demoPing{0%{transform:scale(.45);opacity:.95}100%{transform:scale(1.7);opacity:0}}' +
    '*{cursor:none !important}';
  document.head.appendChild(st);
});

let cx = 960, cy = 760; // cursor state, starts mid-page below the card
await page.evaluate(([x, y]) => window.__setCursor(x, y), [cx, cy]);
await page.mouse.move(cx, cy);

/* ── primitives ──────────────────────────────────────────────────────── */
const moveTo = async (x, y, ms = 700) => {
  const x0 = cx, y0 = cy;
  const frames = Math.max(2, Math.round(ms / 16));
  for (let i = 1; i <= frames; i++) {
    const t = easeInOutCubic(i / frames);
    const nx = x0 + (x - x0) * t;
    const ny = y0 + (y - y0) * t;
    await page.mouse.move(nx, ny);
    await page.evaluate(([a, b]) => window.__setCursor(a, b), [nx, ny]);
    await sleep(16);
  }
  cx = x; cy = y;
};
const click = async () => {
  await page.evaluate(([a, b]) => window.__ripple(a, b), [cx, cy]);
  await page.mouse.down();
  await sleep(70);
  await page.mouse.up();
};
const rectOf = async (sel) =>
  page.evaluate((s) => {
    const el = document.querySelector(s);
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return { x: r.left, y: r.top, w: r.width, h: r.height, cx: r.left + r.width / 2, cy: r.top + r.height / 2 };
  }, sel);

/* ── record ──────────────────────────────────────────────────────────── */
const recorder = new PuppeteerScreenRecorder(page, {
  fps: 60,
  videoFrame: { width: 1920, height: 1080 },
  videoCrf: 17,
  videoCodec: 'libx264',
  videoPreset: 'slow',
  videoPixelFormat: 'yuv420p',
  ffmpeg_Path: ffmpegPath,
  aspectRatio: '16:9',
});
await recorder.start(OUT);
await sleep(600);

/* one variant's beat: approach → hover dwell → click → expanded dwell →
   click → settle */
const playVariant = async (pillSel) => {
  const pill = await rectOf(pillSel);
  await moveTo(pill.cx, pill.cy, 850);
  await sleep(900);                 // hover state visible (bend / ring / tint)
  await click();                    // expand (real GSAP, 150ms)
  await sleep(500);
  const exp = await rectOf(pillSel);     // panel grew — follow it
  await moveTo(exp.x + exp.w / 2, exp.y + exp.h - 26, 650);  // glide over the panel
  await sleep(1100);
  await click();                    // collapse
  await sleep(800);
};

/* 01 Corner Panel (default on load) */
await playVariant('#hw-v4-pill');

/* 02 Floating Card — switch via the real control */
let btn = await rectOf('#hw-ver-v5');
await moveTo(btn.cx, btn.cy, 800);
await click();
await sleep(450);
await playVariant('#hw-v5-pill');

/* 03 Toolbar */
btn = await rectOf('#hw-ver-v6');
await moveTo(btn.cx, btn.cy, 800);
await click();
await sleep(450);
await playVariant('#hw-v6-pill');

await sleep(500);
await recorder.stop();
await browser.close();
if (serverProc) serverProc.kill();
console.log('done ->', OUT);
