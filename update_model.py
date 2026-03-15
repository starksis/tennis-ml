# update_model.py — запускается автоматически каждую неделю
import pandas as pd
import numpy as np
import glob
import json
import joblib
import os
from datetime import datetime

print(f"🔄 Обновление начато: {datetime.now()}")

# ============================================================
# 1. ЗАГРУЗКА ДАННЫХ
# ============================================================
def load_tour(pattern, tour_name, start_year=1985):
    frames = []
    for f in sorted(glob.glob(pattern)):
        try:
            basename = f.split('_')[-1].replace('.csv', '')
            digits   = ''.join(filter(str.isdigit, basename))
            if not digits or int(digits) < start_year:
                continue
            tmp = pd.read_csv(f, low_memory=False)
            tmp['tour'] = tour_name
            frames.append(tmp)
        except:
            continue
    return pd.concat(frames, ignore_index=True)

atp = load_tour("tennis_atp/atp_matches_*.csv", "ATP")
wta = load_tour("tennis_wta/wta_matches_*.csv", "WTA")
df  = pd.concat([atp, wta], ignore_index=True)

df['tourney_date'] = pd.to_datetime(
    df['tourney_date'].fillna(0).astype(int).astype(str),
    format='%Y%m%d', errors='coerce'
)
df = df.dropna(subset=['tourney_date'])
df = df.sort_values('tourney_date').reset_index(drop=True)
print(f"✅ Загружено матчей: {len(df):,}")

# ============================================================
# 2. ELO
# ============================================================
elo_general = {}
elo_surface = {}
K = 32

for row in df[['winner_name','loser_name','surface']].itertuples():
    w = row.winner_name
    l = row.loser_name
    s = row.surface if row.surface in ('Hard','Clay','Grass','Carpet') else 'Hard'

    for p in [w, l]:
        if p not in elo_general:
            elo_general[p] = 1500.0
        if p not in elo_surface:
            elo_surface[p] = {'Hard':1500.0,'Clay':1500.0,
                              'Grass':1500.0,'Carpet':1500.0}

    ew  = elo_general[w]
    el  = elo_general[l]
    ews = elo_surface[w][s]
    els = elo_surface[l][s]

    exp_w = 1 / (1 + 10 ** ((el - ew) / 400))
    elo_general[w] = ew + K * (1 - exp_w)
    elo_general[l] = el + K * (0 - (1 - exp_w))

    exp_ws = 1 / (1 + 10 ** ((els - ews) / 400))
    elo_surface[w][s] = ews + K * (1 - exp_ws)
    elo_surface[l][s] = els + K * (0 - (1 - exp_ws))

# ============================================================
# 3. ИСТОРИЯ ИГРОКОВ
# ============================================================
player_history = {}
h2h_records    = {}

for row in df[['winner_name','loser_name','surface']].itertuples():
    w = row.winner_name
    l = row.loser_name
    s = str(row.surface)

    for player, won in [(w, 1), (l, 0)]:
        if player not in player_history:
            player_history[player] = []
        player_history[player].append({
            'won':  won,
            'surf': s,
            'opp_elo': elo_general.get(l if player==w else w, 1500)
        })
        # Держим только последние 50 матчей — экономим память
        if len(player_history[player]) > 50:
            player_history[player] = player_history[player][-50:]

    pair = f"{min(w,l)}||{max(w,l)}"
    if pair not in h2h_records:
        h2h_records[pair] = []
    h2h_records[pair].append({'winner': w})

print(f"✅ Игроков в базе: {len(player_history):,}")
print(f"✅ H2H пар: {len(h2h_records):,}")

# ============================================================
# 4. СОХРАНЯЕМ СНАПШОТ В JSON (для GitHub)
# ============================================================

# Топ-200 игроков по ELO — сохраняем в JSON
top200 = sorted(elo_general.items(), key=lambda x: x[1], reverse=True)[:200]

snapshot = {
    'updated_at': datetime.now().isoformat(),
    'total_matches': len(df),
    'top200_elo': {p: round(e, 1) for p, e in top200},
    'elo_surface': {
        p: {s: round(v, 1) for s, v in surf.items()}
        for p, surf in elo_surface.items()
        if p in dict(top200)
    }
}

with open('elo_snapshot.json', 'w') as f:
    json.dump(snapshot, f, indent=2, ensure_ascii=False)

print(f"✅ ELO snapshot сохранён")

# ============================================================
# 5. СОХРАНЯЕМ PKL ДЛЯ KAGGLE
# ============================================================
joblib.dump(elo_general,   'elo_general.pkl')
joblib.dump(elo_surface,   'elo_surface.pkl')
joblib.dump(player_history,'player_history.pkl')
joblib.dump(h2h_records,   'h2h_records.pkl')

print(f"✅ PKL файлы сохранены")

# Топ-10
top10 = top200[:10]
print(f"\n🏆 Топ-10 ELO на {datetime.now().strftime('%Y-%m-%d')}:")
for i, (p, e) in enumerate(top10, 1):
    print(f"  {i:2}. {p:<30} {e:.0f}")

print(f"\n✅ Обновление завершено!")
```

---

## Шаг 4 — Загрузи файлы в репозиторий

В GitHub репозитории `tennis-ml` создай:
```
tennis-ml/
├── .github/
│   └── workflows/
│       └── update.yml
├── update_model.py
└── elo_snapshot.json  (создастся автоматически)
