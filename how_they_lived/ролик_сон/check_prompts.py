# -*- coding: utf-8 -*-
"""
Проверка prompts.txt ДО генерации картинок (How They Lived, Z-Image-Turbo).
Запуск:  python check_prompts.py prompts.txt [shotpos.json]
Каждое правило — ошибка, которую мы уже реально видели на картинках.
ОШИБКА = точно испортит кадр, ВНИМАНИЕ = риск, стоит посмотреть.
"""
import re, sys, json, collections

CAVE = "a grown adult prehistoric man in his mid 30s with a mature masculine face, a short thick dark brown beard covering his jaw, messy shoulder-length dark brown hair, a ragged brown fur tunic, barefoot"
YOU = "a modern man in his late 20s with short messy brown hair and a plain white t-shirt"
ROUND_EYES = "big round white eyes"
BANNED = ["ice age", "a group of", "apes", "monkey", "hairy", "furry", "drinking", "question mark",
          "shaped like", "symbol", "painting of", "young prehistoric man", "caveman", "cavemen",
          "primitive", "wild man", "neanderthal", "beast", "ape-like"]
TINY = r"\b(bugs?|bed bugs?|ants?|larvae|fleas?|lice|louse|ticks?|mosquito(es)?|insects?|beetles?)\b"
SLEEP = r"\b(asleep|sleeping|sleeps|deep sleep|in his sleep|in her sleep)\b"
AWAKE = r"awake|eyes open|eyes wide open|one eye half open|turning over|poking|stretching|whispering|talking|yawning"
TEXTRISK = r"\b(chart|charts|graph|diagram|map|sign|poster|newspaper|label|screen showing|page of|calendar|years\")"

def scene(p):
    i = p.find("storyboard frame.")
    return p[i + 17:] if i >= 0 else p

def check(prompts, shotpos=None):
    issues = []
    def add(n, lvl, msg): issues.append((n, lvl, msg))
    prev = None
    for n, p in prompts:
        low = p.lower(); sc = scene(p); scl = sc.lower()
        has_people = ROUND_EYES in low or "human faces" in low or "the character is" in scl or "two characters" in scl or "hunter-gatherers" in scl and "nobody in it" not in scl
        empty = "nobody in it" in low or "plain warm beige background" in low or "only animals in the scene" in low
        single = "only one person in the scene" in low
        group = "only these two" in low or "only these three" in low or "two characters" in scl
        nw = len(p.split())
        # 1 запрещённые слова
        for b in BANNED:
            if re.search(r"\b" + re.escape(b) + r"\b", low) or (b == "apes" and "apes" in low):
                add(n, "ОШИБКА", f'запрещённое слово "{b}"')
        if re.search(r"\bpeople\b", scl) and not re.search(r"\b(two|three)\b[^.]{0,40}\bpeople\b", scl):
            add(n, "ВНИМАНИЕ", '"people" без числа — модель рисует толпу')
        # 2 пустые сцены и карточки: никаких глаз/лиц/людей
        if empty:
            for w in ["eyes", "eye", "face", "faces", "mouth", "everyone", "people", "person"]:
                if re.search(r"\b" + w + r"\b", scl):
                    add(n, "ОШИБКА", f'в кадре без людей слово "{w}" — появятся лица/глаза или люди')
        # 3 один человек + Everyone
        if single and "everyone" in low:
            add(n, "ОШИБКА", '"Everyone" в кадре с одним человеком — на фоне появляется толпа')
        # 4 пол
        if re.search(r"\b(woman|grandmother|she)\b", scl) and re.search(r"(?<!s)\bhe is completely alone", low) and not re.search(r"\bman\b(?! scientist)", scl.replace("woman", "")):
            add(n, "ОШИБКА", 'женщина, но написано "He is completely alone"')
        if re.search(r"\b(she|he) is a (man|woman) (scientist|archaeologist|anthropologist)", scl):
            add(n, "ОШИБКА", "два персонажа склеены в одно предложение — будет мутант")
        # 5 спящие
        if re.search(SLEEP, scl) and not re.search(r"sleeping mat|sleeping mats", scl) and has_people and not empty:
            awake = re.search(AWAKE, scl)
            if not awake and ROUND_EYES in low:
                add(n, "ОШИБКА", "персонаж спит, но в стиле стоят круглые открытые глаза")
            if not awake and group and "upright" in low:
                add(n, "ОШИБКА", 'спящая группа с "upright bodies" — модель посадит их')
            if awake and "the sleeping person has eyes" not in low:
                add(n, "ВНИМАНИЕ", "один спит, другой нет — не указано, у кого закрыты глаза")
        if re.search(r"squeezed shut|half closed|yawning", scl) and ROUND_EYES in low and not re.search(r"one yawning", scl):
            add(n, "ОШИБКА", "глаза должны быть закрыты/прищурены, а в стиле круглые глаза")
        # 6 руки крупно
        if re.search(r"close-up of (the )?hands|hands of", scl) and ("only the hands are visible" not in scl):
            add(n, "ОШИБКА", 'крупный план рук без "only the hands are visible" — нарисует всю фигуру')
        if "only the hands are visible" in scl and ("the character is" in scl or CAVE[:40] in sc):
            add(n, "ВНИМАНИЕ", "в крупном плане рук полное описание героя — может нарисовать всю фигуру")
        # 7 мелкие существа
        if re.search(TINY, scl) and "macro" not in scl and "cloud of" not in scl and "only animals" in low:
            add(n, "ВНИМАНИЕ", 'мелкие существа без "macro close-up ... clearly visible" — их не будет видно')
        # 8 вид со спины
        if re.search(r"seen from behind|from behind", scl) and "back of his head" not in scl and "back of her head" not in scl:
            add(n, "ОШИБКА", '"seen from behind" модель игнорирует — нужно "we see his back and the back of his head"')
        # 9 свет
        if "firelight" in low and not re.search(r"fire|flame|ember|hearth|candle|lantern|coals|torch", scl.split("lighting:")[0]):
            add(n, "ВНИМАНИЕ", "свет от костра, но костра в сцене нет")
        if "midday sunlight" in low and not re.search(r"\b(noon|midday|hot|heat)\b", scl.split("lighting:")[0]):
            add(n, "ОШИБКА", "полуденный свет без причины (ловушка: слово shot содержит hot)")
        if "window" in low and re.search(r"excavation|cave|rock shelter", scl) and "lab" not in scl.split("lighting:")[0]:
            add(n, "ВНИМАНИЕ", "окно в пещерной сцене")
        # 10 текст на картинке
        if re.search(TEXTRISK, scl) and not re.search(r"\bonly\b|no writing|simple colorful|bars only", scl):
            add(n, "ВНИМАНИЕ", "экран/график/табличка — модель напишет кашу из букв")
        if re.search(r'"[^"]+"', sc):
            add(n, "ВНИМАНИЕ", "текст в кавычках — будет надпись на картинке")
        # 11 отрицания (модель рисует то, что упомянуто)
        for m in re.finditer(r"\bno (face|eyes|shelter|walls|people|animals|fire|trees)\b", scl):
            add(n, "ВНИМАНИЕ", f'отрицание "{m.group(0)}" — лучше описать, что видно')
        if re.search(r"glowing eyes|eyes glow|eyes of animals", scl):
            add(n, "ОШИБКА", "светящиеся глаза — появятся глаза на камнях; лучше силуэт зверя")
        # 12 обезьяны/массовка
        if re.search(r"early human|ancestor|homo erectus", scl) and "normal human face" not in scl:
            add(n, "ОШИБКА", 'ранний предок без "normal human face" — выйдет обезьяна')
        if re.search(r"(two|three) adult hunter-gatherers", scl) and "anatomically modern humans" not in low:
            add(n, "ОШИБКА", 'группа без "anatomically modern humans with normal human proportions"')
        if re.search(r"\bcrowd of|\bmany people|\bgroup of people|\btribe\b", scl) and "far away" not in scl:
            add(n, "ВНИМАНИЕ", "толпа крупно — лица поплывут; показывать только издалека")
        # 13 герои
        if "prehistoric man in his" in low and CAVE not in p:
            add(n, "ОШИБКА", "описание CAVE не дословное — герой будет меняться")
        if "modern man in his" in low and YOU not in p:
            add(n, "ОШИБКА", "описание YOU не дословное")
        # 14 длина и повторы
        if nw > 260: add(n, "ВНИМАНИЕ", f"промпт длинный ({nw} слов)")
        if nw < 60: add(n, "ВНИМАНИЕ", f"промпт короткий ({nw} слов)")
        if prev and scene(prev).split("Lighting:")[0] == sc.split("Lighting:")[0]: add(n, "ОШИБКА", "одинаковый кадр подряд")
        prev = p
    # 15 длительность кадров
    if shotpos:
        W = shotpos["W"]; P = [p for _, p in shotpos["pos"]] + [len(W)]
        for i, (a, b) in enumerate(zip(P, P[1:])):
            if not 6 <= b - a <= 8:
                add(f"shot_{i+1:03d}", "ОШИБКА", f"{b-a} слов — не 2–3 секунды (нужно 6–8 слов)")
    return issues

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "prompts.txt"
    prompts = [l.rstrip("\n").split("|", 1) for l in open(path, encoding="utf-8") if "|" in l]
    sp = json.load(open(sys.argv[2], encoding="utf-8")) if len(sys.argv) > 2 else None
    iss = check(prompts, sp)
    c = collections.Counter(l for _, l, _ in iss)
    print(f"Кадров: {len(prompts)}   ОШИБОК: {c['ОШИБКА']}   ВНИМАНИЕ: {c['ВНИМАНИЕ']}")
    for n, l, m in iss: print(f"{n}  {l}: {m}")
    if not iss: print("Всё чисто.")
