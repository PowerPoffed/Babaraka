// render HTML animation layers to PNG frames with transparent background
const { chromium } = require('playwright');
const fs = require('fs'); const path = require('path');
const FPS = 30;
const JOBS = [['title', 3.5], ['map', 4.5], ['src', 4.0]];
(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  await page.goto('file://' + path.resolve(__dirname, 'anim.html'));
  await page.evaluate(() => document.fonts.ready);
  for (const [id, dur] of JOBS) {
    const dir = path.join(__dirname, 'frames_' + id); fs.rmSync(dir, { recursive: true, force: true }); fs.mkdirSync(dir);
    await page.evaluate((id) => window.setup(id), id);
    const n = Math.round(dur * FPS);
    for (let i = 0; i < n; i++) {
      await page.evaluate(([id, t, d]) => window.draw(id, t, d), [id, i / FPS, dur]);
      await page.screenshot({ path: path.join(dir, `f_${String(i).padStart(4, '0')}.png`), omitBackground: true });
    }
    console.log(id, n, 'frames');
  }
  await browser.close();
})();
