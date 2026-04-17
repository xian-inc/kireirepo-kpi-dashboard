# 予約解放済みクリニック 営業ダッシュボード

キレイレポ予約解放済み121院の営業活動向けKPIダッシュボード。

## 機能

- 📊 全期間/月別でSS・予約・予約率を一覧表示
- 🟦 ランディング / 🟩 経由 / 🟧 予約 / 🟪 メニュー の色分け
- 🔍 クリニック詳細（月別タブ切替）
- 💡 営業チャンス（SSあるのに予約0の院TOP20）
- 🎯 掲載リストページ経由状況
- 🍽 人気メニュー月別SS・予約・CTR

## データソース

- BigQuery GA4（非サンプリング全件）
- `replica_kireirepo_production`（本番DBレプリカ）

## 更新頻度

毎日朝9時に自動更新（ローカルcron → GitHub push → Streamlit Cloud自動再デプロイ）

## ローカルで起動

```
pip install -r requirements.txt
streamlit run streamlit_app.py
```
