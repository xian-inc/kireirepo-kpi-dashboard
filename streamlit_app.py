"""
予約解放済み121院 営業ダッシュボード
起動: streamlit run streamlit_app.py
"""
import warnings; warnings.filterwarnings("ignore")
import os
import streamlit as st
import pandas as pd
import json
import re
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# データディレクトリ: 通常は同階層の `data/`。環境変数で上書き可能
BASE = Path(os.environ.get("DATA_DIR", Path(__file__).parent / "data"))

st.set_page_config(
    page_title="予約解放済みクリニック ダッシュボード",
    page_icon="🏥",
    layout="wide",
)

# ======== データロード ========
@st.cache_data(ttl=300)
def load_data():
    data = {}
    files = {
        "ss": "_bq_121院_detail_ss.json",
        "rsv": "_bq_121院_rsv.json",
        "sp_menu": "_bq_sp_menu_count.json",
        "exclusive": "_bq_exclusive_count.json",
        "routes": "_bq_121院_list_routes.json",
        "routes_monthly": "_bq_121院_list_routes_monthly.json",
        "list_ss": "_bq_list_page_ss.json",
        "list_ss_monthly": "_bq_list_page_ss_monthly.json",
        "menu_monthly": "_bq_menu_monthly.json",
        "menu_names": "_bq_menu_names.json",
    }
    for key, fname in files.items():
        with open(BASE / fname) as f:
            data[key] = json.load(f)
    return data

@st.cache_data(ttl=300)
def load_stores():
    """121院マスタをJSONから読み込む（cronで事前保存されている）"""
    master_file = BASE / "_stores_master.json"
    if master_file.exists():
        with open(master_file) as f:
            return json.load(f)
    # フォールバック: Redash API（Secretsに REDASH_API_KEY が設定されてる場合のみ）
    api_key = None
    try:
        api_key = st.secrets.get("REDASH_API_KEY")
    except Exception:
        pass
    if not api_key:
        api_key = os.environ.get("REDASH_API_KEY", "")
    if not api_key:
        return []
    import requests
    for _ in range(3):
        try:
            r = requests.get(
                "https://redash.kireireport.com/api/query_results/202938",
                headers={"Authorization": f"Key {api_key}"},
                timeout=30
            )
            return r.json()["query_result"]["data"]["rows"]
        except Exception:
            pass
    return []

TC_JP = {"twofold":"二重","skin":"美容皮膚科","nose":"鼻","lip":"唇","eye":"目元","forehead":"額",
    "laser":"レーザー","fat":"脂肪","liposuction":"脂肪吸引","breast":"豊胸","artmake":"アートメイク",
    "earrings":"ピアス","hair":"薄毛・育毛","removal":"脱毛","bust":"バスト","neck":"首","face":"顔",
    "body":"ボディ","cheek":"頬","mouth":"口","chin":"あご","mole":"ホクロ","pigment":"シミ",
    "wrinkle":"しわ","pore":"毛穴","acne":"ニキビ","internalmedicine":"内科","dental":"歯科",
    "others":"その他","slimming":"ダイエット"}
TREAT_JP = {"visia":"肌診断VISIA","mofius":"モフィウス8","lumeca":"ルメッカ","piercingears":"ピアス",
    "sofwave":"ソフウェーブ","xerf":"XERF","hifu":"HIFU","ultraformer":"ウルセラ",
    "whitestoneinjection":"白玉注射","platysmabotoxinjection":"プラチスマボトックス",
    "mesonaj":"メソナJ","skinbotox":"スキンボトックス","foreheadbotoxinjection":"額ボトックス",
    "eyebrowartmakeup":"眉アートメイク","artmakeupremoval":"アートメイク除去",
    "hayfeverbotox":"花粉症ボトックス","mounjaro":"マンジャロ","rybelsus":"リベルサス",
    "snecosinjection":"スネコス注射","hydrafacial":"ハイドラフェイシャル","picospot":"ピコスポット",
    "massagepeel":"マッサージピール","inmode":"インモード","inmoode":"インモード","peeling":"ピーリング",
    "botoxinjection":"ボトックス注射","skintyte":"スキンタイト","emface":"エムフェイス","emsella":"エムセラ",
    "milanoripeel":"ミラノリピール","onda":"オンダリフト","potenza":"ポテンツァ","pico":"ピコレーザー",
    "picolaser":"ピコレーザー","picotoning":"ピコトーニング","dermapen":"ダーマペン","shirokojun":"白玉点滴",
    "iv":"点滴","carboxy":"カーボキシー","aquafull":"アクアフル","yvoire":"イボワール","juvederm":"ジュビダーム",
    "restylane":"レスチレン","boletas":"ボリタス","skinbooster":"スキンブースター","rejuran":"リジュラン",
    "placenta":"プラセンタ","glutathione":"グルタチオン","forma":"フォーマ","morpheus":"モーフィアス",
    "pcool":"Pクール","sfphecia":"シルファーム","aqualyx":"アクアリクス","lipolysisshot":"脂肪溶解注射",
    "fraxel":"フラクセル","qswitch":"Qスイッチ","ultheraprime":"ウルセラプライム","thermaprime":"サーマプライム",
    "titanprime":"タイタンプライム","radiesse":"ラディエッセ","sculpt":"スカルプ","embeddedmethod":"埋没法",
    "doublefold":"二重埋没","incisioneyelid":"切開二重","ptosis":"眼瞼下垂","bleph":"二重整形",
    "eyelifting":"アイリフト","eyebags":"目の下のたるみ","darkcircles":"クマ取り","buccalfatremoval":"頬脂肪除去",
    "facelift":"フェイスリフト","threadlift":"糸リフト","hifulift":"HIFUリフト","foreheadlift":"額リフト",
    "nosejob":"鼻整形","nosetip":"鼻尖形成","liplift":"リップリフト","lipfiller":"リップフィラー",
    "aga":"AGA治療","pill":"ピル","diet":"ダイエット","saxenda":"サクセンダ","glp1":"GLP-1","wegovy":"ウゴービ",
    "bbl":"BBL","ipl":"IPL","redness":"赤ら顔","pigmentremoval":"シミ取り","liverspotremoval":"肝斑治療",
    "tranexamicacid":"トラネキサム酸","vitaminc":"ビタミンC","whitening":"美白","priceinjection":"プライス注射"}
# 都道府県
PREF_JP = {"tokyo":"東京","osaka":"大阪","kanagawa":"神奈川","chiba":"千葉","saitama":"埼玉",
    "aichi":"愛知","hyogo":"兵庫","kyoto":"京都","fukuoka":"福岡","hokkaido":"北海道","miyagi":"宮城",
    "niigata":"新潟","shizuoka":"静岡","hiroshima":"広島","okinawa":"沖縄","gunma":"群馬","tochigi":"栃木",
    "ibaraki":"茨城","nagano":"長野","yamanashi":"山梨","gifu":"岐阜","mie":"三重","shiga":"滋賀",
    "nara":"奈良","wakayama":"和歌山","okayama":"岡山","yamaguchi":"山口","ehime":"愛媛","kagawa":"香川",
    "tokushima":"徳島","kochi":"高知","oita":"大分","miyazaki":"宮崎","kagoshima":"鹿児島","kumamoto":"熊本",
    "saga":"佐賀","nagasaki":"長崎","fukushima":"福島","yamagata":"山形","iwate":"岩手","akita":"秋田",
    "aomori":"青森","ishikawa":"石川","toyama":"富山","fukui":"福井","tottori":"鳥取","shimane":"島根"}

def cat_name(path):
    if not path: return ""
    # /tc-category/t-treatment/p-pref
    m = re.search(r'/tc-([^/]+)(?:/t-([^/]+))?(?:/p-([^/]+))?', str(path))
    if m:
        c = TC_JP.get(m.group(1), m.group(1))
        t = TREAT_JP.get(m.group(2), m.group(2)) if m.group(2) else ""
        p = PREF_JP.get(m.group(3), m.group(3)) if m.group(3) else ""
        base = f"{c}＞{t}" if t else c
        return f"{base}（{p}）" if p else base
    m = re.search(r'/q-(\d+)(?:/p-([^/]+))?', str(path))
    if m:
        p = PREF_JP.get(m.group(2), m.group(2)) if m.group(2) else ""
        base = f"口コミまとめq-{m.group(1)}"
        return f"{base}（{p}）" if p else base
    return ""

# ======== データ準備 ========
data = load_data()
stores = load_stores()
store_map = {str(s["store_id"]): s["クリニック名"] for s in stores}
type_map = {str(s["store_id"]): s["予約方式"] for s in stores}

df_ss = pd.DataFrame(data["ss"])
df_rsv = pd.DataFrame(data["rsv"])
df_routes = pd.DataFrame(data["routes"])
df_routes_m = pd.DataFrame(data["routes_monthly"])
df_list_ss = pd.DataFrame(data["list_ss"])
df_list_ss_m = pd.DataFrame(data["list_ss_monthly"])

df_menu_m = pd.DataFrame(data["menu_monthly"])
df_names = pd.DataFrame(data["menu_names"]).drop_duplicates(subset=["id"])
df_names["menu_id"] = df_names["id"].astype(str)
df_menu_m = df_menu_m.merge(df_names[["menu_id","name","campaign_type"]], on="menu_id", how="left")
df_menu_m["name"] = df_menu_m["name"].fillna("(名前不明)")

MONTH_LABELS = {"202601":"1月", "202602":"2月", "202603":"3月", "202604":"4月"}

sp_map = {str(r["store_id"]): r["sp_menu_count"] for r in data["sp_menu"]}
exc_map = {str(r["store_id"]): r["exclusive_count"] for r in data["exclusive"]}
all_sids = sorted(set(str(s["store_id"]) for s in stores), key=lambda x: int(x))

# ======== スプシと同じ列構成の関数 ========
def build_summary(month_filter=None):
    """
    スプシと同じ列構成のサマリDataFrameを作る
    month_filter: "202601"〜"202604" または None（全期間）
    """
    # SS集計（visit_type別・チャネル別）
    if month_filter:
        ss_data = df_ss[df_ss["month"]==month_filter]
        rsv_data = df_rsv[df_rsv["month"]==month_filter]
    else:
        ss_data = df_ss
        rsv_data = df_rsv

    # visit_typeで分けて集計
    direct_ss_agg = ss_data[ss_data["visit_type"]=="direct_land"].groupby("store_id").agg(
        ランディング_合計=("ss","sum"),
        ランディング_検索=("organic_ss","sum"),
        ランディング_SNS=("social_ss","sum"),
        ランディング_直接=("direct_ss","sum"),
        ランディング_他サイト=("referral_ss","sum"),
    ).reset_index()
    via_ss_agg = ss_data[ss_data["visit_type"]=="via"].groupby("store_id").agg(
        経由_合計=("ss","sum"),
        経由_検索=("organic_ss","sum"),
        経由_SNS=("social_ss","sum"),
        経由_直接=("direct_ss","sum"),
        経由_他サイト=("referral_ss","sum"),
    ).reset_index()
    rsv_agg = rsv_data.groupby("store_id")["total_rsv"].sum().reset_index().rename(columns={"total_rsv":"予約数"})

    all_stores_df = pd.DataFrame({"store_id": all_sids})
    merged = all_stores_df.merge(direct_ss_agg, on="store_id", how="left").merge(via_ss_agg, on="store_id", how="left").merge(rsv_agg, on="store_id", how="left").fillna(0)

    ss_cols = ["ランディング_合計","ランディング_検索","ランディング_SNS","ランディング_直接","ランディング_他サイト",
                "経由_合計","経由_検索","経由_SNS","経由_直接","経由_他サイト","予約数"]
    for c in ss_cols:
        if c in merged.columns:
            merged[c] = merged[c].astype(int)
        else:
            merged[c] = 0

    merged["クリニック名"] = merged["store_id"].map(store_map)
    merged["予約方式"] = merged["store_id"].map(type_map)
    merged["合計SS"] = merged["ランディング_合計"] + merged["経由_合計"]
    merged["予約率(%)"] = (merged["予約数"]/merged["合計SS"]*100).round(2).where(merged["合計SS"]>0, 0)
    merged["sp-menu数"] = merged["store_id"].map(sp_map).fillna(0).astype(int)
    merged["キレイレポ限定数"] = merged["store_id"].map(exc_map).fillna(0).astype(int)

    return merged[[
        "store_id","クリニック名","予約方式","合計SS",
        "ランディング_合計","ランディング_検索","ランディング_SNS","ランディング_直接","ランディング_他サイト",
        "経由_合計","経由_検索","経由_SNS","経由_直接","経由_他サイト",
        "予約数","予約率(%)","sp-menu数","キレイレポ限定数"
    ]]

# ======== サイドバー ========
st.sidebar.title("🔍 フィルタ")
search_query = st.sidebar.text_input("🔍 検索（store_id または クリニック名）", "", placeholder="例: 86871 または ラフェ")
show_no_rsv = st.sidebar.checkbox("🔥 予約0のみ (営業チャンス)", value=False)
yoyaku_type = st.sidebar.selectbox("予約方式", ["全て", "rakumane_connected(即時予約)", "request_only(リクエスト予約)"])
sort_by = st.sidebar.selectbox("並び順", ["合計SS", "予約数", "予約率(%)", "クリニック名"])
sort_asc = st.sidebar.checkbox("昇順", value=False)

def filter_and_sort(df):
    out = df.copy()
    if search_query:
        q = search_query.strip()
        # store_id (数字のみ) または クリニック名 で部分一致
        mask_id = out["store_id"].astype(str).str.contains(q, case=False, na=False)
        mask_name = out["クリニック名"].str.contains(q, case=False, na=False)
        out = out[mask_id | mask_name]
    if show_no_rsv:
        out = out[(out["予約数"]==0) & (out["合計SS"]>0)]
    if yoyaku_type != "全て":
        y_val = "rakumane_connected" if "rakumane" in yoyaku_type else "request_only"
        out = out[out["予約方式"]==y_val]
    return out.sort_values(sort_by, ascending=sort_asc)

df_total = build_summary()
df_filtered_total = filter_and_sort(df_total)

st.sidebar.markdown("---")
# 「store_id｜クリニック名」形式で選択肢を作る
base_df = df_filtered_total if len(df_filtered_total) > 0 else df_total
clinic_options_labeled = [f"{r['store_id']}｜{r['クリニック名']}" for _, r in base_df.iterrows()]
selected_label = st.sidebar.selectbox("🏥 クリニック選択（詳細タブ用）", clinic_options_labeled, index=0 if clinic_options_labeled else None)
# "｜"で分割してクリニック名だけ取り出す
selected_clinic = selected_label.split("｜", 1)[1] if selected_label else None

# ======== メイン ========
st.title("🏥 予約解放済みクリニック 営業ダッシュボード")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📊 全期間合計", "📅 1月", "📅 2月", "📅 3月", "📅 4月", "🔍 クリニック詳細 / 💡営業チャンス"])

LANDING_SUB_COLS = ["ランディング_検索","ランディング_SNS","ランディング_直接","ランディング_他サイト"]
LANDING_TOTAL_COLS = ["ランディング_合計"]
VIA_SUB_COLS = ["経由_検索","経由_SNS","経由_直接","経由_他サイト"]
VIA_TOTAL_COLS = ["経由_合計"]
RSV_COLS = ["予約数","予約率(%)"]
MENU_COLS = ["sp-menu数","キレイレポ限定数"]
TOTAL_COLS = ["合計SS"]

def style_df(df):
    """合計系は大きく濃色で強調、カテゴリ別に色分け"""
    styles = pd.DataFrame("", index=df.index, columns=df.columns)
    # 🏆 合計SS（最重要）= 濃紺+白字+太字+大きめ
    for col in TOTAL_COLS:
        if col in df.columns:
            styles[col] = "background-color: #0D47A1; color: white; font-weight: 900; font-size: 15px; border: 2px solid #1F4E79"
    # ランディング_合計 = 青強調
    for col in LANDING_TOTAL_COLS:
        if col in df.columns:
            styles[col] = "background-color: #1976D2; color: white; font-weight: bold; font-size: 14px"
    # ランディング内訳 = 薄青
    for col in LANDING_SUB_COLS:
        if col in df.columns:
            styles[col] = "background-color: #D6E4F0; color: #0D47A1"
    # 経由_合計 = 緑強調
    for col in VIA_TOTAL_COLS:
        if col in df.columns:
            styles[col] = "background-color: #2E7D32; color: white; font-weight: bold; font-size: 14px"
    # 経由内訳 = 薄緑
    for col in VIA_SUB_COLS:
        if col in df.columns:
            styles[col] = "background-color: #E8F5E9; color: #1B5E20"
    # 予約数（合計扱い）= オレンジ強調
    for col in ["予約数"]:
        if col in df.columns:
            styles[col] = "background-color: #E65100; color: white; font-weight: bold; font-size: 14px"
    # 予約率(%)
    for col in ["予約率(%)"]:
        if col in df.columns:
            styles[col] = "background-color: #FFE0B2; color: #E65100; font-weight: bold"
    # メニュー = 紫
    for col in MENU_COLS:
        if col in df.columns:
            styles[col] = "background-color: #F3E5F5; color: #4A148C"
    return styles

def render_summary_tab(df_month, title):
    st.subheader(title)
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("合計SS", f"{df_month['合計SS'].sum():,}")
    with col2: st.metric("予約数", f"{df_month['予約数'].sum():,}")
    with col3:
        rate = df_month['予約数'].sum()/df_month['合計SS'].sum()*100 if df_month['合計SS'].sum()>0 else 0
        st.metric("平均予約率", f"{rate:.2f}%")
    with col4:
        no_rsv = len(df_month[(df_month['予約数']==0) & (df_month['合計SS']>0)])
        st.metric("予約0院数", f"{no_rsv}院")

    st.markdown("### 📋 クリニック一覧（🟦=ランディング / 🟩=経由 / 🟧=予約 / 🟪=メニュー）")
    styled = df_month.style.apply(style_df, axis=None).format({"予約率(%)": "{:.2f}%"})
    st.dataframe(styled, use_container_width=True, hide_index=True)

# ===== タブ1: 全期間合計 =====
with tab1:
    # 全体月別推移
    st.markdown("### 📈 全体 月別推移")
    monthly_all = []
    for m_ym, m_lbl in MONTH_LABELS.items():
        df_m = filter_and_sort(build_summary(m_ym))
        monthly_all.append({"月": m_lbl, "SS": int(df_m["合計SS"].sum()), "予約数": int(df_m["予約数"].sum())})
    df_monthly_all = pd.DataFrame(monthly_all)

    fig = go.Figure()
    fig.add_trace(go.Bar(x=df_monthly_all["月"], y=df_monthly_all["SS"], name="SS", marker_color="#1F4E79"))
    fig.add_trace(go.Scatter(x=df_monthly_all["月"], y=df_monthly_all["予約数"], name="予約数", yaxis="y2",
                            mode="lines+markers", marker_color="#E65100", line=dict(width=3)))
    fig.update_layout(yaxis=dict(title="SS"), yaxis2=dict(title="予約数", overlaying="y", side="right"),
                      hovermode="x unified", height=350)
    st.plotly_chart(fig, use_container_width=True)

    from datetime import datetime
    now_str = datetime.now().strftime("%Y/%-m/%-d %H時")
    render_summary_tab(df_filtered_total, f"📊 全期間合計（1/1〜{now_str}時点）")

# ===== タブ2-5: 月別 =====
for tab, month_ym, month_label in [(tab2,"202601","1月"), (tab3,"202602","2月"), (tab4,"202603","3月"), (tab5,"202604","4月")]:
    with tab:
        df_m = filter_and_sort(build_summary(month_ym))
        render_summary_tab(df_m, f"📅 {month_label}")

# ===== タブ6: クリニック詳細 + 営業チャンス =====
with tab6:
    # クリニック詳細
    if selected_clinic:
        sel_row = df_total[df_total["クリニック名"]==selected_clinic].iloc[0]
        sid = sel_row["store_id"]

        st.header(f"🏥 {selected_clinic}")
        st.caption(f"store_id: {sid}  /  予約方式: {sel_row['予約方式']}")

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("合計SS", f"{sel_row['合計SS']:,}")
        c2.metric("予約数", f"{sel_row['予約数']:,}")
        c3.metric("予約率", f"{sel_row['予約率(%)']:.2f}%")
        c4.metric("sp-menu", sel_row["sp-menu数"])
        c5.metric("キレイレポ限定", sel_row["キレイレポ限定数"])

        # 月別推移（全期間グラフ・最初に全体を見せる）
        st.markdown("### 📈 月別推移")
        monthly = []
        for m_ym, m_lbl in MONTH_LABELS.items():
            m_df = build_summary(m_ym)
            m_r = m_df[m_df["store_id"]==sid].iloc[0] if sid in m_df["store_id"].values else None
            monthly.append({
                "月": m_lbl,
                "SS": int(m_r["合計SS"]) if m_r is not None else 0,
                "予約数": int(m_r["予約数"]) if m_r is not None else 0,
            })
        df_m_clinic = pd.DataFrame(monthly)
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df_m_clinic["月"], y=df_m_clinic["SS"], name="SS", marker_color="#1F4E79"))
        fig.add_trace(go.Scatter(x=df_m_clinic["月"], y=df_m_clinic["予約数"], name="予約数", yaxis="y2",
                                mode="lines+markers", marker_color="#E65100", line=dict(width=3)))
        fig.update_layout(yaxis=dict(title="SS"), yaxis2=dict(title="予約数", overlaying="y", side="right"),
                          hovermode="x unified", height=350)
        st.plotly_chart(fig, use_container_width=True)

        # アプローチポイント
        st.markdown("### 💡 アプローチポイント")
        points = []
        if sel_row["予約数"] == 0 and sel_row["合計SS"] > 500:
            points.append(f"🔥 **営業チャンス**: SS {sel_row['合計SS']:,}件あるのに予約0件")
        if sel_row["sp-menu数"] == 0:
            points.append("🎯 **限定メニュー(sp-menu)未保有** → 作成で予約獲得チャンス")
        else:
            points.append(f"✅ 限定メニュー(sp-menu)保有: {sel_row['sp-menu数']}件")
        if sel_row["キレイレポ限定数"] == 0:
            points.append("🎯 **キレイレポ限定フラグ未保有** → 限定付けるだけで露出アップ")
        else:
            points.append(f"✅ キレイレポ限定フラグ保有: {sel_row['キレイレポ限定数']}件")
        for p in points: st.markdown(f"- {p}")

        # ========= 月別タブ切替 =========
        st.markdown("### 📅 月別詳細（タブ切り替え）")
        period_tab_labels = ["全期間"] + list(MONTH_LABELS.values())
        period_tabs = st.tabs(period_tab_labels)

        for idx, period_label in enumerate(period_tab_labels):
            with period_tabs[idx]:
                period_ym = None if period_label == "全期間" else [k for k,v in MONTH_LABELS.items() if v==period_label][0]

                # SS詳細（ランディング/経由/チャネル別）
                st.markdown("#### 🟦 SS詳細")
                df_period = build_summary(period_ym)
                period_row = df_period[df_period["store_id"]==sid]
                if len(period_row) > 0:
                    r_ = period_row.iloc[0]
                    ss_detail = pd.DataFrame([
                        {"項目": "合計SS", "値": int(r_["合計SS"])},
                        {"項目": "ランディング_合計", "値": int(r_["ランディング_合計"])},
                        {"項目": "　↳ 検索", "値": int(r_["ランディング_検索"])},
                        {"項目": "　↳ SNS", "値": int(r_["ランディング_SNS"])},
                        {"項目": "　↳ 直接", "値": int(r_["ランディング_直接"])},
                        {"項目": "　↳ 他サイト", "値": int(r_["ランディング_他サイト"])},
                        {"項目": "経由_合計", "値": int(r_["経由_合計"])},
                        {"項目": "　↳ 検索", "値": int(r_["経由_検索"])},
                        {"項目": "　↳ SNS", "値": int(r_["経由_SNS"])},
                        {"項目": "　↳ 直接", "値": int(r_["経由_直接"])},
                        {"項目": "　↳ 他サイト", "値": int(r_["経由_他サイト"])},
                        {"項目": "📦 予約数", "値": int(r_["予約数"])},
                        {"項目": "📦 予約率(%)", "値": f"{r_['予約率(%)']:.2f}%"},
                    ])
                    st.dataframe(ss_detail, use_container_width=True, hide_index=True)

                # ページ種別×チャネル別SS（月別フィルタ）
                st.markdown("#### 📄 ページ種別別SS")
                ps = df_ss[df_ss["store_id"]==sid]
                if period_ym:
                    ps = ps[ps["month"]==period_ym]
                if len(ps) > 0:
                    page_labels = {
                        "top":"クリニックトップ","menus":"メニュー一覧","menu_detail":"メニュー単体",
                        "sp_menus":"限定メニュー","reports":"口コミ一覧","reports_detail":"口コミ個別",
                        "articles":"取材記事","doctors":"ドクター","access":"アクセス",
                        "medical_cases":"症例","photos":"写真","other":"その他",
                    }
                    ps = ps.copy()
                    ps["ページ種別"] = ps["page_type"].map(page_labels)
                    pg = ps.groupby("ページ種別").agg(
                        SS=("ss","sum"), 検索=("organic_ss","sum"),
                        SNS=("social_ss","sum"), 直接=("direct_ss","sum"), 他サイト=("referral_ss","sum"),
                    ).reset_index().sort_values("SS", ascending=False)
                    st.dataframe(pg, use_container_width=True, hide_index=True)

                # 掲載リストページ（月別）
                st.markdown("#### 🎯 掲載リストページ TOP10")
                if period_ym:
                    cr = df_routes_m[df_routes_m["store_id"]==sid].copy()
                    cr = cr[cr["month"]==period_ym]
                    lss = df_list_ss_m[df_list_ss_m["month"]==period_ym][["list_path","page_ss"]]
                else:
                    cr = df_routes[df_routes["store_id"]==sid].copy()
                    lss = df_list_ss
                if len(cr) > 0:
                    cr = cr.merge(lss, on="list_path", how="left")
                    cr["カテゴリ"] = cr["list_path"].apply(cat_name)
                    ca = cr.groupby("カテゴリ").agg(経由SS=("via_ss","sum"), ページSS=("page_ss","max")).reset_index()
                    ca = ca[ca["カテゴリ"]!=""]
                    ca["流入率(%)"] = (ca["経由SS"]/ca["ページSS"]*100).round(1).where(ca["ページSS"]>0, 0)
                    ca = ca.sort_values("経由SS", ascending=False).head(10)
                    st.dataframe(ca, use_container_width=True, hide_index=True)
                else:
                    st.info("データなし")

                # 人気メニュー（月別）
                st.markdown("#### 🍽 人気メニュー TOP10")
                cm = df_menu_m[df_menu_m["store_id"]==sid].copy()
                if period_ym:
                    cm = cm[cm["month"]==period_ym]
                if len(cm) > 0:
                    def _flag_row(row):
                        if row["menu_type"] == "sp-menus": return "🎯 sp-menu"
                        elif row.get("campaign_type") == "exclusive": return "⭐ キレイレポ限定"
                        else: return "📄 ノーマル"
                    cm["タイプ"] = cm.apply(_flag_row, axis=1)
                    ma = cm.groupby(["menu_type","menu_id","タイプ","name"]).agg(
                        URL=("sample_url","first"), SS=("ss","sum"),
                        予約数=("rsv_count","sum"),
                    ).reset_index()
                    ma["CTR(%)"] = (ma["予約数"]/ma["SS"]*100).round(1).where(ma["SS"]>0, 0)
                    ma = ma.rename(columns={"name":"メニュー名"})
                    top_m = ma[["タイプ","メニュー名","URL","SS","予約数","CTR(%)"]].sort_values("SS", ascending=False).head(10)
                    st.dataframe(top_m, use_container_width=True, hide_index=True,
                        column_config={
                            "CTR(%)": st.column_config.ProgressColumn(min_value=0, max_value=25, format="%.1f%%"),
                            "URL": st.column_config.LinkColumn(),
                        })
                else:
                    st.info("データなし")

    st.markdown("---")
    st.subheader("🔥 営業チャンス：SSあるのに予約0院 TOP20")
    chance = df_total[(df_total["予約数"]==0) & (df_total["合計SS"]>0)].sort_values("合計SS", ascending=False).head(20)
    if len(chance) > 0:
        fig = px.bar(chance, x="合計SS", y="クリニック名", orientation="h",
                     color="sp-menu数", color_continuous_scale="Reds_r", height=600)
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(chance, use_container_width=True, hide_index=True)

st.markdown("---")
st.caption("データソース: BigQuery GA4（非サンプリング） / replica_kireirepo_production  |  毎日9:07自動更新")
