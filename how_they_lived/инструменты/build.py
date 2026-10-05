import re,json,collections,os,shutil
OUT='Ancient_Sleep_Without_Beds'
os.makedirs(OUT+'/Picker',exist_ok=True)
PEOPLE="2D cartoon illustration in a modern adult animated TV series style, bold clean dark outlines, simple cartoon human faces with big round white eyes with small black pupils, expressive eyebrows and simple expressions, flat cel-shaded colors with soft shading, muted desaturated cinematic color palette, atmospheric lighting, richly detailed background with depth, wide 16:9 storyboard frame."
NOFACE="2D cartoon illustration in a modern adult animated TV series style, bold clean dark outlines, flat cel-shaded colors with soft shading, muted desaturated cinematic color palette, atmospheric lighting, richly detailed background with depth, wide 16:9 storyboard frame."
TAIL="Everyone is fully clothed, no nudity. No text, no letters, no watermark."
TAIL_NP="No text, no letters, no watermark."
QUAL="High quality, crisp clean linework, professional animated series background art, rich detail."
END_LAND="An empty landscape with nobody in it. Rocks, trees and objects have plain natural surfaces."
END_ROOM="An empty room with nobody in it. Objects have plain natural surfaces."
END_ANIM="Only animals in the scene, with normal natural animal anatomy. Rocks, trees and objects have plain natural surfaces."
END_CARD="Simple objects centered on a plain warm beige background. Plain natural objects with simple surfaces."
T={
'{CAVE}':"a grown adult prehistoric man in his mid 30s with a mature masculine face, a short thick dark brown beard covering his jaw, messy shoulder-length dark brown hair, a ragged brown fur tunic, barefoot",
'{YOU}':"a modern man in his late 20s with short messy brown hair and a plain white t-shirt",
'{ALONE}':"Only one person in the scene. He is completely alone, nobody else around, no crowd.",
'{ALONEF}':"Only one person in the scene. She is completely alone, nobody else around, no crowd.",
'{OLDW}':"an old woman with long gray hair tied back and a kind wrinkled face, wearing a simple brown fur and leather wrap, a normal human body with normal human proportions",
'{OLDM}':"an old man with short gray hair, a short gray beard and a kind wrinkled face, wearing a simple brown fur and leather wrap, a normal human body with normal human proportions",
'{GRANNY}':"an old grandmother with short gray hair, round glasses and a pink cardigan",
'{SCI1}':"a woman archaeologist in her 50s with glasses, gray hair in a bun and a khaki shirt",
'{SCI2}':"a man scientist in his 60s with a gray beard, round glasses and a green sweater",
'{SAMSON}':"an anthropologist in his 40s with a short brown beard, a khaki shirt and a baseball cap",
'{WRANG}':"an anthropologist in his 70s with white hair, glasses and a blue shirt",
'{HIST}':"a historian in his 70s with gray hair, glasses and a tweed jacket",
'{EARLY}':"a small early human ancestor with long strong arms, short dark hair and a normal human face with a slightly heavy brow, upright human posture, wearing a simple brown hide wrap",
'{ERECTUS}':"a tall slim early human with long legs, short dark hair and a normal human face with a slightly heavy brow, wearing a simple brown hide wrap, normal human proportions",
'{G3}':"Three adult hunter-gatherers",
'{G2}':"Two adult hunter-gatherers",
}
GROUP=" Medium shot, the characters are big in the frame. They are anatomically modern humans with normal human proportions and slim upright bodies, men and women with neat dark brown hair, the men with short stubble beards, wearing simple brown fur tunics that fully cover the chest and shoulders, tied with thin leather cords, clear simple cartoon human faces with big round white eyes. Only these {n} in the scene, nobody in the background."
ANIMALS=re.compile(r'\b(lions?|chimpanzees?|hyenas?|leopards?|bats?|frogs?|owls?|mosquito|mosquitoes|ants?|beetles?|bugs?|larvae|ticks?|fleas?|louse|insects?)\b',re.I)
def norm(s): return re.sub(r"[^a-z0-9' ]+"," ",s.lower().replace("’","'").replace("/","")).split()
parts=[];rows=[]
for l in open('shots.txt',encoding='utf-8').read().splitlines():
    if not l.strip(): continue
    if l.startswith('#'): parts.append([l[2:].strip(),[]]); continue
    txt,loc,typ,sc=l.split('|',3); parts[-1][1].append(len(rows)); rows.append(dict(txt=txt,loc=loc,typ=typ,sc=sc.strip()))

FEM={'{OLDW}','{GRANNY}','{SCI1}'}
CHARS=['{CAVE}','{YOU}','{OLDW}','{OLDM}','{GRANNY}','{SCI1}','{SCI2}','{SAMSON}','{WRANG}','{HIST}','{EARLY}','{ERECTUS}']
SETTING={
'CAMP':"Setting: an open-air hunter-gatherer camp in a grassy clearing, a ring of stones around a fire pit, grass sleeping mats, wooden spears and leather bags on the ground, trees at the edge of the clearing.",
'CAVE':"Setting: a large dry cave with rough brown and gray rock walls, a sandy floor with patches of ash, daylight coming from the cave entrance.",
'ROCK':"Setting: a huge overhanging sandstone rock shelter above a green river valley, a flat sandy floor, green bushes at the edge.",
'SAV':"Setting: an African savanna with tall golden grass, flat-topped acacia trees and distant blue hills.",
'FOR':"Setting: a dense green tropical forest with tall trunks, hanging vines, ferns and moss.",
'RIV':"Setting: a wide calm river with reedy banks, tall sedges and green forest on both sides.",
'MTN':"Setting: rugged rocky mountains and cliffs above a deep green valley.",
'STP':"Setting: a wide open dry plain with low grass and scattered bushes under a huge sky.",
'SWP':"Setting: a swamp with tall reeds, still dark water, lily pads and mossy logs.",
'LAB':"Setting: a modern museum workroom with wooden tables, trays of bones and stone tools, shelves and a big window.",
'HOME':"Setting: a cozy small modern apartment with a bed, a nightstand, a lamp and a window.",
'VILL':"Setting: a small medieval stone cottage with a thatched roof, a stone hearth, a straw bed and simple wooden furniture.",
'SEA':"Setting: a windswept green island coast by the gray sea with low round stone houses set into the ground.",
'EGY':"Setting: an ancient Egyptian house with white plaster walls, painted borders, linen curtains and palm trees outside.",
}
PLACEWORDS=re.compile(r'\b(in|inside|on|at|across|through|over|by|under|from) (a|an|the|his|her|their|one|dry|open|tall|dark)\b|savanna|forest|cave|river|camp|lab|museum|library|kitchen|bedroom|office|cottage|village|shelter|plain|bush|study|tent|coast|swamp|mountain|valley|cliff|steppe|beige|excavation|nest|tree|wall|branch|desk|bed\b',re.I)
def light(sc,loc,people=True):
    t=sc.lower()
    if re.search(r'\b(night|nights|moon|moonlight|midnight|stars|lantern|darkness)\b',t) or re.search(r'\bat night\b',t):
        if re.search(r'fire|flame|ember|hearth|candle|lantern|coals',t): return "Lighting: deep blue night light with warm orange firelight on "+("the characters" if people else "rocks and grass")+", soft glow."
        return "Lighting: deep blue moonlight with soft silver highlights, calm night atmosphere."
    if re.search(r'\b(sunset|dusk|evening|twilight)\b',t): return "Lighting: warm orange sunset light with long soft shadows."
    if re.search(r'\b(dawn|sunrise|morning)\b',t): return "Lighting: soft pink and gold early morning light, light mist."
    if re.search(r'\b(noon|midday|hot|heat)\b',t): return "Lighting: bright warm midday sunlight with short shadows."
    if loc=='LAB' and re.search(r'excavation|cave|shelter|bush|camp|tent|forest|ground',t): loc='CAVE' if re.search(r'cave|shelter',t) else 'X'
    return {'HOME':"Lighting: warm cozy lamp light.",'LAB':"Lighting: soft clean daylight from a big window.",'CAVE':"Lighting: soft daylight from the cave entrance with deep warm shadows inside.",'VILL':"Lighting: dim warm candle and hearth light."}.get(loc,"Lighting: soft natural daylight with gentle shadows.")
def camera(sc,typ):
    t=sc.lower()
    if 'close-up' in t: return ''
    if t.startswith('wide shot') or 'seen from far away' in t: return ''
    return {'P':'Medium shot. ','E':'Wide establishing shot. ','C':'Still life close-up. '}[typ]
def expand_chars(sc):
    fem=False
    m2=re.match(r'^(\{[A-Z0-9]+\}) and (\{[A-Z0-9]+\})[ ,]+(.*)$',sc)
    m3=re.match(r'^(\{[A-Z0-9]+\}) explaining something to (\{[A-Z0-9]+\})[ ,]+(.*)$',sc)
    m=re.match(r'^(\{[A-Z0-9]+\})\s+(.*)$',sc)
    if m2 and m2.group(1) in CHARS and m2.group(2) in CHARS:
        a,b2,rest=m2.groups()
        sc=f"Two characters. The first is {T[a]}. The second is {T[b2]}. Together they are {rest}"
        return sc,False
    if m3 and m3.group(1) in CHARS and m3.group(2) in CHARS:
        a,b2,rest=m3.groups()
        sc=f"Two characters. The first is {T[a]}. The second is {T[b2]}. The first is explaining something to the second, {rest}"
        return sc,False
    if m and m.group(1) in CHARS:
        tag,rest=m.groups(); fem=tag in FEM
        rest=re.sub(r'^(and|while)\s+','',rest)
        sc=f"The character is {T[tag]}. {'She' if fem else 'He'} is {rest}"
    for k in CHARS: 
        if k in sc and k in FEM: fem=fem or sc.find(k)<20
        sc=sc.replace(k,T[k]+',')
    sc=re.sub(r',\s*,',',',sc).replace(',.','.')
    if re.search(r'\bwoman\b|\bshe\b|\bher\b',sc,re.I) and not re.search(r'\bman\b|\bhe\b',sc.replace('woman',''),re.I): fem=True
    return sc,fem
VIDREADY=" Video-ready composition: every character and the main subject are fully inside the frame with empty space around them, nothing important touches the edges of the frame, clear readable forms, simple background with soft natural elements that can move such as flames, smoke, mist, grass and leaves."
def build(r):
    vid='{VID}' in r['sc']
    r=dict(r); r['sc']=r['sc'].replace(' {VID}','').replace('{VID}','')
    sc=r['sc']; typ=r['typ']; loc=r['loc']; n=None
    if '{G3}' in sc: n='three'
    if '{G2}' in sc: n='two'
    sc=sc.replace('{G3}',T['{G3}']).replace('{G2}',T['{G2}'])
    alone='{ALONE}' in sc or '{ALONEF}' in sc
    sc=sc.replace('{ALONE}','').replace('{ALONEF}','').strip()
    sc,fem=expand_chars(sc)
    sc=sc.rstrip(' .')+'.'
    sc=sc[0].upper()+sc[1:]
    setting='' if PLACEWORDS.search(r['sc']) else SETTING.get(loc,'')
    L=light(r['sc'],loc,typ=='P')
    if typ=='P':
        low=r['sc'].lower()
        asleep=re.search(r'\b(asleep|sleeping|sleeps|deep sleep|closing his eyes|in his sleep)\b',low)
        awake=re.search(r'awake|eyes open|eyes wide open|one eye half open|turning over|poking|stretching|whispering|yawning|talking',low)
        style=PEOPLE
        sleepnote=''
        sleeping_all=False
        if asleep and not awake:
            style=PEOPLE.replace("simple cartoon human faces with big round white eyes with small black pupils, expressive eyebrows and simple expressions","simple cartoon human faces with calm relaxed expressions")
            multi = bool(n) or 'Only these two' in r['sc'] or 'Only these three' in r['sc'] or re.search(r'\b(couple|man and woman|mother, a father)\b',low)
            subj = ("All of them are" if multi else ("She is" if fem else "He is"))
            sleepnote=f" {subj} lying down fast asleep with eyes fully closed, the closed eyes drawn as two simple curved lines like small downward arcs, relaxed eyebrows, peaceful sleeping "+("faces." if multi else "face.")
            sleeping_all=True
        elif not n and re.search(r'squeezed shut|half closed|dreamy|sleepy|yawning',low) and not re.search(r'one yawning',low):
            style=PEOPLE.replace("simple cartoon human faces with big round white eyes with small black pupils, expressive eyebrows and simple expressions","simple cartoon human faces with expressive eyebrows and simple expressions")
            sleepnote=" The eyes are "+("squeezed shut" if re.search(r'squeezed shut|yawning',low) else "heavy and half closed, sleepy drooping eyelids")+"."
        elif n and re.search(r'sleepy',low):
            style=PEOPLE.replace("simple cartoon human faces with big round white eyes with small black pupils, expressive eyebrows and simple expressions","simple cartoon human faces with expressive eyebrows and simple expressions")
            sleepnote=" Both have sleepy faces with heavy half-closed eyelids."
        elif asleep and awake:
            sleepnote=" The sleeping person has eyes fully closed, drawn as two simple curved lines; the awake person has big round open eyes."
        hands='only the hands are visible' in r['sc'].lower()
        sleep_comp = "Composition: slightly high angle view, the sleeping "+("characters lie" if (n or 'Only these' in r['sc']) else "character lies")+" on the ground or bed with the whole body visible, big and clear in the frame, nobody is sitting up." 
        comp=("Composition: tight close-up on the hands and the object, anatomically correct human hands with five fingers." if hands else
              "Composition: wide shot with small readable figures, clear silhouettes, all with normal human proportions." if ('wide shot' in r['sc'].lower() or 'far away' in r['sc'].lower()) else
              ("Composition: back view of the character, facing away from the viewer, readable silhouette." if 'from the back' in r['sc'] else
              "Composition: the characters are big and clear in the frame, faces and upper bodies clearly visible, anatomically correct hands, background slightly softer than the characters." if n or 'Only these two' in r['sc'] or 'Only these three' in r['sc'] else
              "Composition: the character is big and clear in the frame, face and upper body clearly visible, anatomically correct hands, background slightly softer than the character."))
        who=(GROUP.format(n=n) if n else (" Only one person in the scene. "+("She" if fem else "He")+" is completely alone, nobody else around, no crowd." if alone else ""))
        grp=GROUP.format(n=n) if n else ''
        if n and asleep and not awake: grp=grp.replace("clear simple cartoon human faces with big round white eyes","clear simple cartoon human faces with closed eyes").replace("slim upright bodies","slim bodies lying down on the ground").replace("Medium shot, the characters are big in the frame.","Slightly high angle shot, the characters lie side by side and are big in the frame.")
        if n and 'sleepy' in low: grp=grp.replace("clear simple cartoon human faces with big round white eyes","clear simple cartoon human faces with sleepy half-closed eyes")
        who=(grp if n else who)
        cam='' if n else camera(r['sc'],'P')
        if sleeping_all: comp=sleep_comp
        if sleeping_all and n: setting=''
        single = alone and not n
        tail = (("She" if fem else "He")+" is fully clothed, no nudity. No text, no letters, no watermark.") if single else ("All of them are fully clothed, no nudity. No text, no letters, no watermark." if (n or 'Only these' in r['sc']) else TAIL)
        p=f"{style} {cam}{sc}{sleepnote}{who} {setting} {L} {comp} {QUAL} {tail}"
    elif typ=='E':
        end=END_ROOM if loc in ('HOME','LAB','EGY') and not re.search(r'savanna|forest|river|city|village|valley',sc) else END_LAND
        if ANIMALS.search(sc): end=END_ANIM
        comp=("Composition: close-up with the main subject sharp in the center, soft blurred background." if 'close-up' in sc.lower() else
              "Composition: clear foreground, middle ground and background layers with one strong focal point.")
        if re.search(r'\b(asleep|sleeping)\b',sc.lower()) and not re.search(r'sleeping mat',sc.lower()) and ANIMALS.search(sc): sc=sc.rstrip('.')+', fast asleep with eyelids shut.'
        p=f"{NOFACE} {camera(r['sc'],'E')}{sc} {setting} {L} {comp} {end} {QUAL} {TAIL_NP}"
    else:
        p=f"{NOFACE} {camera(r['sc'],'C')}{sc} {END_CARD} Soft even studio light with a gentle shadow under the objects, objects large and clear, filling about half of the frame. High quality, crisp clean linework, clean professional illustration. {TAIL_NP}"
    if vid: p=p.replace(' High quality, crisp', VIDREADY+' High quality, crisp',1)
    return re.sub(r'\s+',' ',p).strip()
for r in rows: r['prompt']=build(r)
# voiceover
vo=[];zv=[]
for i,(title,idx) in enumerate(parts,1):
    body=' '.join(rows[j]['txt'] for j in idx)
    vo.append(f"{title}\n\n{body}\n"); zv.append(f"===== ЧАСТЬ {i} =====\n{body}\n")
open(OUT+'/voiceover_EN.txt','w',encoding='utf-8').write('\n'.join(vo))
open(OUT+'/ОЗВУЧКА_по_частям.txt','w',encoding='utf-8').write('\n'.join(zv))
# shotpos
t=open(OUT+'/voiceover_EN.txt',encoding='utf-8').read().split('PART 1',1)[1].split('\n',1)[1]
t=re.sub(r'^PART .*$','',t,flags=re.M); W=norm(t)
pos=[];c=0
for r in rows:
    pos.append(c); c+=len(norm(r['txt']))
assert c==len(W),(c,len(W))
for r,p in zip(rows,pos): assert W[p:p+len(norm(r['txt']))]==norm(r['txt'])
sp={'W':W,'pos':[[i+1,p] for i,p in enumerate(pos)]}
json.dump(sp,open(OUT+'/shotpos.json','w'));json.dump(sp,open(OUT+'/Picker/.shotpos.json','w'))
dur=[(b-a)/162*60 for a,b in zip(pos,pos[1:]+[len(W)])]
# prompts + storyboard
open(OUT+'/prompts.txt','w',encoding='utf-8').write('\n'.join(f"shot_{i+1:03d}|{r['prompt']}" for i,r in enumerate(rows))+'\n')
LOCN={'CAMP':'стоянка','CARD':'карточка','SAV':'саванна','HOME':'дом YOU','LAB':'музей/лаборатория','FOR':'лес','CAVE':'пещера','ROCK':'скальный навес','RIV':'река','MTN':'горы','STP':'степь','VILL':'средневековая деревня','SEA':'берег моря','EGY':'Египет','SWP':'болото'}
sb=[];t0=0
for i,(r,d) in enumerate(zip(rows,dur)):
    sb.append(f"shot_{i+1:03d} | {LOCN[r['loc']]} | {t0:6.1f}s +{d:.1f}s | \"{r['txt']}\"\n    {r['prompt']}\n"); t0+=d
open(OUT+'/storyboard.txt','w',encoding='utf-8').write('\n'.join(sb))
# checks
BAN=['ice age','a group of','apes','hairy','furry','drinking','question mark','shaped like','symbol','painting of','young prehistoric man','caveman','cavemen','primitive','wild man','neanderthal','monkey']
bad=[]
for i,r in enumerate(rows):
    pl=r['prompt'].lower()
    for b in BAN:
        if b in pl: bad.append((i+1,b))
    if re.search(r'(?<!two )(?<!three )(?<!hunter-gatherers )\bpeople\b',pl): bad.append((i+1,'people'))
    if '{' in r['prompt']: bad.append((i+1,'tag'))
    if r['typ']!='P' and re.search(r'\b(eyes?|faces?|mouths?|everyone|people)\b',pl): bad.append((i+1,'eyes/face in no-people shot'))
    if len(r['prompt'].split())>260: bad.append((i+1,'long %d'%len(r['prompt'].split())))
dups=[k for k,v in collections.Counter(r['sc'] for r in rows).items() if v>1]
loc=collections.Counter(LOCN[r['loc']] for r in rows)
words=len(W); chars=sum(len(r['txt'])+1 for r in rows)
print('shots',len(rows),'words',words,'chars',chars,'min %.1f'%(words/162),'avg %.2f max %.1f'%(sum(dur)/len(dur),max(dur)))
print('over5:',[(i+1,round(d,1)) for i,d in enumerate(dur) if d>5])
print('bad:',bad); print('dups:',dups)
for k,v in loc.most_common(): print(f'  {k}: {v} ({100*v/len(rows):.0f}%)')
consec=[i+1 for i in range(1,len(rows)) if rows[i]['sc']==rows[i-1]['sc']]
print('consecutive dup',consec); L=[len(r['prompt'].split()) for r in rows]; print('prompt words min/avg/max',min(L),sum(L)//len(L),max(L)); print('He/She check',[i+1 for i,r in enumerate(rows) if ('woman' in r['sc'] or '{SCI1}' in r['sc'][:7] or '{GRANNY}' in r['sc'][:9] or '{OLDW}' in r['sc'][:7]) and ' He is completely' in r['prompt']])
json.dump({'loc':loc.most_common(),'words':words,'shots':len(rows),'min':words/162},open('summary.json','w'),ensure_ascii=False)
