# Сборка ролика про ацтеков из shots.txt: текст озвучки, shotpos, полные промпты (prompts.txt),
# раскадровка и короткие промпты для агента Google Flow пачками по 24.
import re, json, collections, os
D = os.path.dirname(os.path.abspath(__file__))
os.makedirs(D + '/Picker', exist_ok=True)

STYLE = ("2D cartoon illustration in a modern adult animated TV series style, bold clean dark outlines, "
         "simple cartoon human faces with big round white eyes with small black pupils, expressive eyebrows and simple expressions, "
         "flat cel-shaded colors with soft shading, muted cinematic color palette, atmospheric lighting, richly detailed background with depth, wide 16:9 frame.")
STYLE_NP = ("2D cartoon illustration in a modern adult animated TV series style, bold clean dark outlines, flat cel-shaded colors with soft shading, "
            "muted cinematic color palette, atmospheric lighting, richly detailed background with depth, wide 16:9 frame.")
QUAL = "High quality, crisp clean linework, professional animated series background art."

# персонажи: полное описание (для программы) и имя (для Flow, где описание задано в инструкциях агента)
CH = {
 'COATL': ("COATL", "an Aztec farmer in his early 30s with warm brown skin, straight black hair cut in a bowl shape with short straight bangs, "
           "a plain off-white knee-length maguey-fiber cloak knotted on one shoulder over a white loincloth, barefoot"),
 'CITLA': ("CITLALI", "an Aztec woman in her late 20s with warm brown skin and long black hair twisted up into two small knots above her forehead, "
           "a loose white blouse with a simple red border and a long white wrap skirt, barefoot"),
 'BOY': ("BOY", "an Aztec boy about 12 years old with warm brown skin, straight black bowl-cut hair and a small plain off-white cloak over a white loincloth"),
 'GIRL': ("GIRL", "an Aztec girl about 10 years old with warm brown skin, a long black braid, a loose white blouse and a white wrap skirt"),
 'GRANDPA': ("GRANDPA", "an old Aztec man with warm brown skin, short gray hair, a kind wrinkled face and a plain off-white knee-length cloak"),
 'NOBLE': ("NOBLE", "an Aztec nobleman in his 40s with warm brown skin, a long ankle-length white cotton cloak with bright red and blue patterns, "
           "a green jade necklace, a feather headband and leather sandals"),
 'SPANIARD': ("SPANIARD", "a Spanish soldier from 1519 with a short dark beard, a rounded steel helmet, a steel breastplate over a red shirt and dark trousers"),
 'YOU': ("YOU", "a modern man in his late 20s with short messy brown hair and a plain white t-shirt"),
}
FEM = {'CITLA', 'GIRL'}
FAMILY_FLOW = "the family: COATL, CITLALI, BOY and GIRL"
FAMILY_FULL = ("an Aztec family of four: " + CH['COATL'][1].replace('an Aztec farmer', 'the father, an Aztec farmer') +
               "; the mother, " + CH['CITLA'][1].replace('an Aztec woman', 'an Aztec woman') + "; a boy about 12 and a girl about 10 in simple white clothes")

SETTING = {
 'HOUSE': "Setting: inside a simple one-room Aztec adobe house with whitewashed walls, woven reed mats on a packed earth floor, clay pots and a small three-stone hearth with a clay griddle.",
 'YARD': "Setting: a small Aztec house courtyard with white adobe walls, flowering plants, clay pots and big clay water jars.",
 'CHIN': "Setting: long narrow green garden fields on the water lined with tall willow trees and separated by calm canals, volcanoes in the distance.",
 'CANAL': "Setting: a city canal lined with white adobe houses with flowering rooftops, dugout canoes on the water.",
 'CITY': "Setting: the Aztec island city of Tenochtitlan on a blue lake, white adobe houses, canals, causeways and a huge stepped pyramid temple with two shrines on top, volcanoes in the distance.",
 'LAKE': "Setting: a wide calm blue lake with reeds, a stone causeway and mountains around.",
 'MKT': "Setting: a huge open-air Aztec market plaza with rows of stalls under cloth shades, piles of maize, peppers, tomatoes, pottery and colorful cloth.",
 'SCHOOL': "Setting: a simple Aztec school house with adobe walls and an open courtyard.",
 'TEMPLE': "Setting: a wide stone plaza in front of a huge stepped pyramid temple with two shrines on top.",
 'PALACE': "Setting: a spacious Aztec palace room with painted walls, reed mats, flowers and a garden view.",
 'COURT': "Setting: a long narrow stone ballcourt with sloping side walls and a carved stone ring high on each side wall.",
 'FOREST': "Setting: a lush green tropical forest with tall trees and ferns.",
 'EUR': "Setting: a 16th-century European town with timber houses and a muddy street.",
 'HOME': "Setting: a cozy small modern apartment with a couch, a lamp, a kitchen corner and a window.",
 'CANDLE': "Setting: a simple stone room with a wooden table, a candle and rolled papers.",
 'CAVE': "",
 'CARD': "",
}
LOCN = {'HOUSE': 'дом (внутри)', 'YARD': 'двор', 'CHIN': 'чинампы', 'CANAL': 'канал', 'CITY': 'город', 'LAKE': 'озеро', 'MKT': 'рынок',
        'SCHOOL': 'школа', 'TEMPLE': 'храм', 'PALACE': 'дворец', 'COURT': 'стадион', 'FOREST': 'лес', 'EUR': 'Европа', 'HOME': 'дом YOU',
        'CANDLE': 'комната со свечой', 'CAVE': 'пещера', 'CARD': 'карточка'}
PLACEWORDS = re.compile(r'\b(courtyard|canal|lake|causeway|market|plaza|temple|house|field|garden|school|ballcourt|forest|street|kitchen|couch|hearth|room|stall|town|city|hill|canoe|shore|apartment|tree)\b', re.I)

def light(sc, loc):
    t = sc.lower()
    if re.search(r'\b(night|midnight|stars|starry|dark)\b', t):
        if re.search(r'fire|flame|torch|hearth|bonfire|brazier|ember|candle', t): return "Lighting: deep blue night with warm orange firelight, soft glow."
        return "Lighting: deep blue moonlight with soft silver highlights, calm night atmosphere."
    if re.search(r'\b(sunset|dusk|evening)\b', t): return "Lighting: warm orange sunset light with long soft shadows."
    if re.search(r'\b(dawn|sunrise|morning|early)\b', t): return "Lighting: soft pink and gold early morning light."
    if loc == 'CANDLE' or 'candle' in t: return "Lighting: warm candle light in a dim room."
    if loc == 'HOME': return "Lighting: warm cozy lamp light."
    if loc == 'HOUSE': return "Lighting: warm light from the doorway and the hearth."
    if loc == 'EUR': return "Lighting: dull gray overcast daylight."
    return "Lighting: bright warm sunny daylight with soft shadows."

def chars(sc, full):
    """Заменяет теги персонажей. Возвращает текст и множество персонажей."""
    used = set(re.findall(r'\{([A-Z]+)\}', sc)) - {'ALONE', 'ALONEF', 'VID', 'FAMILY'}
    if '{FAMILY}' in sc:
        sc = sc.replace('{FAMILY}', FAMILY_FULL if full else FAMILY_FLOW)
    for k in used:
        sc = sc.replace('{%s}' % k, (CH[k][1] + ',' if full else CH[k][0]))
    if full: sc = re.sub(r',(\s*)(,|\.|;| and | while | points| glares| laughs)', lambda m: m.group(1) + m.group(2).lstrip(), sc)
    return sc, used

def build(r, full):
    sc = r['sc']; typ = r['typ']; loc = r['loc']
    vid = '{VID}' in sc; alone = '{ALONE}' in sc or '{ALONEF}' in sc
    fam = '{FAMILY}' in sc
    sc = re.sub(r'\s*\{(VID|ALONE|ALONEF)\}', '', sc).strip()
    sc, used = chars(sc, full)
    sc = sc[0].upper() + sc[1:]
    sc = sc.rstrip(' .') + '.'
    setting = '' if PLACEWORDS.search(r['sc']) and loc not in ('HOUSE', 'YARD') else SETTING.get(loc, '')
    if loc in ('HOUSE', 'YARD') and re.search(r'courtyard|house|hearth|mat', r['sc']): setting = SETTING[loc]
    L = light(r['sc'], loc)
    hands = 'only the hands are visible' in r['sc']
    parts = []
    if typ == 'P':
        cam = '' if re.match(r'(close-up|wide)', r['sc'], re.I) else 'Medium shot. '
        parts.append(cam + sc)
        if alone:
            parts.append("Only one person in the scene, nobody else around.")
        if fam:
            parts.append("Only these four persons in the scene.")
        if re.search(r'\bsleeping\b', r['sc']) and not re.search(r'awake', r['sc']):
            parts.append("Everyone is fast asleep with eyes fully closed, drawn as simple curved lines.")
        parts += [setting, L]
        if hands: parts.append("Composition: tight close-up on the hands, anatomically correct hands with five fingers.")
        else: parts.append("Composition: characters big and clear in the frame, faces clearly visible.")
        tail = "Everyone is fully clothed. No text, no letters, no watermark."
    elif typ == 'W':
        parts += ['Wide shot. ' + sc, "Small distant figures with simple shapes and normal human proportions, no close-up faces.", setting, L]
        tail = "Everyone is fully clothed. No text, no letters, no watermark."
    elif typ == 'E':
        cam = '' if re.match(r'(close-up|wide|high)', r['sc'], re.I) else 'Wide establishing shot. '
        parts += [cam + sc, setting, L, "No people in the scene."]
        tail = "No text, no letters, no watermark."
    else:
        parts += ['Still life close-up. ' + sc, "Simple objects centered on a plain warm beige background, objects large and clear. Soft even studio light."]
        tail = "No people. No text, no letters, no watermark."
    if vid and typ != 'C':
        parts.append("Video-ready: the main subject fully inside the frame, soft natural elements that can move such as water, smoke, leaves and flames.")
    body = ' '.join(p for p in parts if p)
    if full:
        style = STYLE if typ in ('P', 'W') else STYLE_NP
        return re.sub(r'\s+', ' ', f"{style} {body} {QUAL} {tail}").strip(), used
    return re.sub(r'\s+', ' ', f"{body} {tail}").strip(), used

def norm(s): return re.sub(r"[^a-z0-9' ]+", " ", s.lower().replace("’", "'").replace("/", "").replace("é", "e").replace("í", "i")).split()

parts = []; rows = []
for l in open(D + '/shots.txt', encoding='utf-8').read().splitlines():
    if not l.strip(): continue
    if l.startswith('#'): parts.append([l[2:].strip(), []]); continue
    txt, loc, typ, sc = l.split('|', 3)
    parts[-1][1].append(len(rows)); rows.append(dict(txt=txt.strip(), loc=loc, typ=typ, sc=sc.strip()))

for r in rows:
    r['full'], r['used'] = build(r, True)
    r['flow'], _ = build(r, False)

vo = []; zv = []
for i, (title, idx) in enumerate(parts, 1):
    body = ' '.join(rows[j]['txt'] for j in idx)
    vo.append(f"{title}\n\n{body}\n"); zv.append(f"===== ЧАСТЬ {i} =====\n{body}\n")
open(D + '/voiceover_EN.txt', 'w', encoding='utf-8').write('\n'.join(vo))
open(D + '/ОЗВУЧКА_по_частям.txt', 'w', encoding='utf-8').write('\n'.join(zv))

t = open(D + '/voiceover_EN.txt', encoding='utf-8').read().split('PART 1', 1)[1].split('\n', 1)[1]
t = re.sub(r'^PART .*$', '', t, flags=re.M); W = norm(t)
pos = []; c = 0
for r in rows: pos.append(c); c += len(norm(r['txt']))
assert c == len(W), (c, len(W))
sp = {'W': W, 'pos': [[i + 1, p] for i, p in enumerate(pos)]}
json.dump(sp, open(D + '/shotpos.json', 'w')); json.dump(sp, open(D + '/Picker/.shotpos.json', 'w'))
dur = [(b - a) / 162 * 60 for a, b in zip(pos, pos[1:] + [len(W)])]

open(D + '/prompts.txt', 'w', encoding='utf-8').write('# TITLE: What Was Everyday Life Like for the Aztecs\n' +
    '\n'.join(f"shot_{i + 1:03d}|{r['full']}" for i, r in enumerate(rows)) + '\n')
sb = []; t0 = 0
for i, (r, d) in enumerate(zip(rows, dur)):
    sb.append(f"shot_{i + 1:03d} | {LOCN[r['loc']]} | {t0:6.1f}s +{d:.1f}s | \"{r['txt']}\"\n    {r['flow']}\n"); t0 += d
open(D + '/storyboard.txt', 'w', encoding='utf-8').write('\n'.join(sb))

# Flow: пачки по 24
HEAD = ("Generate {n} images, one for each prompt below, in the style from the instructions. Follow each prompt exactly. "
        "Characters written in CAPITALS (COATL, CITLALI, BOY, GIRL, GRANDPA, NOBLE, SPANIARD, YOU) must look exactly like in their instructions and reference images. "
        "Make exactly ONE image per prompt, one by one, and label each image with its shot number. Do not make extra variations, "
        "do not repeat any shot, and stop after the last shot in this list.")
out = ["Google Flow — агент. Пачки по 24 кадра. Каждую пачку — отдельным сообщением агенту.",
       "Перед первой пачкой: настроить инструкции из flow_INSTRUCTIONS.txt и сделать референсы персонажей (flow_REFERENCES.txt).",
       "Скачанные картинки называть shot_XXX.png (номер кадра).", ""]
for b in range(0, len(rows), 24):
    chunk = list(range(b, min(b + 24, len(rows))))
    who = sorted(set().union(*[rows[i]['used'] for i in chunk]) | ({'COATL', 'CITLA', 'BOY', 'GIRL'} if any('{FAMILY}' in rows[i]['sc'] for i in chunk) else set()))
    names = ', '.join(CH[k][0] for k in who) or 'нет'
    out.append(f"==================== ПАЧКА {b // 24 + 1}  (shot_{chunk[0] + 1:03d} – shot_{chunk[-1] + 1:03d}, {len(chunk)} шт.) ====================")
    out.append(f"Персонажи в пачке: {names}\n")
    out.append(HEAD.format(n=len(chunk)) + "\n")
    out += [f"shot_{i + 1:03d}: {rows[i]['flow']}" for i in chunk]
    out.append("")
open(D + '/flow_batches_of_24.txt', 'w', encoding='utf-8').write('\n'.join(out))

# проверки
BAN = ['drinking', 'naked', 'nude', 'blood', 'gore', 'corpse', 'dead body', 'skull', 'question mark', 'symbol', 'caveman', 'primitive', 'savage', 'sip']
bad = []
for i, r in enumerate(rows):
    pl = r['full'].lower()
    for b in BAN:
        if re.search(r'\b' + b + r'\b', pl): bad.append((i + 1, b))
    if '{' in r['full'] or '{' in r['flow']: bad.append((i + 1, 'tag'))
    if r['typ'] in ('E', 'C') and re.search(r'\b(eyes?|faces?|everyone|people|person|man|woman)\b', r['flow'].split('No people')[0].lower()): bad.append((i + 1, 'person word in no-people shot'))
    if r['typ'] == 'P' and 'Only one person' in r['flow'] and len(r['used']) > 1: bad.append((i + 1, 'alone but 2 chars'))
    if len(r['full'].split()) > 265: bad.append((i + 1, 'long %d' % len(r['full'].split())))
    if r['loc'] not in SETTING: bad.append((i + 1, 'loc ' + r['loc']))
dups = [k for k, v in collections.Counter(r['sc'] for r in rows).items() if v > 1]
wc = [len(norm(r['txt'])) for r in rows]
chars_n = len(open(D + '/voiceover_EN.txt', encoding='utf-8').read().replace('\n', ' '))
print('shots', len(rows), 'words', len(W), 'chars', sum(len(r['txt']) + 1 for r in rows), 'min %.1f' % (len(W) / 162),
      'avg %.2f max %.1f' % (sum(dur) / len(dur), max(dur)))
print('words/shot min', min(wc), 'max', max(wc), 'short:', [i + 1 for i, w in enumerate(wc) if w < 4], 'long:', [i + 1 for i, w in enumerate(wc) if w > 9])
print('over4s:', [(i + 1, round(d, 1)) for i, d in enumerate(dur) if d > 4])
print('bad:', bad); print('dups:', dups)
print('types', collections.Counter(r['typ'] for r in rows))
print('chars', collections.Counter(k for r in rows for k in r['used']))
L = [len(r['full'].split()) for r in rows]; print('prompt words min/avg/max', min(L), sum(L) // len(L), max(L))
