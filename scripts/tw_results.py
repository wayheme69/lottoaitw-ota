#!/usr/bin/env python3
"""tw_results.py — robot LOTTO AI TW : derniers tirages officiels du 威力彩 et du 大樂透 (API de 台灣彩券),
avec le vrai gain par billet et le nombre de gagnants de chaque rang, le prochain tirage et le prochain jackpot.
Écrit tw_results.json (lu par l'app). Aucun tirage inventé : si l'API ne répond pas, le fichier n'est pas modifié."""
import json, sys, urllib.request
from datetime import date

API = "https://api.taiwanlottery.com/TLCAPIWeB/Lottery"
KEEP = 30
GAMES = {
    "superlotto638": ("SuperLotto638Result", "superLotto638Res", 5134, 38, 8, False, [
        ("6+1", "super638JackpotAssign"), ("6", "super638SecondAssign"), ("5+1", "super638ThirdAssign"),
        ("5", "super638FourthAssign"), ("4+1", "super638FifthAssign"), ("4", "super638SixthAssign"),
        ("3+1", "super638SeventhAssign"), ("2+1", "super638EighthAssign"), ("3", "super638NinthAssign"),
        ("1+1", "super638NormalAssign")]),
    "lotto649": ("Lotto649Result", "lotto649Res", 5118, 49, 49, True, [
        ("6", "jackpotAssign"), ("5+1", "secondAssign"), ("5", "thirdAssign"), ("4+1", "fourthAssign"),
        ("4", "fifthAssign"), ("3+1", "sixthAssign"), ("2+1", "seventhAssign"), ("3", "normalAssign")]),
}

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (LOTTO AI TW results bot)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.load(r)
    if d.get("rtCode") != 0: raise RuntimeError(f"{url}: rtCode {d.get('rtCode')} {d.get('rtMsg')}")
    return d["content"]

def months_back(n):
    y, m = date.today().year, date.today().month
    for _ in range(n):
        yield f"{y:04d}-{m:02d}"
        m -= 1
        if m == 0: y, m = y - 1, 12

def draws(key):
    path, res, _, pool, bpool, same, tiers = GAMES[key]
    out = {}
    for month in months_back(5):
        for x in get(f"{API}/{path}?period&month={month}&pageNum=1&pageSize=50").get(res) or []:
            nums = x["drawNumberSize"]
            main, bonus = sorted(nums[:6]), nums[6:7]
            assert len(nums) == 7 and len(set(main)) == 6 and all(1 <= v <= pool for v in main), x
            assert 1 <= bonus[0] <= bpool and (not same or bonus[0] not in main), x
            payouts, winners = {}, {}
            for k, f in tiers:
                a = x.get(f) or {}
                winners[k] = a.get("winnerCount")
                payouts[k] = a.get("perPrize") if (a.get("winnerCount") or 0) > 0 and (a.get("perPrize") or 0) > 0 else None
            published = sum(w or 0 for w in winners.values()) > 0
            out[x["period"]] = {"date": x["lotteryDate"][:10], "draw": x["period"], "numbers": main, "bonus": bonus,
                                "payouts": payouts if published else None, "winners": winners if published else None}
        if len(out) >= KEEP: break
    rows = sorted(out.values(), key=lambda d: (d["date"], d["draw"]), reverse=True)[:KEEP]
    assert rows, f"{key}: aucun tirage"
    return rows

def main():
    feed = {k: draws(k) for k in GAMES}
    nxt = {}
    try:
        nd = {x["gameCode"]: x for x in get(f"{API}/NextDrawDate")["nextDrawDateList"]}
        jp = {x["gameCode"]: x for x in get(f"{API}/Jackpot")["jackpotList"]}
        for k, g in GAMES.items():
            code = g[2]; d = nd.get(code, {}).get("drawDate") or ""
            j = jp.get(code, {})
            nxt[k] = {"date": f"{d[:4]}-{d[4:6]}-{d[6:8]}" if len(d) >= 8 else None,
                      "jackpot": float(int(j["jackpot"])) if j.get("isShow") and (j.get("jackpot") or "").isdigit() else None}
    except Exception as e:
        print("next/jackpot indisponibles :", e, file=sys.stderr)
    feed["next"] = nxt
    with open("tw_results.json", "w", encoding="utf-8") as f:
        json.dump(feed, f, ensure_ascii=False, indent=1)
    for k in GAMES: print(k, len(feed[k]), feed[k][0]["date"], feed[k][0]["numbers"], feed[k][0]["bonus"], file=sys.stderr)
    print("next", nxt, file=sys.stderr)

if __name__ == "__main__":
    main()
