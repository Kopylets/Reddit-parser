import praw
import time
import datetime
import sys
import sqlite3
import json
from openai import OpenAI

sys.stdout.reconfigure(encoding='utf-8')

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

SUBREDDITS = config["subreddits"]
INTERVAL = config.get("interval", 600)

reddit = praw.Reddit(
    client_id=config["reddit"]["client_id"],
    client_secret=config["reddit"]["client_secret"],  
    user_agent=config["reddit"]["user_agent"]
)

api = OpenAI(api_key=config["ai"]["api_key"], base_url=config["ai"]["base_url"])

system_prompt = (
    "Ты — фильтр постов. Определи, содержит ли данный пост просьбу о коммерческой помощи. "
    "Коммерческая помощь — это когда автор просит денег, предлагает платные услуги или ищет финансирование. "
    "Отвечай только 'yes' (если пост коммерческий) или 'no' (если нет)."
)

conn = sqlite3.connect("reddit_posts.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subreddit TEXT,
    url TEXT,
    title TEXT,
    content TEXT
)
""")
conn.commit()


def is_commercial_request(post_text):
    try:
        completion = api.chat.completions.create(
            model="mistralai/Mistral-7B-Instruct-v0.2",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": post_text},
            ],
            temperature=0.3,
            max_tokens=10,
        )

        response = completion.choices[0].message.content.strip().lower()
        return response == "yes"
    except Exception as e:
        print(f"critical API error: {e}")
        return False


def save_post(subreddit, url, title, content):
    cursor.execute("""
    INSERT INTO posts (subreddit, url, title, content) VALUES (?, ?, ?, ?)
    """, (subreddit, url, title, content))
    conn.commit()


def fetch_last_month_posts():
    now = datetime.datetime.now(datetime.timezone.utc)
    one_month_ago = now - datetime.timedelta(days=30)

    for subreddit in SUBREDDITS:
        print(f" {subreddit}...")
        for post in reddit.subreddit(subreddit).new(limit=12):
            post_time = datetime.datetime.fromtimestamp(post.created_utc, datetime.timezone.utc)
            if post_time < one_month_ago:
                break

            full_text = f"{post.title} {post.selftext}"
            if not is_commercial_request(full_text):
                save_post(subreddit, post.url, post.title, post.selftext)
                print(f"saved post: {post.title}")


def fetch_new_posts():
    now = datetime.datetime.now(datetime.UTC)
    ten_minutes_ago = now.timestamp() - INTERVAL

    for subreddit in SUBREDDITS:
        print(f"{subreddit}...")
        for post in reddit.subreddit(subreddit).new(limit=50):
            if post.created_utc > ten_minutes_ago:
                full_text = f"{post.title} {post.selftext}"
                if not is_commercial_request(full_text):
                    save_post(subreddit, post.url, post.title, post.selftext)
                    print(f"saved new post: {post.title}")


def stream_new_posts():
    while True:
        fetch_new_posts()
        time.sleep(INTERVAL)


if __name__ == "__main__":
    fetch_last_month_posts()
    stream_new_posts()
