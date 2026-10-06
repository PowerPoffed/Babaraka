// Моушн-дизайн по плану: node render.js <motion_plan.json> [субтитры.srt]
// 1) Рендерит каждый элемент плана в видео с прозрачным фоном: out/<ролик>/shot_008_map.mov
// 2) Если рядом с планом лежат субтитры .srt (из CapCut) и shotpos.json — считает, когда начинается
//    каждый кадр, и собирает ОДНУ дорожку на весь ролик: ALL_overlays.mov (кладётся поверх ролика с 0:00).
const { chromium } = require('playwright');
const fs = require('fs'); const path = require('path'); const { execFileSync } = require('child_process');
const FPS = 30;
const DUR = { title: 3.5, map: 4.5, source: 3.0, name: 3.0, number: 3.0, compare: 4.0, timeline: 3.5, myth: 4.0,
  quote: 3.0, checklist: 4.5, alert: 3.0, label: 3.0 };
// где на экране стоит элемент — чтобы два элемента в одном месте не наложились
const ZONE = { title: 'center', map: 'center', myth: 'center', quote: 'center', label: 'center', source: 'topleft', name: 'topleft',
  checklist: 'topleft', number: 'topright', alert: 'topright', compare: 'topright', timeline: 'top' };
const clash = (a, b) => a === b || (a === 'top' && b.startsWith('top')) || (b === 'top' && a.startsWith('top'));

const planPath = path.resolve(process.argv[2] || path.join(__dirname, 'motion_plan.json'));
const planDir = path.dirname(planPath);
const plan = JSON.parse(fs.readFileSync(planPath, 'utf8'));
const outDir = path.join(__dirname, 'out', path.basename(planDir)); fs.mkdirSync(outDir, { recursive: true });
const ffmpeg = (args) => execFileSync('ffmpeg', ['-v', 'error', '-y', ...args], { stdio: ['ignore', 'inherit', 'inherit'] });
const fileOf = (it) => `${it.shot}_${it.type}.mov`;

// уже готовый файл перерисовывается, только если в плане поменяли его текст/длительность
const metaPath = path.join(outDir, '.meta.json');
const meta = fs.existsSync(metaPath) ? JSON.parse(fs.readFileSync(metaPath, 'utf8')) : {};
async function renderAll() {
  let browser;
  if (process.env.CHROME_PATH) browser = await chromium.launch({ executablePath: process.env.CHROME_PATH });
  else { try { browser = await chromium.launch({ channel: 'msedge' }); } catch (e) { browser = await chromium.launch(); } }
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  await page.goto('file://' + path.resolve(__dirname, 'anim.html'));
  await page.evaluate(() => document.fonts.ready);
  const frames = path.join(__dirname, 'frames_tmp');
  for (const [i, it] of plan.items.entries()) {
    const out = path.join(outDir, fileOf(it));
    const dur = it.dur || DUR[it.type], key = JSON.stringify({ ...it, dur });
    if (fs.existsSync(out) && meta[fileOf(it)] === key) { console.log(`[${i + 1}/${plan.items.length}] уже есть: ${fileOf(it)}`); continue; }
    fs.rmSync(frames, { recursive: true, force: true }); fs.mkdirSync(frames);
    await page.evaluate(([type, d]) => window.setup(type, d), [it.type, it]);
    const n = Math.round(dur * FPS);
    for (let f = 0; f < n; f++) {
      await page.evaluate(([type, t, d]) => window.draw(type, t, d), [it.type, f / FPS, dur]);
      await page.screenshot({ path: path.join(frames, `f_${String(f).padStart(4, '0')}.png`), omitBackground: true });
    }
    ffmpeg(['-framerate', String(FPS), '-i', path.join(frames, 'f_%04d.png'),
      '-c:v', 'prores_ks', '-profile:v', '4444', '-qscale:v', '11', '-pix_fmt', 'yuva444p10le', out]);
    meta[fileOf(it)] = key; fs.writeFileSync(metaPath, JSON.stringify(meta, null, 1));
    console.log(`[${i + 1}/${plan.items.length}] готово: ${fileOf(it)}`);
  }
  fs.rmSync(frames, { recursive: true, force: true });
  await browser.close();
}

// ---------- время начала кадров по субтитрам ----------
const norm = (w) => w.toLowerCase().replace(/[^a-z0-9]/g, '');
function srtWords(srt) {
  const ts = (s) => { const [h, m, r] = s.trim().replace(',', '.').split(':'); return +h * 3600 + +m * 60 + +r; };
  const words = [];
  for (const block of srt.replace(/\r/g, '').split(/\n\s*\n/)) {
    const lines = block.trim().split('\n'); const ti = lines.findIndex((l) => l.includes('-->'));
    if (ti < 0) continue;
    const [a, b] = lines[ti].split('-->').map(ts);
    const ws = lines.slice(ti + 1).join(' ').split(/\s+/).map(norm).filter(Boolean);
    const total = ws.reduce((s, w) => s + w.length + 1, 0); let acc = 0;
    for (const w of ws) { words.push({ w, t: a + (b - a) * acc / total }); acc += w.length + 1; }   // слово внутри строки — по доле букв
  }
  return words;
}
function alignTimes(W, S) {   // сопоставление текста ролика (W) со словами субтитров (S); возвращает время для каждого слова W
  const n = W.length, m = S.length, cols = m + 1;
  const dp = new Int32Array((n + 1) * cols);
  for (let i = 1; i <= n; i++) for (let j = 1; j <= m; j++)
    dp[i * cols + j] = W[i - 1] === S[j - 1].w ? dp[(i - 1) * cols + j - 1] + 1 : Math.max(dp[(i - 1) * cols + j], dp[i * cols + j - 1]);
  const t = new Array(n).fill(null);
  for (let i = n, j = m; i > 0 && j > 0;) {
    if (W[i - 1] === S[j - 1].w) { t[i - 1] = S[j - 1].t; i--; j--; }
    else if (dp[(i - 1) * cols + j] >= dp[i * cols + j - 1]) i--; else j--;
  }
  // пропущенные слова (цифры/ошибки распознавания) — интерполяция между соседями
  let prev = -1;
  for (let i = 0; i <= n; i++) if (i === n || t[i] !== null) {
    for (let k = prev + 1; k < i; k++) {
      const a = prev >= 0 ? t[prev] : 0, b = i < n ? t[i] : (S.length ? S[S.length - 1].t : a);
      t[k] = a + (b - a) * (k - prev) / (i - prev);
    }
    prev = i;
  }
  return t;
}
function shotStarts(srtPath) {
  const sp = JSON.parse(fs.readFileSync(path.join(planDir, 'shotpos.json'), 'utf8'));
  const W = sp.W.map(norm); const times = alignTimes(W, srtWords(fs.readFileSync(srtPath, 'utf8')));
  const start = {}; for (const [num, wi] of sp.pos) start['shot_' + String(num).padStart(3, '0')] = times[Math.min(wi, times.length - 1)];
  return start;
}

// длительность каждого элемента: не дольше, чем до следующего элемента в том же месте экрана
function fitDurations(start) {
  const items = plan.items.filter((it) => start[it.shot] != null).sort((a, b) => start[a.shot] - start[b.shot]);
  items.forEach((it, i) => {
    let dur = it.dur || DUR[it.type];
    for (const nx of items.slice(i + 1)) {
      if (start[nx.shot] - start[it.shot] >= dur) break;
      if (clash(ZONE[it.type], ZONE[nx.type])) { dur = Math.max(1.6, start[nx.shot] - start[it.shot] - 0.05); break; }
    }
    it.dur = +dur.toFixed(2);
  });
}

function buildTimeline(start) {
  const items = plan.items.filter((it) => start[it.shot] != null).map((it) => ({ ...it, at: start[it.shot] }));
  const fmt = (s) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${(s % 60).toFixed(1).padStart(4, '0')}`;
  fs.writeFileSync(path.join(outDir, 'timings.txt'), items.map((it) => `${fmt(it.at)}  ${fileOf(it)}`).join('\r\n') + '\r\n');
  const total = Math.max(...items.map((it) => it.at + (it.dur || DUR[it.type]))) + 1;
  const args = ['-f', 'lavfi', '-i', `color=c=black@0:s=1920x1080:r=${FPS}:d=${total.toFixed(2)},format=yuva444p10le`];
  let chain = '', last = '0:v';
  items.forEach((it, k) => {
    args.push('-i', path.join(outDir, fileOf(it)));
    chain += `[${k + 1}:v]setpts=PTS-STARTPTS+${it.at.toFixed(3)}/TB[e${k}];[${last}][e${k}]overlay=eof_action=pass:format=auto[o${k}];`;
    last = `o${k}`;
  });
  args.push('-filter_complex', chain.slice(0, -1), '-map', `[${last}]`, '-c:v', 'prores_ks', '-profile:v', '4444', '-qscale:v', '11',
    '-pix_fmt', 'yuva444p10le', path.join(outDir, 'ALL_overlays.mov'));
  console.log('Собираю одну дорожку на весь ролик...');
  ffmpeg(args);
  console.log('Готово: ALL_overlays.mov  (+ timings.txt — во сколько стоит каждый элемент)');
}

(async () => {
  const srt = process.argv[3] ? path.resolve(process.argv[3]) : fs.readdirSync(planDir).filter((f) => f.toLowerCase().endsWith('.srt')).map((f) => path.join(planDir, f))[0];
  // время кадров: готовый shot_times.json (его пишет программа: {"shot_001": 0.0, ...}) или расчёт по субтитрам .srt
  const timesPath = path.join(planDir, 'shot_times.json');
  const start = fs.existsSync(timesPath) ? JSON.parse(fs.readFileSync(timesPath, 'utf8'))
    : srt && fs.existsSync(path.join(planDir, 'shotpos.json')) ? shotStarts(srt) : null;
  if (start) fitDurations(start);
  await renderAll();
  if (start) buildTimeline(start);
  else console.log('Субтитров .srt рядом с планом нет — общая дорожка не собрана. Элементы лежат по номерам кадров.');
  console.log('Папка:', outDir);
})();
