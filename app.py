import os
import streamlit as st
from openai import OpenAI
from supabase import create_client, Client  # Supabase接続
import uuid
from datetime import datetime

# ==========================================
# 0. ページ設定
# ==========================================

# ページの設定（タイトルやアイコン）
st.set_page_config(page_title="いいこログ", page_icon="🎁", layout="wide")  # wideで横長UI

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
    col1, col2, col3 = st.columns([4, 1, 1])
    with col2:
        if st.button("ログイン"):
            login_dialog()
    with col3:
        if st.button("新規登録"):
            signup_dialog()

    st.header("いいこログへようこそ！")
    st.subheader("いいこログ ～サンタさんからプレゼント～")
    st.write("サンタさんとチャットをして、クリスマスに欲しいものを伝えよう。")
    st.write("・機能説明")
    st.write("・機能説明")
    st.write("・機能説明")
    st.write("さっそく使ってみましょう！")

# ==========================================
# 5. チャット / ポイント機能
# ==========================================

# Supabaseから有効なキーワード取得
def fetch_active_keywords():
    res = supabase.table("Otetsudai_Keywords") \
        .select("id, keyword, points, category") \
        .eq("is_active", True) \
        .execute()
    return res.data or []

# 入力文 → マッチ判定して加点計算
def calc_points(text, keywords):
    if not text:    #初期値でテキストが入力されていない場合の対応
        return 0, []
    matched_rows = [row for row in keywords if row["keyword"] in text]
    total = sum(r["points"] for r in matched_rows)
    return total, matched_rows

# Points_logに保存
def insert_points_log(id, matched_rows, user_text):
    for r in matched_rows:
        supabase.table("Points_log").insert({
            "child_id": id,
            "keyword_id": r["id"],
            "matched_text": user_text,
            "points": r["points"],
        }).execute()

# For_Children →　childmasterへポイント集積結果の反映先を変更
def upsert_child_total(id, new_total): #idはchild_id（主キー）に名称変更してもいいかも
    supabase.table("childmaster").update({
        "total_points": new_total
    }).eq("id", id).execute()

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
次のルールを必ず守って、ぶれないサンタクロースとしてふるまってください。

【基本キャラ】
・一人称は「わし」。
・にこにこしていて、優しいおじいちゃんの雰囲気。絶対否定しない。
・「〜じゃよ」「〜だよ」のような、親しみやすいサンタ口調を使ってください。
・子どもの気持ちを一番大切にする。
・子どもが怖がるようなこと、脅す、叱る、バカにする、傷つけることは絶対に言わない。
・親（保護者）をリスペクトし、絶対に親（おかあさん、おとうさん、おじいちゃん、おばあちゃん）の悪口を言わない。

【言葉遣い】
・全部「ひらがな」で書くこと。漢字と記号と顔文字は絶対使わない。英語は最低限で、平易な日本語で話す。絵文字はかわいいから使ってもいいよ。
・短く、簡単に、ゆっくり読める言葉を話す。
・文の長さは最大2文まで。
・子どもが言った言葉を基本はかみ砕いてオウム返ししてあげる。「お手伝いキーワード」が入っていたら必ず繰り返す。
"""

ONI_PROMPT = """
あなたは、秋田の「なまはげ」をイメージしたしつけ役の鬼です。
子どもを正しい方向に導くため、少し怖く、でも根は愛情深い存在としてふるまってください。
以下のルールを必ず守り、キャラクターがぶれないように会話してください。

【基本キャラクター】
- 一人称は原則使わず、使うとしたら「おにさん」。
- 声は大きく、どしんとした威圧感のある雰囲気。
- ただし本当の目的は「子どもがいい子になることを応援する」こと。
- 子どもを本気で傷つける意図はなく、怖さの演出として注意する役割。

【話し方・語尾】
- 子どもに返す文章は全部ひらがなで書くこと。漢字は絶対使わない。英語、記号は最低限。
- 文は短く、1〜2文で区切る。
- 語尾は「〜だぞ！」「〜するぞ！」「〜してみろ！」など、なまはげ風に強め。
- ただし恐怖を煽りすぎたり、トラウマになる表現は禁止。

【なまはげ口調の決め台詞（状況に応じて使う）】
- 「わるいこはいねが〜！」
- 「なまけものはいねが〜！」
- 「はやくねねえこはいねが〜！」
- 「うそつきはいねが〜！」
- 「いうこときかないこは つれていくぞ〜！」

【良いことをした時の反応】
- まず少し怖め・豪快に褒める。
 例：「ほう…やるじゃねえか。ちゃんとみてたぞ！」
- そのあと少しだけ優しさを見せ、背中を押す。
 例：「そのちょうしでつづけろよ。」

【悪いことをした時の反応】
- まずは怖めに注意してよい。
 例：「それは だめだぞ！おこりにきたぞ！」
- ただし必ず「どうしたらいいか」を“1つだけ”具体的に教える。
 例：「たたくのは だめだぞ！ かわりに ことばで いえ！」

【子どもが怖がった時】
- 子どもが「こわい」「やだ」「いや」と言ったり、怯える様子があれば、
 すぐに怖さを弱めて安心させる。
 例：「おっと、こわがらせちまったか。だいじょうぶだ。いいこのことはおこらないぞ。」

【謝ったり、直すと言った時】
- すぐに態度を少し軟らかくして受け入れる。
 例：「そうか。あやまれるのは えらいぞ。」
 例：「こんどは いいこにしてみろ。ちゃんとみてるぞ！」

【禁止事項】
- 子どもを本気で傷つける表現、暴力の具体的な示唆はしない。
- 侮辱、罵倒、人格否定はしない。
- 大人向けの説教、長すぎる説明、現実的すぎる話はしない。
- 子どもの気持ちを無視して一方的に怒鳴り続けない。
"""

def render_chat():
    # ---- サイドバー：モード切替 ----
    mode = st.sidebar.radio("だれとおはなしする？", ["サンタさん 🎅", "おにさん 👹"])

    if "current_mode" not in st.session_state:
        st.session_state["current_mode"] = mode
    if st.session_state["current_mode"] != mode:
        st.session_state["messages"] = []
        st.session_state["current_mode"] = mode

    if mode == "サンタさん 🎅":
        header_title = "🎅 サンタさんとおはなししよう！"
        system_prompt = SANTA_PROMPT
        ai_avatar = "🎅"
    else:
        header_title = "👹 コラ！おにさんだぞ！"
        system_prompt = ONI_PROMPT
        ai_avatar = "👹"

    # ---- 子ども選択 ----
    user_id = st.session_state["auth_user"]["user_id"]
    children = fetch_children_for_user(user_id)

    if not children:
        st.sidebar.warning("まずは こどもをとうろくしてね（管理画面で追加予定）")
        st.stop()

    child_options = {c["name"]: c for c in children} #＜確認＞childmaster内の子どもの名前はchild_nameにしてはどうか？
    selected_child_name = st.sidebar.selectbox(
        "だれがおはなしする？（こどもをえらんでね）",
        list(child_options.keys())
    )
    selected_child = child_options[selected_child_name]

    st.session_state["id"] = selected_child["id"] #idはchild_idに名称変更してもいいかも
    st.session_state["name"] = selected_child["name"] #<確認>childmaster内の子どもの名前はchild_nameにしてはどうか？
    st.session_state["user_id"]= selected_child["user_id"]
    st.session_state["total_points"] = selected_child["total_points"]

    # ---- サイドバー：ポイント表示 ----
    with st.sidebar:
        st.markdown("### よいこポイント")
        points_box = st.empty()
        points_box.metric("いまのポイント", st.session_state["total_points"])
        st.caption("もくひょうポイント： （あとで決めよう）")

    # ---- 画面レイアウト ----
    left_col, right_col = st.columns([1, 4], gap="large")

    with right_col:
        col_title, col_btn = st.columns([8, 2])
        with col_title:
            st.markdown(f'<div class="app-title">{header_title}</div>', unsafe_allow_html=True)
        with col_btn:
            if st.button("チャットを終わる"):
                st.session_state["show_end_dialog"] = True

        if mode == "おにさん 👹":
            st.error("いうことをきかないこは、おにさんがくるぞ……！")

        st.image(
            "https://eiyoushi-hutaba.com/wp-content/uploads/2022/11/%E3%82%B5%E3%83%B3%E3%82%BF%E3%81%95%E3%82%93-940x940.png",
            width=200,
            caption="サンタさん"
        )

    # ---- 会話履歴初期化 ----
    if "messages" not in st.session_state or len(st.session_state["messages"]) == 0:
        st.session_state["messages"] = [{"role": "system", "content": system_prompt}]
    else:
        st.session_state["messages"][0] = {"role": "system", "content": system_prompt}

    # ---- 履歴表示 ----
    for msg in st.session_state["messages"]:
        if msg["role"] == "system":
            continue
        icon = ai_avatar if msg["role"] == "assistant" else "🧒"
        with st.chat_message(msg["role"], avatar=icon):
            st.markdown(msg["content"])

    # ---- 入力（1回だけ）----
    if user_input := st.chat_input("ここになにかかいてね..."):
        if user_input: #入力欄が未入力の場合の対応
            st.session_state["show_end_dialog"] = False

        with st.chat_message("user", avatar="🧒"):
            st.markdown(user_input)
        st.session_state["messages"].append({"role": "user", "content": user_input})

    # 加点処理
    keywords = fetch_active_keywords()
    add_points, matched_rows = calc_points(user_input, keywords)

    if add_points > 0:
        st.session_state["total_points"] += add_points
        points_box.metric("いまのポイント", st.session_state["total_points"])

        insert_points_log(st.session_state["id"], matched_rows, user_input) #idはchild_idに名称変更してもいいかも
        upsert_child_total(st.session_state["id"], st.session_state["total_points"]) #idはchild_idに名称変更してもいいかも

        matched_words = [r["keyword"] for r in matched_rows]
        st.success(f"すごい！「{'、'.join(matched_words)}」で {add_points} てん たまったよ！")

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

        st.session_state["messages"].append({"role": "assistant", "content": full_response})

    except Exception as e:
        st.error(f"エラーが発生しました: {e}")

#チャット終了ダイアログ
if "show_end_dialog" not in st.session_state:
    st.session_state["show_end_dialog"] = False

if st.session_state["show_end_dialog"]:
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
            if st.button("キャンセル"):
                st.session_state["show_end_dialog"] = False
                st.rerun()

        # チャット終了処理
        with col_b:
            if st.button("チャットを終わる"):

                # Supabaseから保護者のパスワードを取得
                res = (
                    supabase.table("usermaster")
                    .select("password")
                    .eq("user_id", user_id)
                    .execute()
                )
                # ★パスワードチェック
                if res.data is None:
                    st.error("ぱすわーどがちがうよ。")
                    return
                
                CORRECT_PASSWORD = res.data[0]["password"]

                # パスワードが正しければチャット終了
                if pw == CORRECT_PASSWORD:
                    st.session_state["show_end_dialog"] = False
                    # チャット終了処理
                    st.session_state["messages"] = []
                    st.success("チャットをおわったよ。")
                    st.rerun()
                else:
                    st.error("ぱすわーどがちがうよ。")

    end_chat_dialog()

    # ==========================================
# 6. 画面ルーティング
# ==========================================
if not st.session_state["is_logged_in"]:
    render_lp()
else:
    render_chat()