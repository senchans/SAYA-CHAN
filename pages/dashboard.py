import streamlit as st
from supabase import create_client, Client
import uuid
from datetime import datetime
import os
from dotenv import load_dotenv
load_dotenv()

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

# -- お子さんの情報初期化 --

if "children_list" not in st.session_state:
    st.session_state.children_list = load_children()
if "registration_done" not in st.session_state:
    st.session_state.registration_done = False

child_names = [child["name"] for child in st.session_state.children_list]

# -- お子さんのプロフィール新規登録ポップアップ定義 --

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

#　-- タイトル --

st.title(f"ようこそ、{user['name']} さん！")

#　--サイドバー--

st.sidebar.header("お子さんの選択")

# プルダウン
selected_child = st.sidebar.selectbox(
    "お子さんを選択してください",
    child_names if child_names else ["登録されていません"]
)
if st.sidebar.button("お子さんを登録する"):
    registration_dialog()


