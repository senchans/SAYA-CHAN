import os
import streamlit as st
from openai import OpenAI
from supabase import create_client, Client  # Supabase接続
import uuid
from datetime import datetime
import random
import re
from audio_recorder_streamlit import audio_recorder
from tempfile import NamedTemporaryFile
from urllib.parse import quote_plus
import base64

#ほしいものをSupabaseに保存
def add_wish(child_id: int, item_name: str, point: int = 0):
    data = {
        "child_id": child_id,
        "item_name": item_name,
        "point": point,
        "is_deleted": 0,
        "created_at": datetime.utcnow().isoformat()
    }
    response = supabase.table("wishlist").insert(data).execute()
    return response

# ==========================================
# 0. ページ設定
# ==========================================

from streamlit_extras.let_it_rain import rain

# ページの設定（タイトルやアイコン）
st.set_page_config(
    page_title="いいこログ", page_icon="🎁", layout="wide", # wideで横長UI
    initial_sidebar_state="collapsed"  # デフォルトでサイドバーを閉じる
) 

# 雪降らし
rain(
    emoji="❄️",
    font_size=14,            # 雪の大きさ
    falling_speed=6.0,       # 落下速度（1.0-3.0目安）
    animation_length="infinite",  # ずっと降らせる
)

# 壁紙設定（後で変えたい）
bg_url = "https://ibqjfzinmlhvoxcfnvrx.supabase.co/storage/v1/object/sign/imgfiles/background_snow.png?token=eyJraWQiOiJzdG9yYWdlLXVybC1zaWduaW5nLWtleV85ZDk1NzYwNC00ODQyLTRhNjItOTYwMi04ZGUyOTY3ZjcwN2MiLCJhbGciOiJIUzI1NiJ9.eyJ1cmwiOiJpbWdmaWxlcy9iYWNrZ3JvdW5kX3Nub3cucG5nIiwiaWF0IjoxNzY1MjI5OTg3LCJleHAiOjQ4ODcyOTM5ODd9.bg5sUS6XJ97UcxJwbNgYQCiprRZmZQ7MUPLv442nXu0"

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

st.markdown("""
<style>
/* ====== 全体（紙っぽいカード感） ====== */
.block-container {
    background: transparent;
    border-radius: 0px; 
    box-shadow: none;
    padding: 1.6rem 2rem 2.2rem; 
}

/* ====== サイドバー（絵本の表紙） ====== */
section[data-testid="stSidebar"] {
    background: rgba(255,255,255,0.82);
    backdrop-filter: blur(6px);
    border-right: 2px solid rgba(255,255,255,0.9);
}
section[data-testid="stSidebar"] * {
    color: #23324a; /* 文字色：濃いネイビー */
}

/* サイドバーの見出し */
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    color: #c62828; /* クリスマス赤 */
    font-weight: 700;
}

/* ラジオ・セレクトの箱を丸く */
section[data-testid="stSidebar"] .stRadio,
section[data-testid="stSidebar"] .stSelectbox {
    background: rgba(255,255,255,0.9);
    padding: 10px 12px;
    border-radius: 14px;
    box-shadow: 0 4px 10px rgba(0,0,0,0.08);
}

/* ====== チャット吹き出し ====== */
div[data-testid="stChatMessage"] {
    padding: 12px 14px;
    border-radius: 18px;
    margin-bottom: 8px;
    box-shadow: 0 4px 10px rgba(0,0,0,0.15);
    background: rgba(255,255,255,0.92);
}
/* サンタ側だけ少し色味を変える*/
div[data-testid="stChatMessage"][data-testid="chatMessage-assistant"] {
    background: rgba(255,245,245,0.98) !important;
}

/* ====== タイトル装飾の余白 ====== */
h1, h2, h3 {
    text-shadow: 0 2px 6px rgba(0,0,0,0.08);
}
</style>
            
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* ====== 全体の本文・見出しを絵本っぽく ====== */
html, body, [class*="css"]  {
    line-height: 1.55;          /* 行間を詰めて読みやすく */
    letter-spacing: 0.02em;     /* 少しだけ字間を広げてやわらかく */
}

/* 見出しの雰囲気（太すぎ＆硬すぎを防ぐ） */
h1, h2, h3 {
    font-weight: 700;
    line-height: 1.25;
    margin-bottom: 0.6rem;
}

/* 段落の余白を詰める*/
p, li {
    margin-bottom: 0.35rem !important;
}

/* Streamlitのwriteが作る余白ブロックも少し詰める */
div[data-testid="stMarkdownContainer"] {
    margin-bottom: 0.2rem;
}
</style>
""", unsafe_allow_html=True)

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

</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* ====== ボタンデザインをクリスマス風に統一 ====== */
button[kind="primary"] {
    background: #BA8C6A !important;
    color: white !important;
    border-radius: 999px !important;
    padding: 0.6rem 1.2rem !important;
    border: none !important;
    box-shadow: 0 6px 14px rgba(0,0,0,0.18) !important;
}
button[kind="primary"]:hover {
    background: #A17656 !important;
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. Supabase / OpenAI 初期化
# ==========================================

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

# --- OpenAI ---
#cloud上でのキー認証
try:
    api_key = st.secrets.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")

except (FileNotFoundError, KeyError):
    # ローカル環境の場合
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")

if api_key:
    api_key = api_key.strip()

if not api_key:
    api_key = st.sidebar.text_input("OpenAI API Key", type="password")

if not api_key:
    st.warning("OpenAI APIキーが設定されていません。")
    st.stop()

client = OpenAI(api_key=api_key)

# ==========================================
# 2. SessionState 初期化（キー衝突防止）
# ==========================================
if "page" not in st.session_state:
    st.session_state["page"] = "lp"  # lp / chat

if "auth_user" not in st.session_state:
    st.session_state["auth_user"] = None

if "is_logged_in" not in st.session_state:
    st.session_state["is_logged_in"] = False

# ==========================================
# 3. ログイン / サインアップ ダイアログ
# ==========================================
@st.dialog("ログイン")
def login_dialog():
    mail_address = st.text_input("メールアドレス")
    password = st.text_input("パスワード", type="password")

    if st.button("ログイン"):
        result = (
            supabase.table("usermaster")
            .select("*")
            .eq("mail_address", mail_address)
            .eq("password", password)
            .execute()
        )

        if result.data:
            st.session_state["auth_user"] = result.data[0]
            st.session_state["is_logged_in"] = True
            user = st.session_state.auth_user
            st.session_state["user_id"] = user["user_id"] #追加：user_idをセッションに保存
            st.session_state["page"] = "chat"
            st.success("ログイン成功")
            st.switch_page("pages/dashboard.py")
        else:
            st.error("メールアドレスまたはパスワードが正しくありません。")

@st.dialog("新規登録")
def signup_dialog():
    name = st.text_input("ユーザー名")
    mail_address = st.text_input("メールアドレス")
    password = st.text_input("パスワード", type="password")
    password2 = st.text_input("パスワード（確認）", type="password")
    amazon_id = st.text_input("Amazon ID（任意）")

    if st.button("アカウント作成"):
        if not name.strip():
            st.error("ユーザー名は必須です。"); return
        if not mail_address.strip():
            st.error("メールアドレスは必須です。"); return
        if not password:
            st.error("パスワードは必須です。"); return
        if password != password2:
            st.error("パスワードが一致しません"); return

        supabase.table("usermaster").insert({
            "name": name,
            "mail_address": mail_address,
            "password": password,
            "amazon_id": amazon_id or None
        }).execute()

        st.success("アカウントを作成しました。ログインしてください。")

# ==========================================
# 4. LP（ログイン前トップ）
# ==========================================
def render_lp():
    
    #ヒーロー部分のカード（LPにだけ表示させる）
    st.markdown("""
    <div class="hero-card">
    <div class="hero-title">いいこログ  ～サンタさんからプレゼント～</div>
    <div class="hero-sub">サンタさんとおはなしして、いいこポイントをためよう！</div>

    <ul class="hero-list">
        <li>がんばったことや おてつだいしたことを つたえると、ポイントがふえるよ。</li>
        <li>サンタさんに こっそり ほしいものを おしえてみよう。</li>
        <li>いいこは クリスマスに プレゼントが もらえるかもしれないよ。</li>
    </ul>

    <div class="hero-foot">じゅんびはいい？ さっそく はじめよう！</div>
    </div>
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
        font-size: 2.1rem;
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
    /* LPのボタン列を前面に出す */
    div[data-testid="column"] button {
        position: relative;
        z-index: 5;
    }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([2, 2, 15])
    with col2:
        if st.button("ログイン", type="primary"):
            login_dialog()
    with col3:
        if st.button("新規登録", type="primary"):
            signup_dialog()

    # ★ ボタンの下に子供のイラスト追加
    st.markdown(
        """
        <style>
        .lp-illust {
            margin-top: -5px;
            margin-left: 30px;
            pointer-events: none;
        }
        .lp-illust img {
            width: 520px;
            max-width: 100%;
            pointer-events: none;
        }
        </style>

        <div class="lp-illust">
            <img src="https://ibqjfzinmlhvoxcfnvrx.supabase.co/storage/v1/object/sign/imgfiles/children_resize.png?token=eyJraWQiOiJzdG9yYWdlLXVybC1zaWduaW5nLWtleV85ZDk1NzYwNC00ODQyLTRhNjItOTYwMi04ZGUyOTY3ZjcwN2MiLCJhbGciOiJIUzI1NiJ9.eyJ1cmwiOiJpbWdmaWxlcy9jaGlsZHJlbl9yZXNpemUucG5nIiwiaWF0IjoxNzY1MzU5MTQ3LCJleHAiOjQ4ODc0MjMxNDd9.L_Z328gkyeSQ5MA9WlrUPwFQWF2MqCNh-bG1Jx8K8hk"
                 alt="children illust">
        </div>
        """,
        unsafe_allow_html=True
    )

# ==========================================
# 5. チャット / ポイント機能
# ==========================================

#ダッシュボードページで選択した子供情報の反映
selected_child = st.session_state.get("selected_child")

# Supabaseから有効なキーワード取得
# DB名称変更を修正
def fetch_active_keywords():
    res = supabase.table("taskmaster") \
        .select("task_id, task_name, point, category") \
        .eq("is_active", True) \
        .execute()
    return res.data or []

# 入力文 → マッチ判定して加点計算
def calc_points(text, keywords):
    if not text:    #初期値でテキストが入力されていない場合の対応
        return 0, []
    matched_rows = [row for row in keywords if row["task_name"] in text]
    total = sum(r["point"] for r in matched_rows)
    return total, matched_rows

# Points_logに保存 → pointledgerへ変更
def insert_points_log(child_id, matched_rows, user_text):
    for r in matched_rows:
        supabase.table("pointledger").insert({
            "child_id": child_id,
            "task_id": r["task_id"],
            "task_name": user_text,
            "point": r["point"],
        }).execute()

# For_Children →　childmasterへポイント集積結果の反映先を変更
def upsert_child_total(child_id, new_total):
    supabase.table("childmaster").update({
        "total_points": new_total
    }).eq("child_id", child_id).execute()

# 子ども情報取得  #<確認>childmaster内の子どもの名前はchild_nameにしてはどうか？
def fetch_children_for_user(user_id):
    res = supabase.table("childmaster") \
        .select("*") \
        .eq("user_id", user_id) \
        .execute()
    return res.data or []

# ---------------------------
# キャラプロンプト
# ---------------------------
SANTA_PROMPT = """
あなたは子供が大好きな、優しくて温かいサンタクロースです。
子供とお話して、いいことをしたらたくさん褒め、嫌なことや悪いことをしたら優しく諭してあげます。
4〜6ターン目くらいで「そういえば、もうすぐクリスマスじゃな。クリスマスプレゼントはなにがほしいのかい？」とやさしく聞いてください。
次のルールを必ず守って、ぶれないサンタクロースとしてふるまってください。

【基本キャラ】
・一人称は「わし」。
・にこにこしていて、優しいおじいちゃんの雰囲気。絶対否定しない。
・「〜じゃよ」「〜だよ」のような、親しみやすいサンタ口調を使ってください。
・子どもの気持ちを一番大切にする。
・子どもが怖がるようなこと、脅す、叱る、バカにする、傷つけることは絶対に言わない。
・親（保護者）をリスペクトし、絶対に親（おかあさん、おとうさん、おじいちゃん、おばあちゃん）の悪口を言わない。

【言葉遣い】
・必ず全部「ひらがな」で書くこと。漢字と記号と顔文字は絶対使わない。英語は最低限で、平易な日本語で話す。絵文字はかわいいから使ってもいいよ。
・短く、簡単に、ゆっくり読める言葉を話す。
・文の長さは最大2文まで。
・子どもが言った言葉を基本はかみ砕いてオウム返ししてあげる。「お手伝いキーワード」が入っていたら必ず繰り返す。
"""

# ===== サンタ固定設定 =====
header_title = "🎅 サンタさんとおはなししよう！"
system_prompt = SANTA_PROMPT
ai_avatar = "https://ibqjfzinmlhvoxcfnvrx.supabase.co/storage/v1/object/sign/imgfiles/santa_icon_resize.png?token=eyJraWQiOiJzdG9yYWdlLXVybC1zaWduaW5nLWtleV85ZDk1NzYwNC00ODQyLTRhNjItOTYwMi04ZGUyOTY3ZjcwN2MiLCJhbGciOiJIUzI1NiJ9.eyJ1cmwiOiJpbWdmaWxlcy9zYW50YV9pY29uX3Jlc2l6ZS5wbmciLCJpYXQiOjE3NjUzNTg3MTIsImV4cCI6NDg4NzQyMjcxMn0.zxPY_pHoLm87BpMlqNy-mb0uajI1Mv-EFq0nayOJ-Ag"

# ---------------------------
# 音声 → テキスト（STT）
# ---------------------------
def transcribe_audio_to_text(audio_bytes) -> str:
    # Windows対策：delete=Falseで一旦閉じてから読む
    temp_file = NamedTemporaryFile(delete=False, suffix=".wav")
    try:
        temp_file.write(audio_bytes)
        temp_file.flush()
        temp_file.close()  # ← ここで必ず閉じる

        with open(temp_file.name, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",
                file=audio_file,
                response_format="text",
            )
        return transcription

    finally:
        # 後始末（残った一時ファイルを消す）
        try:
            os.remove(temp_file.name)
        except Exception:
            pass

# ---------------------------
# テキスト → 音声（TTS）
# ---------------------------
def text_to_speech(text: str) -> bytes:
    speech = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="verse",
        input=text
    )
    return speech.content

def autoplay_audio(audio_bytes: bytes):
    b64 = base64.b64encode(audio_bytes).decode()
    st.markdown(
        f"""
        <audio autoplay>
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
        </audio>
        """,
        unsafe_allow_html=True
    )

def render_chat():
    user_input = None

    # ---- 子ども選択 ----
    user_id = st.session_state["auth_user"]["user_id"]
    children = fetch_children_for_user(user_id)

    if not children:
        st.sidebar.warning("まずは こどもをとうろくしてね（管理画面で追加予定）")
        st.stop()

    child_options = {c["name"]: c for c in children} #＜確認＞childmaster内の子どもの名前はchild_nameにしてはどうか？
    sorted_names = sorted(child_options.keys())
    selected_child_name = st.sidebar.selectbox(
        "だれがおはなしする？（こどもをえらんでね）",
        sorted_names,
        index=st.session_state.get("selected_child_index", 0)
    )
    selected_child = child_options[selected_child_name]

    st.session_state["child_id"] = selected_child["child_id"]
    st.session_state["name"] = selected_child["name"] #<確認>childmaster内の子どもの名前はchild_nameにしてはどうか？
    st.session_state["user_id"]= selected_child["user_id"]
    #st.session_state["total_points"] = selected_child["total_points"]
    #if st.session_state["total_points"] not in st.session_state or st.session_state["total_points"] is None:
    #    st.session_state["total_points"] = 0
    if "total_points" not in st.session_state:
        st.session_state["total_points"] = selected_child.get("total_points") or 0

    # ---- 画面レイアウト ----   
    left_col, right_col = st.columns([1, 4], gap="large")
    with right_col:
        col_title, col_btn = st.columns([8, 2])
        with col_title:
            st.markdown(f'<div class="app-title">{header_title}</div>', unsafe_allow_html=True)
        with col_btn:
            if st.button("チャットを終わる", type="primary", key="open_end_dialog"):
                st.session_state["show_end_dialog"] = True
            if st.session_state.get("show_end_dialog"):
                end_chat_dialog()
                st.stop()  # または return


    # ---- チャットを左、ポイントを右に表示 ----
    with st.container():
        col_chat, col_point = st.columns([4,1])
        with col_point:
            st.image(
            "https://eiyoushi-hutaba.com/wp-content/uploads/2022/11/%E3%82%B5%E3%83%B3%E3%82%BF%E3%81%95%E3%82%93-940x940.png",
            width=200,
            caption="サンタさん"
            )
            st.markdown("### よいこポイント")
            points_box1 = st.empty()
            points_box1.metric("いまのポイント", st.session_state["total_points"])
        #   もくひょうポイント
            goal_points =  selected_child.get("goal_points")
        #    Noneのときはデフォルト値を50に設定
            if goal_points is None:
                goal_points = 50  # デフォルト目標ポイント
            points_box2 = st.empty()
            points_box2.metric("もくひょうポイント", goal_points)


        with col_chat:
            # ---- 会話履歴初期化 ----
            if "messages" not in st.session_state or len(st.session_state["messages"]) == 0:
                st.session_state["messages"] = [{"role": "system", "content": system_prompt}]
            else:
                st.session_state["messages"][0] = {"role": "system", "content": system_prompt}

            # ---- チャット履歴表示 ----
            for msg in st.session_state["messages"]:
                if msg["role"] == "system":
                    continue
                if not msg.get("content"):
                    continue
                icon = ai_avatar if msg["role"] == "assistant" else "🧒"
                with st.chat_message(msg["role"], avatar=icon):
                    st.markdown(msg["content"])

            # ===== 入力方法の選択=====
            use_voice = st.toggle("🎙️ こえで しゃべる", value=False)

            user_input = None

            if use_voice:
                audio_bytes = audio_recorder(text="🎤 おはなししてね", pause_threshold=3)
                if audio_bytes is None or len(audio_bytes) < 1000:
                    st.info("もういちど、こえを いれてみてね")
                    return
                with st.spinner("こえを もじに しているよ…"):
                    user_input = transcribe_audio_to_text(audio_bytes)
                if not user_input:
                    st.info("うまく ききとれなかったよ。もういちど しゃべってね")
                    return
                    # 子どもが話した内容を画面にも見せたい場合
                st.chat_message("user", avatar="🧒").write(user_input)
                st.session_state["messages"].append({"role": "user", "content": user_input})
            else:
                user_input = st.chat_input("ここに いれてね")
                # ★ 何も入力されてない（None / ""）時はここで終了
                if not user_input:
                    return
                with st.chat_message("user", avatar="🧒"):
                    st.markdown(user_input)
                if user_input:  # ★None/"" のときはappendしない
                    st.session_state["messages"].append({"role": "user", "content": user_input})

                # 正規表現で「〇〇ほしい」「〇〇がいい」などを抽出
                pattern = r"(.+?)(ほしい|がほしい|がいいな|がいい|おねがい|をおねがい|おねがいします|をおねがいします|ください|をください|かな)"
                match = re.search(pattern, user_input)

                if match:
                    item = match.group(1).strip()
                else:
                    item = user_input.strip()

                # ===== 保存処理はサンタが質問した直後だけ =====
                if st.session_state.get("awaiting_wish", False) and item:
                    try:
                        result = add_wish(
                            child_id=st.session_state["child_id"],
                            item_name=item,
                            point=0
                        )
                        st.success(f"🎁 {item} をサンタさんへのおねがいとして保存したよ！")
                        st.session_state["awaiting_wish"] = False  # 保存後はフラグを戻す
                    except Exception as e:
                        st.error(f"おねがいの保存中にエラーが発生しました: {e}")

            # 加点処理
            if not user_input:
                return
            keywords = fetch_active_keywords()
            add_points, matched_rows = calc_points(user_input, keywords)

            if add_points > 0:
                st.session_state["total_points"] += add_points
                points_box1.metric("いまのポイント", st.session_state["total_points"])

                insert_points_log(st.session_state["child_id"], matched_rows, user_input)
                upsert_child_total(st.session_state["child_id"], st.session_state["total_points"])

                matched_words = [r["task_name"] for r in matched_rows]
                st.success(f"すごい！「{'、'.join(matched_words)}」で {add_points} てん たまったよ！")

                # 加点時に風船
                st.balloons()

            if st.session_state.get("show_end_dialog"):
                pass #　ボタンが押された場合は以下の処理は実施しない

            else:
                # AI返答
                try:
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=st.session_state["messages"],
                        stream=True
                    )

                    with st.chat_message("assistant", avatar=ai_avatar):
                        message_placeholder = st.empty()
                        full_response = ""

                        for chunk in response:
                            delta = chunk.choices[0].delta
                            token = delta.content if delta and delta.content else ""
                            full_response += token
                            message_placeholder.markdown(full_response + "▌")

                        message_placeholder.markdown(full_response)

                    if full_response:
                        st.session_state["messages"].append(
                            {"role": "assistant", "content": full_response}
                        )

                        # ===== サンタの声を出す（TTS）=====
                        # 子ども側が「こえで しゃべる」をONにしていた時だけ音声を返す
                        if use_voice:
                            try:
                                santa_voice = text_to_speech(full_response)
                                autoplay_audio(santa_voice)
                                st.audio(santa_voice, format="audio/mp3")
                            except Exception as e:
                                st.warning(f"おんせいが だせなかったよ: {e}")

                        # ===== サンタが質問したかどうかを判定 =====
                        # プロンプトで「クリスマスプレゼントはなにがほしいのかい？」と聞くようにしているので
                        # 返答に「クリスマスプレゼント」や「ほしい」が含まれていたらフラグを立てる
                        if "クリスマスプレゼント" in full_response and "ほしい" in full_response:
                            st.session_state["awaiting_wish"] = True


                except Exception as e:
                    st.error(f"エラーが発生しました: {e}")


            if st.session_state["show_end_dialog"]:
                end_chat_dialog()

                # ---- おねがいリスト管理 ----
                if "pending_item" not in st.session_state:
                    st.session_state["pending_item"] = None
                if "chat_count" not in st.session_state:
                    st.session_state["chat_count"] = 0

#チャット終了ダイアログ
if "show_end_dialog" not in st.session_state:
    st.session_state["show_end_dialog"] = False

# Streamlitのダイアログ（モーダル風）
@st.dialog("チャットを終わりますか？")
def end_chat_dialog():
    st.write("ほごしゃのぱすわーどをいれてね。")

    # ★ここでパスワード入力
    pw = st.text_input("パスワード", type="password")

    # 照合先のpasswordをSupabaseから取得するキーとしてuser_idを使う
    user_id = st.session_state.get("user_id")


    col_a, col_b = st.columns(2)
    # キャンセル処理
    with col_a:
        if st.button("キャンセル", key="cancel_exit_dialog"):
            st.session_state["show_end_dialog"] = False
            st.rerun()

    # チャット終了処理
    with col_b:
        if st.button("チャットを終わる", key="confirm_exit_chat"):

            # Supabaseから保護者のパスワードを取得
            res = (
                supabase.table("usermaster")
                .select("password")
                .eq("user_id", user_id)
                .execute()
            )
            # ★パスワードチェック
            if not res.data:
                st.error("ぱすわーどがちがうよ。")
                return
            
            CORRECT_PASSWORD = res.data[0]["password"]

            # パスワードが正しければチャット終了
            if pw == CORRECT_PASSWORD:
                st.session_state["show_end_dialog"] = False
                # チャット終了処理
                st.session_state["messages"] = []
                st.success("チャットをおわったよ。")
                st.switch_page("pages/dashboard.py")

            else:
                st.error("ぱすわーどがちがうよ。")

    # ==========================================
# 6. 画面ルーティング
# ==========================================
if not st.session_state["is_logged_in"]:
    render_lp()
else:
    render_chat()