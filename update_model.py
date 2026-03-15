import pandas as pd
import numpy as np
import glob
import json
from datetime import datetime

print(f"Start: {datetime.now()}")

def load_tour(pattern, tour_name, start_year=2000):
    frames = []
    for f in sorted(glob.glob(pattern)):
        try:
            basename = f.split('_')[-1].replace('.csv','')
            digits = ''.join(filter(str.isdigit, basename))
            if not digits or int(digits) < start_year:
                continue
            tmp = pd.read_csv(f, low_memory=False)
            tmp['tour'] = tour_name
            frames.append(tmp)
        except Exception as e:
            print(f"Skip {f}: {e}")
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)

atp = load_tour("tennis_atp/atp_matches_*.csv", "ATP")
wta = load_tour("tennis_wta/wta_matches_*.csv", "WTA")

if len(atp) == 0 and len(wta) == 0:
    print("ERROR: no data")
    exit(1)

df = pd.concat([atp, wta], ignore_index=True)
df['tourney_date'] = pd.to_datetime(
    df['tourney_date'].fillna(0).astype(int).astype(str),
    format='%Y%m%d', errors='coerce'
)
df = df.dropna(subset=['tourney_date'])
df = df.sort_values('tourney_date').reset_index(drop=True)
print(f"Matches: {len(df)}")

elo = {}
K = 32
for row in df[['winner_name','loser_name']].itertuples():
    w = str(row.winner_name)
    l = str(row.loser_name)
    if w not in elo: elo[w] = 1500.0
    if l not in elo: elo[l] = 1500.0
    exp_w   = 1 / (1 + 10**((elo[l]-elo[w])/400))
    elo[w] += K * (1 - exp_w)
    elo[l] += K * (0 - (1 - exp_w))

top200 = sorted(elo.items(), key=lambda x: x[1], reverse=True)[:200]
print(f"ELO done: {len(elo)} players")

for i, (p, e) in enumerate(top200[:10], 1):
    print(f"{i}. {p} {e:.0f}")

snapshot = {
    'updated_at': datetime.now().isoformat(),
    'total_matches': len(df),
    'top200_elo': {p: round(e,1) for p,e in top200}
}
import requests
import io

def load_2025_odds():
    sources = [
        "http://www.tennis-data.co.uk/2025/2025.xlsx",
        "http://www.tennis-data.co.uk/2025w/2025.xlsx"
    ]
    frames = []
    for url in sources:
        try:
            r = pd.read_excel(url)
            frames.append(r)
            print(f"OK: {url} — {len(r)} матчей")
        except Exception as e:
            print(f"Skip: {url}")
    return pd.concat(frames) if frames else pd.DataFrame()

fresh = load_2025_odds()
print(f"Свежих матчей 2025: {len(fresh)}")
```

---

## Реальная картина по датам
```
tennis_atp/wta GitHub    до конца 2024  ✅
tennis-data.co.uk        2025 частично  ⚠️
ultimatetennisstatistics  2025 полностью ✅ (платно)
sofascore/flashscore      реальное время ✅ (scraping)

with open('elo_snapshot.json', 'w') as f:
    json.dump(snapshot, f, indent=2)

print("Done!")
