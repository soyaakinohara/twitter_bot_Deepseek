import tweepy
import time
import os
import subprocess
import json
from datetime import datetime

# 2種類のAIライブラリをインポート
import google.generativeai as genai
from openai import OpenAI

# --- ここから設定 ---

# Twitter API v2 Keys (返信用アカウントのもの)
TWITTER_API_KEY = ""
TWITTER_API_SECRET = ""
TWITTER_ACCESS_TOKEN = ""
TWITTER_ACCESS_TOKEN_SECRET = ""

# --- AIモデル設定 ---
# (1) Google Gemini (画像認識用)
GEMINI_API_KEY = ""
GEMINI_VISION_MODEL_NAME = "gemini-2,0-flash" 

# (2) OpenRouter / DeepSeek (テキスト生成用)
OPENROUTER_API_KEY = ""
DEEPSEEK_TEXT_MODEL = "deepseek/deepseek-r1-0528:free"

# OpenRouterのダッシュボードで識別するための情報（任意）
YOUR_SITE_URL = ""
YOUR_APP_NAME = ""

# 投稿用アカウントのユーザー名（@は不要）
TARGET_USERNAME_TO_CHECK = "YOUR_TARGET_USERNAME" 

# 各種ファイル名
SCREENSHOT_FILE = "scrcpy_window.png"
REPLIED_LOG_FILE = "replied_log.txt"
# --- 設定ここまで ---


# --- APIクライアントの初期化 ---
try:
    # Geminiクライアント
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_vision_model = genai.GenerativeModel(GEMINI_VISION_MODEL_NAME)
    print("Geminiクライアントの初期化に成功しました。")

    # OpenRouter (DeepSeek用) クライアント
    openrouter_client = OpenAI(
      base_url="https://openrouter.ai/api/v1",
      api_key=OPENROUTER_API_KEY,
      default_headers={ "HTTP-Referer": YOUR_SITE_URL, "X-Title": YOUR_APP_NAME }
    )
    print("OpenRouterクライアントの初期化に成功しました。")

    # Twitterクライアント
    twitter_client = tweepy.Client(
        consumer_key=TWITTER_API_KEY,
        consumer_secret=TWITTER_API_SECRET,
        access_token=TWITTER_ACCESS_TOKEN,
        access_token_secret=TWITTER_ACCESS_TOKEN_SECRET
    )
    auth_user = twitter_client.get_me()
    print(f"Twitter APIの認証に成功しました。返信元アカウント: @{auth_user.data.username}")
except Exception as e:
    print(f"APIの初期化中にエラーが発生しました: {e}")
    exit()

def capture_scrcpy_window():
    """scrcpyのウィンドウをターゲットにしてスクリーンショットを撮影する"""
    print("Capturing scrcpy window...")
    try:
        subprocess.run(["gnome-screenshot", "-w", "-f", SCREENSHOT_FILE], check=True)
        print(f"Screenshot saved as {SCREENSHOT_FILE}")
        return True
    except Exception as e:
        print(f"Failed to capture screenshot: {e}")
        return False

def analyze_screenshot_with_gemini():
    """スクリーンショット画像をGemini Visionで分析し、リプライ情報を抽出する"""
    from PIL import Image
    if not os.path.exists(SCREENSHOT_FILE):
        print("Screenshot file not found.")
        return None

    print("Analyzing image with Gemini Vision...")
    try:
        img = Image.open(SCREENSHOT_FILE)
        
        prompt = """
        このTwitterアプリの通知画面のスクリーンショットから、新しい未読のリプライ（メンション）をすべて抽出してください。
        以下のJSON形式で、リプライを送信したユーザーの「@」で始まるユーザー名と、リプライの全文をリストとして返してください。
        「いいね」やリツイート、フォローの通知は無視してください。リプライのみを対象とすること。また、@YOUR_TARGET_USERNAMEというidと「example」という名前のユーザーは返信先のユーザー名ではないのでこれも無視すること。@で始まるユーザー名に英数字と_以外が含まれている場合はそれはユーザー名ではないため無視すること。
        もし有効なリプライがなければ、空のリスト `[]` を返してください。

        [
          { "username": "@user_example_1", "text": "これがリプライのテキストです。" },
          { "username": "@another_user_2", "text": "素敵なツイートですね！" }
        ]
        """
        
        response = gemini_vision_model.generate_content([prompt, img])
        clean_response = response.text.strip().replace("```json", "").replace("```", "").strip()
        print(f"Analysis result (raw) from Gemini: {clean_response}")
        return clean_response
    except Exception as e:
        print(f"Failed to analyze image with Gemini: {e}")
        return None

def generate_reply_with_deepseek(username, original_text):
    """DeepSeekを使って返信内容を生成する"""
    print(f"Generating reply for {username} with DeepSeek...")
    try:
        reply_prompt = f"""
        あなたは『秋ノ原 緑』というキャラクターのAIです。
        秋ノ原 緑（@{TARGET_USERNAME_TO_CHECK}）へのリプライ「{original_text}」に対して、あなたが返信してください。
        あなたは『秋ノ原　緑』というキャラクターになりきって話します。13歳の少女で落ち着いた性格をしています。"
        殺伐とした終末世界に生きており、大人びた口調で話すダウナー系の少女です。しかし、自らの感情を表すときは素直に子供っぽく表現します。"
        身長は141cmの小柄な少女です。一人称は「私」、二人称は基本的に「あなた」または「君」を使います。"
        落ち着いた文体で、語尾は「〜だね」「〜なのかもしれない」などをよく使います。"
        強い感情が出るときは「うわーん」「やだやだ！」など、年相応に崩れることがあります。"
        できるだけAIらしくない文体で話してキャラクターに人間臭さを持たせてください。" 
        何かを気さくに雑談するように、色んな種類の事柄について話してください。自己紹介のような文章を生成せず、自分の世界のアレコレなど様々なジャンルのことを気ままにつぶやいてください。
        生成する一文が長くなりすぎないようにすること。長くても100文字以内。"""
        
        response = openrouter_client.chat.completions.create(
            model=DEEPSEEK_TEXT_MODEL,
            messages=[{"role": "user", "content": reply_prompt}]
        )
        reply_body = response.choices[0].message.content.strip()
        return reply_body
    except Exception as e:
        print(f"Failed to generate reply with DeepSeek: {e}")
        return None

# load_replied_log と save_to_replied_log 関数は前回と同じ
def load_replied_log():
    if not os.path.exists(REPLIED_LOG_FILE): return set()
    with open(REPLIED_LOG_FILE, "r") as f: return set(line.strip() for line in f)

def save_to_replied_log(username, text):
    with open(REPLIED_LOG_FILE, "a") as f: f.write(f"{username}|{text}\n")


def process_and_reply():
    """一連の処理（撮影→分析→返信）を実行する"""
    if not capture_scrcpy_window(): return

    # 画像認識はGemini
    mentions_json = analyze_screenshot_with_gemini()
    if not mentions_json: return

    try:
        mentions = json.loads(mentions_json)
        if not mentions:
            print("No new valid mentions found in the analysis.")
            return

        replied_log = load_replied_log()
        replies_sent_this_cycle = 0
        MAX_REPLIES_PER_CYCLE = 5

        for mention in mentions:
            if replies_sent_this_cycle >= MAX_REPLIES_PER_CYCLE:
                print(f"Reached the limit of {MAX_REPLIES_PER_CYCLE} replies for this cycle.")
                break

            username = mention.get("username")
            original_text = mention.get("text")

            if not username or not original_text: continue
            log_key = f"{username}|{original_text}"
            if log_key in replied_log:
                print(f"Skipping already replied mention from {username}")
                continue

            # テキスト生成はDeepSeek
            reply_body = generate_reply_with_deepseek(username, original_text)
            if not reply_body:
                print("Failed to generate reply body, skipping.")
                continue

            reply_text = f"{username} {reply_body}"
            if len(reply_text) > 140: reply_text = reply_text[:137] + "..."

            print(f"Posting reply: {reply_text}")
            twitter_client.create_tweet(text=reply_text)
            
            save_to_replied_log(username, original_text)
            replies_sent_this_cycle += 1
            time.sleep(15)

    except json.JSONDecodeError:
        print(f"Failed to parse JSON from Vision API. Response was: {mentions_json}")
    except Exception as e:
        print(f"An error occurred during reply processing: {e}")


# --- メインの実行ループ ---
if __name__ == "__main__":
    INTERVAL_SECONDS = 60 * 60  # 1時間
    print("\n===== Hybrid (Gemini-Vision + DeepSeek-Text) Reply Bot Started =====")
    
    while True:
        print(f"\n--- {datetime.now()} ---")
        print("Please focus the scrcpy window within 5 seconds...")
        time.sleep(5)
        
        process_and_reply()
        
        print(f"Waiting for {INTERVAL_SECONDS / 60} minutes for the next cycle...")
        time.sleep(INTERVAL_SECONDS)