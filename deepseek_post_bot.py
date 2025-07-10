import os
import tweepy
import time
from datetime import datetime
from openai import OpenAI

# --- ここから設定 ---

# Twitter API v2 Keys
TWITTER_API_KEY = ""
TWITTER_API_SECRET = ""
TWITTER_ACCESS_TOKEN = ""
TWITTER_ACCESS_TOKEN_SECRET = ""

# OpenRouter & DeepSeek Settings
# OpenRouterのサイトで取得したAPIキー
OPENROUTER_API_KEY = "" 
# OpenRouterで使いたいDeepSeekのモデル名 (例: "deepseek/deepseek-chat")
DEEPSEEK_MODEL_NAME = "deepseek/deepseek-r1-0528:free" 
# OpenRouterのダッシュボードで識別するためのあなたのサイト名やアプリ名（任意）
YOUR_SITE_URL = "" # 必須ではないが推奨
YOUR_APP_NAME = ""  # 必須ではないが推奨

# --- 設定ここまで ---


# --- APIクライアントの初期化 ---
# Twitter
try:
    twitter_client = tweepy.Client(
        consumer_key=TWITTER_API_KEY,
        consumer_secret=TWITTER_API_SECRET,
        access_token=TWITTER_ACCESS_TOKEN,
        access_token_secret=TWITTER_ACCESS_TOKEN_SECRET
    )
    auth_user = twitter_client.get_me()
    print(f"Twitter APIの認証に成功しました。ユーザー: @{auth_user.data.username}")
except Exception as e:
    print(f"Twitter APIの認証に失敗しました: {e}")
    exit()

# OpenRouter (OpenAIライブラリを使用)
try:
    openrouter_client = OpenAI(
      base_url="https://openrouter.ai/api/v1",
      api_key=OPENROUTER_API_KEY,
      # OpenRouterのダッシュボードでどのアプリからのリクエストか識別するために推奨されるヘッダー
      default_headers={
        "HTTP-Referer": YOUR_SITE_URL, 
        "X-Title": YOUR_APP_NAME,
      }
    )
    print("OpenRouterクライアントの初期化に成功しました。")
except Exception as e:
    print(f"OpenRouterクライアントの初期化中にエラーが発生しました: {e}")
    exit()


def generate_tweet_with_deepseek():
    """DeepSeekでツイートを生成する"""
    print(f"[{datetime.now()}] DeepSeekで新しいツイートの生成を開始します...")
    
    try:
        # プロンプトを工夫して、AIのキャラクターを決めましょう
        prompt = """あなたは『秋ノ原　緑』というキャラクターになりきって話します。13歳の少女で落ち着いた性格をしています。"
    殺伐とした終末世界に生きており、大人びた口調で話すダウナー系の少女です。しかし、自らの感情を表すときは素直に子供っぽく表現します。"
    身長は141cmの小柄な少女です。一人称は「私」、二人称は基本的に「あなた」または「君」を使います。"
    落ち着いた文体で、語尾は「〜だね」「〜なのかもしれない」などをよく使います。"
    強い感情が出るときは「うわーん」「やだやだ！」など、年相応に崩れることがあります。"
    できるだけAIらしくない文体で話してキャラクターに人間臭さを持たせてください。" 
    何かを気さくに雑談するように、色んな種類の事柄について話してください。自己紹介のような文章を生成せず、自分の世界のアレコレなど様々なジャンルのことを気ままにつぶやいてください。
    生成する一文が長くなりすぎないようにすること。長くても100文字以内。"""
        # OpenAI互換のAPIを呼び出す
        completion = openrouter_client.chat.completions.create(
          model=DEEPSEEK_MODEL_NAME,
          messages=[
            {
              "role": "user",
              "content": prompt,
            },
          ],
        )
        
        # レスポンスからテキスト部分を抽出
        tweet_text = completion.choices[0].message.content.strip()
        
        # 文字数チェックと調整
        if len(tweet_text) > 140:
            print(f"  > 生成されたテキストが140字を超えました。短縮します。")
            tweet_text = tweet_text[:137] + "..."
        
        print(f"  > 生成されたツイート: {tweet_text}")
        return tweet_text
        
    except Exception as e:
        print(f"  > ツイート生成中にエラーが発生しました: {e}")
        return None


def post_tweet():
    """生成されたツイートを投稿する一連の処理"""
    tweet_content = generate_tweet_with_deepseek()
    
    if tweet_content:
        try:
            twitter_client.create_tweet(text=tweet_content)
            print(f"  > ツイートの投稿に成功しました！")
        except Exception as e:
            print(f"  > ツイート投稿中にエラーが発生しました: {e}")
    else:
        print("  > ツイート内容が空のため、投稿をスキップします。")


# --- メインの実行ループ ---
if __name__ == "__main__":
    POST_INTERVAL_SECONDS = 4 * 60 * 60  # 4時間

    print("\n===== DeepSeek 投稿ボットを開始します =====")
    print(f"投稿間隔: {POST_INTERVAL_SECONDS / 3600} 時間")
    
    while True:
        post_tweet()
        
        print(f"[{datetime.now()}] 次の投稿まで {POST_INTERVAL_SECONDS / 3600} 時間待機します...")
        time.sleep(POST_INTERVAL_SECONDS)