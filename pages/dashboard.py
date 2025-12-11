import streamlit as st
from supabase import create_client, Client
import pandas as pd #app.py統合時には追加を忘れないように！
import uuid
from datetime import datetime, date
from urllib.parse import quote_plus
import os
from dotenv import load_dotenv
load_dotenv()

st.set_page_config(
    page_title="いいこログ", page_icon="🎁", layout="wide",
    initial_sidebar_state="collapsed"  # ←ここでデフォルトを閉じる
)

# 壁紙設定（後で変えたい）
bg_url = "https://ibqjfzinmlhvoxcfnvrx.supabase.co/storage/v1/object/sign/imgfiles/background_snowdark.png?token=eyJraWQiOiJzdG9yYWdlLXVybC1zaWduaW5nLWtleV85ZDk1NzYwNC00ODQyLTRhNjItOTYwMi04ZGUyOTY3ZjcwN2MiLCJhbGciOiJIUzI1NiJ9.eyJ1cmwiOiJpbWdmaWxlcy9iYWNrZ3JvdW5kX3Nub3dkYXJrLnBuZyIsImlhdCI6MTc2NTI4Njc1NywiZXhwIjo0OTE4ODg2NzU3fQ.cuyBjUpPhoTZrc34VXlaas0U7pHDOG0tz0mamIddIaw"

st.markdown(
    f"""
    <style>
    /* アプリ全体の背景 */
    .stApp {{
        background-image: url("{bg_url}");
        background-repeat: repeat;
        background-size: 160px auto;  /* 好きな細かさに調整 */
        background-position: center;
        background-attachment: fixed;   /* スクロールしても背景固定 */
    }}
    </style>
    """,
    unsafe_allow_html=True
)


# ---- CSSでざっくりフレーム寄せ（見た目調整）----
# === UI変更点: 左ポイント枠/右チャット枠の雰囲気を近づける ===
st.markdown("""
<style>
/* ページ全体の左右余白を減らす */
.main .block-container {
    padding-top: 0.5em;
    padding-bottom: 1.5rem;
    padding-left: 2rem;
    padding-right: 2rem;
    max-width: 100%;
}

/* 上部のデフォルト空白を少し詰める */
header[data-testid="stHeader"] {
    height: 0rem;
}

/* タイトル行を折り返さない（切れを防ぐ） */
.app-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 8px;
}

.app-title {
    font-size: 32px;
    font-weight: 800;
    white-space: nowrap;
}
            
/* 以下app.py統合時には追加を忘れないように！ */           
p {
    margin: 0.3em 0;  
}         

                 
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* ====== トップ用の絵本カード ====== */
.hero-card {
    background: rgba(255,255,255,0.92);
    border-radius: 26px;
    padding: 28px 30px;
    box-shadow: 0 12px 30px rgba(0,0,0,0.18);
    max-width: 900px;
    margin: 20px 0 10px 0;
}

.hero-title {
    font-size: 1.7rem;
    font-weight: 800;
    color: #0B3D2E;
    margin-bottom: 6px;
}

.hero-sub {
    font-size: 1.25rem;
    font-weight: 700;
    color: #D50000;
    margin-bottom: 14px;
}

.hero-list {
    padding-left: 1.2rem;
    margin: 0 0 12px 0;
    color: #0B3D2E;
    font-size: 1.05rem;
    line-height: 1.6;
}

.hero-foot {
    font-size: 1.15rem;
    font-weight: 700;
    color: #0B3D2E;
    margin-top: 8px;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* ====== ボタンをクリスマス風に統一 ====== */
button[kind="primary"] {
    background: #BA8C6A !important;  /* ←ここを変更 */
    color: white !important;
    border-radius: 999px !important;
    padding: 0.6rem 1.2rem !important;
    border: none !important;
    box-shadow: 0 6px 14px rgba(0,0,0,0.18) !important;
}
button[kind="primary"]:hover {
    background: #A17656 !important; /* ←hoverも合わせる */
}
</style>
""", unsafe_allow_html=True)

# --- Supabase ---
#cloud上でのキー認証
try:
    SUPABASE_URL = st.secrets.get("SUPABASE_URL") or os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = st.secrets.get("SUPABASE_ANON_KEY") or os.environ.get("SUPABASE_KEY")

#Localの場合のキー認証として.envから読み取る
except (FileNotFoundError, KeyError):
    # ローカル環境の場合
    from dotenv import load_dotenv
    load_dotenv()
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("SupabaseのSUPABASE_URL / (ANON_KEY or KEY) が見つかりません。secrets か環境変数を確認してください。")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

user = st.session_state.auth_user #ユーザー情報定義

# ユーザー情報に基づきお子さんの情報が登録されているか検索
def load_children():
    res = (
        supabase.table("childmaster")
        .select("*")
        .eq("user_id", user['user_id'])
        .order("created_at", desc=False)
        .execute()
    )
    return res.data or []

def fetch_wishlist_for_child(child_id):
    res = (
        supabase.table("wishlist") 
        .select("item_name, created_at") 
        .eq("child_id", child_id) 
        .order("created_at", desc=False) 
        .execute()
    )
    return res.data or []

def fetch_pointledger_for_child(child_id):
    res = (
        supabase.table("pointledger") 
        .select("task_name, point,created_at ") 
        .eq("child_id", child_id) 
        .order("created_at", desc=False) 
        .execute()
    )
    return res.data or []

# -- 情報初期化 --
#お子さん情報
if "children_list" not in st.session_state:
    st.session_state.children_list = load_children()
if "registration_done" not in st.session_state:
    st.session_state.registration_done = False
if "selected_child" not in st.session_state:
    st.session_state.selected_child = None


child_names = [child["name"] for child in st.session_state.children_list]

# -- ポップアップ定義 --
#お子さんのプロフィール新規登録
@st.dialog("お子さんプロフィール登録")
def registration_dialog():
    name = st.text_input("お名前")
    birth_date = st.date_input(
        "生年月日",
        value=date(2020, 1, 1),          # ← 未来日を避けて過去を初期値に
        min_value=date(2000, 1, 1),      # ← ここで選択可能下限
        max_value=date.today()           # ← 今日まで選択OK
    )
    gender = st.selectbox("性別" ,("男の子","女の子","選択しない"))

    if st.button("登録"):
        if not name.strip():
            st.error("お名前は必須です。")
        elif not birth_date:
            st.error("生年月日は必須です。")
        elif not gender:
            st.error("性別は必須です。")
        # Supabase childmaster に追加
        else:
            supabase.table("childmaster").insert({
                "user_id": user["user_id"],
                "name": name.strip(),
                "birth_date": birth_date.isoformat(),  # "YYYY-MM-DD" の文字列
                "gender": gender
            }).execute()
        st.success("お子さんの情報を登録しました。")
        st.session_state.children_list = load_children()
        st.rerun()

#ほしいものリスト追加
@st.dialog("ほしいものリストに追加")
def wishlist_dialog():
    item_name = st.text_input("商品名")
    if not st.session_state.selected_child:
        st.error("お子さんを選択してください")
        return
    child_id = st.session_state.selected_child['child_id']

    if st.button("登録"):
        if not item_name.strip():
            st.error("商品名は必須です。")
        else:
            supabase.table("wishlist").insert({
                "child_id": child_id,
                "item_name": item_name
            }).execute()
        st.success("ほしいものリストに追加しました。")
        st.rerun()

@st.dialog("目標ポイントを変更")
def changegoal_dialog():
    if not st.session_state.selected_child:
        st.error("お子さんを選択してください。")
        return
    child = st.session_state.selected_child
    current_goal = child.get("goal_points", 50)

    new_goal = st.number_input(
        "新しい目標ポイントを入力してください",
        min_value=1,
        max_value=10000,
        value=int(current_goal),
        step=1
    )

    if st.button("保存する"):
        supabase.table("childmaster").update({
            "goal_points": new_goal
        }).eq("child_id", child["child_id"]).execute()

        st.success("目標ポイントを更新しました。")

        # 最新データを再取得
        st.session_state.children_list = load_children()
        st.session_state.selected_child = next(
            c for c in st.session_state.children_list if c["child_id"] == child["child_id"]
        )
        st.rerun()


#　-- タイトル/ログアウトボタン  --
with st.container():
    col1, col2 = st.columns([5, 1])
    with col1:
        st.header(f"🎄ようこそ、{user['name']} さん！")
    with col2:
        if st.button("ログアウト", type="primary"):
            if "auth_user" in st.session_state:
                del st.session_state["auth_user"]
            st.session_state.clear()
            st.switch_page("app.py")

        # -- ほしいものリスト呼び出し --
        if st.session_state.selected_child:
            st.session_state.wishlist_items = fetch_wishlist_for_child(st.session_state.selected_child['child_id'])
        else:
            st.session_state.wishlist_items = []

        # -- ほしいものリスト呼び出し --
        if st.session_state.selected_child:
            st.session_state.pointledger_points = fetch_pointledger_for_child(st.session_state.selected_child['child_id'])
        else:
            st.session_state.pointledger_points = []
            
# プルダウン
children = st.session_state.children_list
child_map = {child["name"]: child for child in st.session_state.children_list}
child_names = sorted([child["name"] for child in children])
if st.session_state.selected_child:
    child_names = [child["name"] for child in st.session_state.children_list]
    if st.session_state.selected_child["name"] in child_names:
        st.session_state.selected_child_index = child_names.index(st.session_state.selected_child["name"])
    else:
        st.session_state.selected_child_index = 0
else:
    st.session_state.selected_child_index = 0

with st.container():
    col1, col2 = st.columns([7, 2])

    with col1:
        selected_child = st.selectbox(
            "どのお子さんのプロフィールを見ますか？",
            child_names if child_names else ["登録されていません"]
        )
    with col2:
        if st.button("お子さんを登録する", type="primary"):
            registration_dialog()
            st.session_state.children_list = load_children()

        if child_names:
            selected_child_name = selected_child
        else:
            selected_child_name = None

        if selected_child in child_map:
            st.session_state.selected_child = child_map[selected_child]
        else:
            st.session_state.selected_child = None

        if selected_child in child_map:
            selected_child = child_map[selected_child]
            gender = selected_child["gender"]
            birth_date_str = selected_child["birth_date"]
            child_id = selected_child["child_id"]
            birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d").date()
            goal_points = int(selected_child["goal_points"])

            today = date.today()
            age = today.year - birth_date.year - (
                (today.month, today.day) < (birth_date.month, birth_date.day)
            )
        else:
            selected_child = None

st.divider()

# -- ダッシュボード --
with st.container():
    col1, col2 = st.columns([3, 1])

    with col1:  # プロフィール
        if selected_child:
            st.markdown(f"""
            <div class="hero-card">
            <div class="hero-title">{selected_child['name']}プロフィール</div>
            <ul class="hero-list">
                <li>性別：{gender}</li>
                <li>生年月日：{birth_date}</li>
                <li>年齢：{age}歳</li>
            </ul>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("お子さんを登録して、はじめましょう！")

    with col2:  # チャット画面遷移ボタン
        if st.button("サンタさんとチャットする", type="primary", disabled = (st.session_state.selected_child is None)):
            st.switch_page("app.py")

st.divider()

# -- ほしいものリスト表示 --
with st.container():
    st.markdown("<b>💖ほしいものリスト</b>", unsafe_allow_html=True)
    if st.session_state.wishlist_items:
        df = pd.DataFrame(st.session_state.wishlist_items)

        # 表示用の列名に変更
        df = df.rename(columns={
            "item_name": "商品名",
            "created_at": "追加日時"
        })
        df["追加日時"] = pd.to_datetime(df["追加日時"]).dt.strftime("%Y-%m-%d %H:%M")

        # Amazon検索URL列を追加
        df["Amazonで検索"] = df["商品名"].apply(
            lambda x: f"https://www.amazon.co.jp/s?k={quote_plus(str(x))}"
        )

        # クリック可能なリンク列として表示
        st.dataframe(
            df,
            hide_index=True,
            column_config={
                "Amazonで検索": st.column_config.LinkColumn(
                    label="Amazonで検索",
                    display_text="Amazonでひらく"
                )
            }
        )
    else:
        st.info("ほしいものリストに追加されたアイテムはまだありません。")

    if st.button("ほしいものを追加する", type="primary"):
        wishlist_dialog()

st.divider()

# -- いいこポイント表示 --
# -- いいこポイント表示 --
with st.container():
    st.markdown("<b>⭐いいこポイント</b>", unsafe_allow_html=True)
    if st.session_state.pointledger_points:
        df = pd.DataFrame(st.session_state.pointledger_points)
        df = df.rename(columns={
            "task_name": "おてつだい",
            "created_at": "追加日時",
            "point": "ポイント"
        })
        df["追加日時"] = pd.to_datetime(df["追加日時"]).dt.strftime("%Y-%m-%d %H:%M")
        st.dataframe(df, hide_index=True)
        
        # goal_points を int に変換
        try:
            goal_points = int(selected_child["goal_points"])
        except:
            goal_points = 0 

        total_points = df["ポイント"].sum()
        st.markdown(f"<b>合計ポイント： {total_points} ポイント</b>", unsafe_allow_html=True)
        st.markdown(f"<b>目標ポイント： {goal_points} ポイント</b>", unsafe_allow_html=True)

        if total_points >= goal_points:
            st.success("おめでとうございます！目標を達成しました🎉")
        else:
            remaining = goal_points - total_points
            st.markdown(f"<b>目標まであと： {remaining} ポイント</b>", unsafe_allow_html=True)
    else:
        st.info("いいこポイントはまだ貯まっていません。")
    
    if st.button("目標ポイントを変更する", type="primary", disabled = (st.session_state.selected_child is None)):
        changegoal_dialog()
