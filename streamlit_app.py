import json

import streamlit as st
from google import genai
from google.genai import types


# ----------------------------
# ページ設定
# ----------------------------
st.set_page_config(
    page_title="指示の曖昧さチェッカー",
    page_icon="🔎",
    layout="wide",
)

st.title("🔎 指示の曖昧さチェッカー")
st.write(
    "仕事の依頼文をAIが分析し、不足している情報を指摘します。"
    "さらに、分かりやすく具体的な依頼文に書き換えます。"
)


# ----------------------------
# Gemini APIの設定
# ----------------------------
MODEL = "gemini-3.8-flash"

api_key = st.text_input(
    "Gemini API Key",
    type="password",
    help="Google AI Studioで取得したAPIキーを入力してください。",
)

# APIキーが未入力なら、Streamlit Secretsも確認
if not api_key:
    try:
        api_key = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        api_key = ""


# ----------------------------
# AIへの指示
# ----------------------------
SYSTEM_INSTRUCTION = """
あなたは、仕事の依頼文の曖昧さを分析する専門アシスタントです。

ユーザーが入力した最新の依頼文を分析してください。

次の観点を確認してください。
1. 期限：いつまでに完了する必要があるか
2. 担当者：誰が作業するのか
3. 目的：何のために作業するのか
4. 成果物：何を提出するのか
5. 完成条件：どのような状態なら完成なのか
6. 対象・範囲：どの資料や業務を対象にするのか
7. 形式・分量：ファイル形式、ページ数、文字数など
8. 優先順位：他の仕事との優先度

すべての項目を機械的に問題扱いせず、
入力文に必要な情報がすでにあれば、不足項目に含めないでください。

改善後の依頼文を作成するときのルール：
- 入力文に記載されていない事実を勝手に確定しない
- 不明な期限や担当者は「［要確認：期限］」などの
  プレースホルダーを使用する
- 必要以上に長い依頼文にしない
- 実際の業務ですぐ使える自然な日本語にする
- 不足項目がない場合は、その旨を伝える

必ず次のJSON形式で回答してください。
Markdownのコードブロックで囲まず、JSONのみを返してください。

{
  "summary": "依頼文の総評",
  "issues": [
    {
      "item": "不足項目",
      "problem": "何が曖昧なのか",
      "reason": "なぜ明確にする必要があるのか"
    }
  ],
  "improved_text": "改善後の依頼文",
  "questions": [
    "依頼者に確認すべき質問"
  ]
}
"""


# ----------------------------
# 分析結果の表示
# ----------------------------
def display_result(original_text, result):
    st.markdown("### 🔎 分析結果")
    st.write(result.get("summary", "分析が完了しました。"))

    issues = result.get("issues", [])

    if issues:
        st.markdown("#### ⚠️ 不足している項目")

        for issue in issues:
            with st.expander(
                f"🔸 {issue.get('item', '確認項目')}",
                expanded=True,
            ):
                st.markdown("**問題点**")
                st.write(issue.get("problem", ""))

                st.markdown("**指摘する理由**")
                st.write(issue.get("reason", ""))
    else:
        st.success("明確にすべき不足項目は見つかりませんでした。")

    questions = result.get("questions", [])

    if questions:
        st.markdown("#### ❓ 追加で確認したいこと")
        for question in questions:
            st.markdown(f"- {question}")

    st.markdown("### 📝 元の文章と改善後の文章")

    original_col, improved_col = st.columns(2)

    with original_col:
        st.markdown("#### 📄 元の文章")
        st.text_area(
            "元の依頼文",
            value=original_text,
            height=220,
            disabled=True,
            key=f"original_{len(original_text)}_{hash(original_text)}",
        )

    with improved_col:
        st.markdown("#### ✨ 改善後の文章")
        improved_text = result.get("improved_text", "")

        st.text_area(
            "改善された依頼文",
            value=improved_text,
            height=220,
            disabled=True,
            key=f"improved_{len(original_text)}_{hash(original_text)}",
        )

        if improved_text:
            st.code(improved_text, language=None)

    st.caption(
        "※ 改善後の文章にある［要確認］の部分は、"
        "実際の業務に合わせて補完してください。"
    )


# ----------------------------
# チャット履歴
# ----------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []


with st.sidebar:
    st.markdown("### 💡 入力例")

    examples = [
        "この資料、なるべく早くいい感じにまとめておいて",
        "来週の会議で使う資料を作ってください",
        "顧客向けのメールを適切な感じで修正してください",
    ]

    for example in examples:
        if st.button(example, use_container_width=True):
            st.session_state.pending_prompt = example

    if st.button("🗑️ 履歴をクリア", use_container_width=True):
        st.session_state.messages = []
        st.session_state.pop("pending_prompt", None)
        st.rerun()


# 過去の会話を表示
for index, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        if message["role"] == "user":
            st.markdown(message["content"])
        else:
            display_result(
                message["original_text"],
                message["result"],
            )


# ----------------------------
# 入力と分析
# ----------------------------
prompt = st.chat_input(
    "チェックしたい仕事の依頼文を入力してください..."
)

# サイドバーの入力例にも対応
if st.session_state.get("pending_prompt"):
    prompt = st.session_state.pop("pending_prompt")


if prompt:
    if not api_key:
        st.warning(
            "Gemini APIキーを入力してください。"
            "Google AI StudioでAPIキーを取得できます。"
        )
        st.stop()

    # ユーザーの入力を保存・表示
    st.session_state.messages.append(
        {"role": "user", "content": prompt}
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            client = genai.Client(api_key=api_key)

            with st.spinner("依頼文の曖昧さを分析しています..."):
                response = client.models.generate_content(
                    model=MODEL,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        response_mime_type="application/json",
                        temperature=0.2,
                    ),
                )

            result = json.loads(response.text)

            # 分析結果を表示
            display_result(prompt, result)

            # 次回の再描画でも表示できるように保存
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "original_text": prompt,
                    "result": result,
                }
            )

        except json.JSONDecodeError:
            st.error(
                "AIの回答をJSONとして読み取れませんでした。"
                "もう一度お試しください。"
            )

        except Exception as e:
            st.error(f"分析中にエラーが発生しました: {e}")
            st.info(
                "APIキー、利用モデル、APIの利用制限、"
                "インターネット接続を確認してください。"
            )
