#!/bin/bash
# 毎日9:07に実行されるデータ更新スクリプト
# 1. 親ディレクトリの最新JSONを data/ にコピー
# 2. 121院マスタも Redash から再取得
# 3. git commit + push → Streamlit Cloud が自動再デプロイ

set -e
cd "/Users/onukiayana/Desktop/キレイレポ/streamlit-dashboard"

# JSONデータコピー
cp ../_bq_121院_detail_ss.json data/
cp ../_bq_121院_rsv.json data/
cp ../_bq_121院_list_routes.json data/
cp ../_bq_121院_list_routes_monthly.json data/
cp ../_bq_list_page_ss.json data/
cp ../_bq_list_page_ss_monthly.json data/
cp ../_bq_sp_menu_count.json data/
cp ../_bq_exclusive_count.json data/
cp ../_bq_menu_monthly.json data/
cp ../_bq_menu_names.json data/

# 121院マスタを最新化
/usr/bin/python3 <<'PY'
import requests, json
r = requests.get("https://redash.kireireport.com/api/query_results/202938",
    headers={"Authorization": "Key KUWtjbr8rLNs0DPmwwKJUY3ktYSMt0LG6J0kLNA8"}, timeout=30)
stores = r.json()["query_result"]["data"]["rows"]
with open("/Users/onukiayana/Desktop/キレイレポ/streamlit-dashboard/data/_stores_master.json", "w") as f:
    json.dump(stores, f, ensure_ascii=False, indent=2)
print(f"121院マスタ: {len(stores)}院")
PY

# Git push
git add data/
if git diff --cached --quiet; then
    echo "変更なし、pushスキップ"
else
    git commit -m "Update data $(date +'%Y-%m-%d %H:%M')"
    git push origin main
    echo "Push完了: $(date)"
fi
