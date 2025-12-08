import streamlit as st
from supabase import create_client, Client
import pandas as pd #app.py統合時には追加を忘れないように！
import uuid
from datetime import datetime, date
import os
from dotenv import load_dotenv
load_dotenv()

# ---- CSSでざっくりフレーム寄せ（見た目調整）----
# === UI変更点: 左ポイント枠/右チャット枠の雰囲気を近づける ===
st.markdown("""
<style>
/* ページ全体の左右余白を減らす */
.main .block-container {
    padding-top: 1.2rem;
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
    birth_date = st.date_input("生年月日")
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

#　-- タイトル --

st.subheader(f"ようこそ、{user['name']} さん！")

#　--サイドバー--

st.sidebar.header("お子さんの選択")

# プルダウン
children = st.session_state.children_list
child_map = {child["name"]: child for child in st.session_state.children_list}
child_names = list(child_map.keys())

selected_child = st.sidebar.selectbox(
    "お子さんを選択してください",
    child_names if child_names else ["登録されていません"]
)
if st.sidebar.button("お子さんを登録する"):
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

    today = date.today()
    age = today.year - birth_date.year - (
        (today.month, today.day) < (birth_date.month, birth_date.day)
    )

# -- ほしいものリスト呼び出し --
if st.session_state.selected_child:
    st.session_state.wishlist_items = fetch_wishlist_for_child(st.session_state.selected_child['child_id'])
else:
    st.session_state.wishlist_items = []

# -- ダッシュボード --
with st.container():
    col1, col2 = st.columns([2, 1]) 
    with col1: #プロフィール
        st.write(f"{selected_child['name']}プロフィール")
        st.write(f"性別：{gender}")
        st.write(f"生年月日：{birth_date}")
        st.write(f"年齢：{age}歳")
    with col2: #チャット画面遷移ボタン
        if st.button("サンタさんとチャットする"):
            st.switch_page("app.py")

st.divider()

# -- ほしいものリスト表示 --
with st.container():
    st.write("ほしいものリスト")
    if st.session_state.wishlist_items:
        df = pd.DataFrame(st.session_state.wishlist_items)
        df = df.rename(columns={
            "item_name": "商品名",
            "created_at": "追加日時"
        })
        df["追加日時"] = pd.to_datetime(df["追加日時"]).dt.strftime("%Y-%m-%d %H:%M")
        st.dataframe(df, hide_index=True)
    else:
        st.info("ほしいものリストに追加されたアイテムはまだありません。")
    if st.button("ほしいものを追加する"):
        wishlist_dialog()

st.divider()

# -- いいこポイント表示 --
with st.container():
    st.write("いいこポイント")