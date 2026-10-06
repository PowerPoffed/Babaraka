// Рендер моушн-элементов (титр, карта, источник) в видео с прозрачным фоном.
// Windows: использует встроенный браузер Microsoft Edge и ffmpeg.
const { chromium } = require('playwright');
const fs = require('fs'); const path = require('path'); const { execFileSync } = require('child_process');
const FPS = 30;
const JOBS = [['title', 3.5], ['map', 4.5], ['src', 4.0]];
(async () => {
  let browser;
  try { browser = await chromium.launch({ channel: 'msedge' }); }          // Windows: Edge
  catch (e) { browser = await chromium.launch(); }                          // иначе встроенный Chromium Playwright
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  await page.goto('file://' + path.resolve(__dirname, 'anim.html'));
  await page.evaluate(() => document.fonts.ready);
  const outDir = path.join(__dirname, 'out'); fs.mkdirSync(outDir, { recursive: true });
  for (const [id, dur] of JOBS) {
    const dir = path.join(__dirname, 'frames_' + id); fs.rmSync(dir, { recursive: true, force: true }); fs.mkdirSync(dir);
    await page.evaluate((id) => window.setup(id), id);
    const n = Math.round(dur * FPS);
    for (let i = 0; i < n; i++) {
      await page.evaluate(([id, t, d]) => window.draw(id, t, d), [id, i / FPS, dur]);
      await page.screenshot({ path: path.join(dir, `f_${String(i).padStart(4, '0')}.png`), omitBackground: true });
    }
    // видео с прозрачным фоном для CapCut / DaVinci / Premiere
    execFileSync('ffmpeg', ['-v', 'error', '-y', '-framerate', String(FPS), '-i', path.join(dir, 'f_%04d.png'),
      '-c:v', 'prores_ks', '-profile:v', '4444', '-qscale:v', '11', '-pix_fmt', 'yuva444p10le', path.join(outDir, id + '_alpha.mov')]);
    fs.rmSync(dir, { recursive: true, force: true });
    console.log('готово:', id + '_alpha.mov');
  }
  await browser.close();
})();
