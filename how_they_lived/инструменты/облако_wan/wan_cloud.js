// Оживление кадров на арендованной видеокарте: RunPod + ComfyUI + Wan 2.2 14B (картинка -> видео) + Lightning LoRA (4 шага).
// Запуск: node wan_cloud.js <список.txt> <папка с картинками>
// Строка списка: shot_001|промт            -> длительность по умолчанию (config.json, default_seconds)
//                shot_001|4|промт          -> 4 секунды
//                shot_001|промт ... 3 sec  -> длительность прямо в промте: "3s", "4 sec", "5 seconds", "4 сек", "[3s]"
//                [HD] в любом месте промта -> этот кадр в 1280x720 (дольше и дороже)
// Готовые клипы: <рядом с папкой картинок>/video_clips/shot_001.mp4. Уже готовые пропускаются —
// чтобы переделать неудачный клип, удалите его mp4 и запустите снова.
'use strict';
const fs = require('fs');
const path = require('path');

const HERE = __dirname;
const DEFAULTS = {
  servers: [],
  runpod_api_key: '',
  stop_pods_when_done: true,
  default_seconds: 4,
  max_seconds: 5,
  fps: 16,
  width: 832, height: 480,
  hd_width: 1280, hd_height: 720,
  attempts: 3,
};
const MODELS = {
  high: 'wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors',
  low: 'wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors',
  loraHigh: 'wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors',
  loraLow: 'wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors',
  clip: 'umt5_xxl_fp8_e4m3fn_scaled.safetensors',
  vae: 'wan_2.1_vae.safetensors',
};
const NEG = '色调艳丽，过曝，静态，细节模糊不清，字幕，静止，整体发灰，最差质量，低质量，JPEG压缩残留，丑陋的，残缺的，多余的手指，画得不好的手部，画得不好的脸部，畸形的，毁容的，形态畸形的肢体，手指融合，静止不动的画面，杂乱的背景，三条腿，倒着走, morphing, distorted face, text, watermark';
// Варианты узла сохранения видео: в разных версиях ComfyUI у SaveVideo разные поля. Берём первый, который сервер примет.
const SAVE_VARIANTS = [
  { format: 'auto', codec: 'auto' },
  { format: 'mp4', codec: 'h264' },
  { format: 'auto', 'format.codec': 'auto' },
];

function loadConfig() {
  const file = path.join(HERE, 'config.json');
  if (!fs.existsSync(file)) {
    fs.copyFileSync(path.join(HERE, 'config.example.json'), file);
    fail(`Создан файл ${file}\nОткройте его, вставьте адрес вашей видеокарты в "servers" и запустите снова.`);
  }
  const cfg = { ...DEFAULTS, ...JSON.parse(fs.readFileSync(file, 'utf8')) };
  cfg.servers = cfg.servers.map(s => s.trim().replace(/\/+$/, '')).filter(s => s && !s.includes('XXXX'));
  if (!cfg.servers.length) fail(`В ${file} нет адреса видеокарты ("servers"). Пример: https://abc123xyz-8188.proxy.runpod.net`);
  return cfg;
}

function fail(msg) { console.error('\n' + msg + '\n'); process.exit(1); }
const sleep = ms => new Promise(r => setTimeout(r, ms));
const fmtTime = s => s >= 3600 ? `${Math.floor(s / 3600)} ч ${Math.round(s % 3600 / 60)} мин` : s >= 60 ? `${Math.floor(s / 60)} мин ${Math.round(s % 60)} сек` : `${Math.round(s)} сек`;

// Длительность: отдельная колонка "shot|4|..." или пометка в тексте промта. Пометку из промта убираем.
function parseLine(line, cfg) {
  const parts = line.split('|');
  if (parts.length < 2 || !parts[0].trim()) return null;
  const shot = parts[0].trim();
  let seconds = null, text;
  const col = parts.length >= 3 && parts[1].trim().match(/^(\d+(?:[.,]\d+)?)\s*(?:s|sec|с|сек)?$/i);
  if (col) { seconds = parseFloat(col[1].replace(',', '.')); text = parts.slice(2).join('|'); }
  else text = parts.slice(1).join('|');
  let hd = false;
  text = text.replace(/\[\s*HD\s*\]/gi, () => { hd = true; return ' '; });
  const re = /[\[(]?(?<![\p{L}\d])(\d+(?:[.,]\d+)?)\s*(?:seconds?|secs?|s|секунды|секунд|секунда|сек|с)(?![\p{L}\d])[\])]?/iu;
  const m = text.match(re);
  if (m) {
    if (seconds === null) seconds = parseFloat(m[1].replace(',', '.'));
    text = text.replace(m[0], ' ');
  }
  text = text.replace(/\s+([,.])/g, '$1').replace(/,\s*([.,])/g, '$1').replace(/\s{2,}/g, ' ').trim();
  let warn = '';
  if (seconds === null || !(seconds > 0)) seconds = cfg.default_seconds;
  if (seconds > cfg.max_seconds) { warn = `${seconds} сек -> ${cfg.max_seconds} сек (дольше Wan портит качество)`; seconds = cfg.max_seconds; }
  // Wan принимает число кадров вида 4n+1: 3 сек = 49, 4 сек = 65, 5 сек = 81 при 16 fps
  const frames = Math.max(1, Math.round(seconds * cfg.fps / 4)) * 4 + 1;
  return { shot, text, seconds, frames, hd, warn };
}

function findImage(dir, shot) {
  const exts = ['.png', '.jpg', '.jpeg', '.webp'];
  const files = fs.readdirSync(dir).filter(f => exts.includes(path.extname(f).toLowerCase()));
  const base = f => path.basename(f, path.extname(f));
  const hit = files.find(f => base(f) === shot) || files.find(f => /^[\s_\-.(]/.test(base(f).slice(shot.length)) && base(f).startsWith(shot));
  return hit ? path.join(dir, hit) : null;
}

function buildWorkflow(t, image, seed, prefix, cfg, save) {
  const w = t.hd ? cfg.hd_width : cfg.width, h = t.hd ? cfg.hd_height : cfg.height;
  return {
    '1': { class_type: 'UNETLoader', inputs: { unet_name: MODELS.high, weight_dtype: 'default' } },
    '2': { class_type: 'UNETLoader', inputs: { unet_name: MODELS.low, weight_dtype: 'default' } },
    '3': { class_type: 'LoraLoaderModelOnly', inputs: { model: ['1', 0], lora_name: MODELS.loraHigh, strength_model: 1.0 } },
    '4': { class_type: 'LoraLoaderModelOnly', inputs: { model: ['2', 0], lora_name: MODELS.loraLow, strength_model: 1.0 } },
    '5': { class_type: 'ModelSamplingSD3', inputs: { model: ['3', 0], shift: 5.0 } },
    '6': { class_type: 'ModelSamplingSD3', inputs: { model: ['4', 0], shift: 5.0 } },
    '7': { class_type: 'CLIPLoader', inputs: { clip_name: MODELS.clip, type: 'wan', device: 'default' } },
    '8': { class_type: 'VAELoader', inputs: { vae_name: MODELS.vae } },
    '9': { class_type: 'CLIPTextEncode', inputs: { clip: ['7', 0], text: t.text } },
    '10': { class_type: 'CLIPTextEncode', inputs: { clip: ['7', 0], text: NEG } },
    '11': { class_type: 'LoadImage', inputs: { image } },
    '12': { class_type: 'WanImageToVideo', inputs: { positive: ['9', 0], negative: ['10', 0], vae: ['8', 0], width: w, height: h, length: t.frames, batch_size: 1, start_image: ['11', 0] } },
    // 4 шага: первые 2 — модель high noise (движение), последние 2 — low noise (детали)
    '13': { class_type: 'KSamplerAdvanced', inputs: { model: ['5', 0], add_noise: 'enable', noise_seed: seed, steps: 4, cfg: 1.0, sampler_name: 'euler', scheduler: 'simple', positive: ['12', 0], negative: ['12', 1], latent_image: ['12', 2], start_at_step: 0, end_at_step: 2, return_with_leftover_noise: 'enable' } },
    '14': { class_type: 'KSamplerAdvanced', inputs: { model: ['6', 0], add_noise: 'disable', noise_seed: seed, steps: 4, cfg: 1.0, sampler_name: 'euler', scheduler: 'simple', positive: ['12', 0], negative: ['12', 1], latent_image: ['13', 0], start_at_step: 2, end_at_step: 10000, return_with_leftover_noise: 'disable' } },
    '15': { class_type: 'VAEDecode', inputs: { samples: ['14', 0], vae: ['8', 0] } },
    '16': { class_type: 'CreateVideo', inputs: { images: ['15', 0], fps: cfg.fps } },
    '17': { class_type: 'SaveVideo', inputs: { video: ['16', 0], filename_prefix: prefix, ...save } },
  };
}

async function http(url, opts = {}, timeoutMs = 120000) {
  const r = await fetch(url, { ...opts, signal: AbortSignal.timeout(timeoutMs) });
  if (!r.ok) {
    const body = await r.text().catch(() => '');
    const e = new Error(`${r.status} ${url.replace(/\?.*/, '')}\n${body.slice(0, 1500)}`);
    e.status = r.status; e.body = body;
    throw e;
  }
  return r;
}

function comboOptions(spec) {
  if (!spec) return [];
  if (Array.isArray(spec[0])) return spec[0];
  return (spec[1] && spec[1].options) || [];
}

async function checkServer(server) {
  try { await http(`${server}/system_stats`, {}, 20000); }
  catch (e) { return `не отвечает (${e.message.split('\n')[0]}). Видеокарта запущена? ComfyUI успел стартовать?`; }
  const need = [['UNETLoader', 'unet_name', [MODELS.high, MODELS.low]], ['LoraLoaderModelOnly', 'lora_name', [MODELS.loraHigh, MODELS.loraLow]],
    ['CLIPLoader', 'clip_name', [MODELS.clip]], ['VAELoader', 'vae_name', [MODELS.vae]]];
  const missing = [];
  for (const [node, input, files] of need) {
    const info = await (await http(`${server}/object_info/${node}`, {}, 30000)).json();
    const have = comboOptions(info[node].input.required[input]);
    for (const f of files) if (!have.includes(f)) missing.push(f);
  }
  return missing.length ? `нет моделей: ${missing.join(', ')}. Запустите на видеокарте setup_pod.sh (см. ИНСТРУКЦИЯ.txt).` : null;
}

let saveVariant = 0;

async function runOne(server, t, image, outFile, cfg) {
  const form = new FormData();
  form.append('image', new Blob([fs.readFileSync(image)]), `${t.shot}${path.extname(image)}`);
  form.append('overwrite', 'true');
  const up = await (await http(`${server}/upload/image`, { method: 'POST', body: form })).json();
  const imageName = up.subfolder ? `${up.subfolder}/${up.name}` : up.name;
  const seed = Math.floor(Math.random() * 2 ** 31);
  let promptId;
  for (;;) {
    const wf = buildWorkflow(t, imageName, seed, `wan_cloud/${t.shot}`, cfg, SAVE_VARIANTS[saveVariant]);
    try {
      const r = await http(`${server}/prompt`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ prompt: wf }) });
      promptId = (await r.json()).prompt_id;
      break;
    } catch (e) {
      // сервер не принял поля SaveVideo — пробуем следующий вариант
      if (e.status === 400 && /"17"/.test(e.body || '') && saveVariant < SAVE_VARIANTS.length - 1) { saveVariant++; continue; }
      throw e;
    }
  }
  const deadline = Date.now() + 30 * 60 * 1000;
  while (Date.now() < deadline) {
    await sleep(3000);
    const hist = await (await http(`${server}/history/${promptId}`, {}, 30000)).json();
    const item = hist[promptId];
    if (!item) continue;
    if (item.status && item.status.status_str === 'error') {
      const msg = (item.status.messages || []).filter(m => m[0] === 'execution_error').map(m => m[1].exception_message).join(' ');
      throw new Error(`ComfyUI: ${msg || 'ошибка выполнения'}`);
    }
    if (!item.status || !item.status.completed) continue;
    const files = [];
    for (const out of Object.values(item.outputs || {}))
      for (const v of Object.values(out)) if (Array.isArray(v)) for (const f of v) if (f && f.filename) files.push(f);
    const vid = files.find(f => /\.(mp4|webm|mov|mkv)$/i.test(f.filename));
    if (!vid) throw new Error('ComfyUI закончил, но видео не найдено в ответе');
    const q = new URLSearchParams({ filename: vid.filename, subfolder: vid.subfolder || '', type: vid.type || 'output' });
    const data = Buffer.from(await (await http(`${server}/view?${q}`, {}, 300000)).arrayBuffer());
    const ext = path.extname(vid.filename).toLowerCase();
    const target = ext === '.mp4' ? outFile : outFile.replace(/\.mp4$/, ext);
    fs.writeFileSync(target + '.part', data);
    fs.renameSync(target + '.part', target);
    return target;
  }
  throw new Error('нет ответа 30 минут');
}

async function stopPods(cfg, servers) {
  if (!cfg.stop_pods_when_done) return;
  for (const s of servers) {
    const m = s.match(/^https?:\/\/([a-z0-9]+)-\d+\.proxy\.runpod\.net/i);
    if (!m) continue;
    if (!cfg.runpod_api_key) { console.log(`!!! Выключите видеокарту вручную на runpod.io (Stop), иначе деньги продолжат списываться: ${m[1]}`); continue; }
    try {
      await http(`https://rest.runpod.io/v1/pods/${m[1]}/stop`, { method: 'POST', headers: { Authorization: `Bearer ${cfg.runpod_api_key}` } }, 30000);
      console.log(`Видеокарта ${m[1]} выключена (Stop). Диск сохранён; удалить совсем — Terminate на сайте.`);
    } catch (e) {
      console.log(`!!! Не получилось выключить ${m[1]}: ${e.message.split('\n')[0]}\n!!! Выключите вручную на runpod.io (Stop).`);
    }
  }
}

async function main() {
  const [listFile, imgDirArg] = process.argv.slice(2);
  if (!listFile || !imgDirArg) fail('Запуск: node wan_cloud.js <список.txt> <папка с картинками>');
  const imgDir = path.resolve(imgDirArg.replace(/^"|"$/g, ''));
  if (!fs.existsSync(listFile)) fail(`Нет файла списка: ${listFile}`);
  if (!fs.existsSync(imgDir)) fail(`Нет папки с картинками: ${imgDir}`);
  const cfg = loadConfig();
  const outDir = path.join(path.dirname(imgDir), 'video_clips');
  fs.mkdirSync(outDir, { recursive: true });

  const lines = fs.readFileSync(listFile, 'utf8').replace(/^﻿/, '').split(/\r?\n/).filter(l => l.includes('|') && !l.trim().startsWith('#'));
  const queue = [];
  let skipped = 0, noImage = [];
  for (const line of lines) {
    const t = parseLine(line, cfg);
    if (!t) continue;
    if (t.warn) console.log(`${t.shot}: ${t.warn}`);
    t.out = path.join(outDir, `${t.shot}.mp4`);
    if (['.mp4', '.webm'].some(e => fs.existsSync(t.out.replace(/\.mp4$/, e)))) { skipped++; continue; }
    t.image = findImage(imgDir, t.shot);
    if (!t.image) { noImage.push(t.shot); continue; }
    t.tries = 0;
    queue.push(t);
  }
  const bySec = {};
  for (const t of queue) bySec[t.seconds] = (bySec[t.seconds] || 0) + 1;
  console.log(`Список: ${lines.length} строк. Уже готово: ${skipped}. Нет картинки: ${noImage.length}. В очереди: ${queue.length}`);
  if (queue.length) console.log('Длительности: ' + Object.entries(bySec).map(([s, n]) => `${s} сек — ${n}`).join(', '));
  if (noImage.length) console.log(`Нет картинки для: ${noImage.slice(0, 20).join(', ')}${noImage.length > 20 ? ' …' : ''}`);
  console.log(`Клипы сохраняются в: ${outDir}\n`);
  if (!queue.length) { await stopPods(cfg, cfg.servers); return; }

  const servers = [];
  for (const s of cfg.servers) {
    const problem = await checkServer(s);
    if (problem) console.log(`Сервер ${s}: ${problem}`);
    else { servers.push(s); console.log(`Сервер ${s}: готов`); }
  }
  if (!servers.length) fail('Нет ни одной готовой видеокарты. Исправьте и запустите снова.');

  const total = queue.length, failed = [];
  let done = 0;
  const t0 = Date.now();
  async function worker(server, n) {
    let errorsInRow = 0;
    while (queue.length) {
      const t = queue.shift();
      t.tries++;
      const start = Date.now();
      try {
        await runOne(server, t, t.image, t.out, cfg);
        done++; errorsInRow = 0;
        const avg = (Date.now() - t0) / 1000 / done;
        console.log(`[${done + failed.length}/${total}] ${t.shot} ${t.seconds} сек${t.hd ? ' HD' : ''} — ${fmtTime((Date.now() - start) / 1000)} (карта ${n}), осталось ~${fmtTime(avg * queue.length)}`);
      } catch (e) {
        errorsInRow++;
        console.log(`${t.shot}: ошибка (попытка ${t.tries}/${cfg.attempts}) на карте ${n}: ${e.message.split('\n').slice(0, 3).join(' ')}`);
        if (t.tries < cfg.attempts) queue.push(t); else failed.push(t.shot);
        if (errorsInRow >= 5) { console.log(`Карта ${n} (${server}) 5 ошибок подряд — отключаю её.`); return; }
        await sleep(5000);
      }
    }
  }
  await Promise.all(servers.map((s, i) => worker(s, i + 1)));

  console.log(`\nГотово: ${done} из ${total} за ${fmtTime((Date.now() - t0) / 1000)}.`);
  if (queue.length) console.log(`Не обработано (все карты отключились): ${queue.length}. Запустите снова — доделает только недостающие.`);
  if (failed.length) console.log(`Не получились: ${failed.join(', ')}. Запустите снова — доделает только их.`);
  await stopPods(cfg, cfg.servers);
}

main().catch(e => fail('Ошибка: ' + e.message));
