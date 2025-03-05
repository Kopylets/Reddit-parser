from flask import Flask, render_template
import sqlite3

app = Flask(__name__)

def get_posts():
    try:
        conn = sqlite3.connect('reddit_posts.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM posts ORDER BY id DESC")
        posts = cursor.fetchall()
        conn.close()
        
        formatted_posts = []
        for post in posts:
            formatted_posts.append({
                'id': post[0],
                'subreddit': post[1],
                'url': post[2],
                'title': post[3],
                'content': post[4]
            })
        return formatted_posts
    except sqlite3.Error as e:
        print(f"error while getting posts: {e}")
        return []

@app.route('/')
def index():
    posts = get_posts()
    return render_template('index.html', posts=posts)

if __name__ == '__main__':
    app.run(debug=True)