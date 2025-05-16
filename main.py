from flask import Flask, render_template, request, redirect, url_for, send_file
import json
import os
import datetime

app = Flask(__name__)

DATA_FILE = "vocab_data.json"
ERROR_FILE = "error_summary.txt"
REVIEW_DAYS = [1, 2, 3, 5, 7, 9, 12, 14, 17, 21]

# 加载数据
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

# 保存数据
def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# 获取今天需要复习的单词
def get_review_words(data):
    today = datetime.date.today()
    review_words = []
    for word, info in data.items():
        if info.get("completed"):
            continue
        start = datetime.datetime.strptime(info["start_date"], "%Y-%m-%d").date()
        days_since = (today - start).days
        for d in REVIEW_DAYS:
            if 0 < d <= days_since and d not in info["reviews"]:
                review_words.append((word, info))
                break
    return review_words

# 获取错误单词
def get_error_words(data):
    return [(word, info) for word, info in data.items() if info.get("wrong")]

# 导出错词
def export_errors(errors):
    with open(ERROR_FILE, 'w', encoding='utf-8') as f:
        for word, info in errors:
            f.write(f"{word} - {info['meaning']} (记录于 {info['start_date']})\n")

@app.route('/', methods=['GET', 'POST'])
def index():
    data = load_data()
    message = ""

    if request.method == 'POST':
        if 'new_word' in request.form:
            word = request.form['new_word'].strip()
            meaning = request.form['meaning'].strip()
            if word and word not in data:
                data[word] = {
                    "meaning": meaning,
                    "start_date": str(datetime.date.today()),
                    "reviews": [],
                    "completed": False,
                    "wrong": False
                }
                message = f"✅ 添加成功：{word}"
            else:
                message = "⚠️ 单词已存在或无效"

        elif 'review_action' in request.form:
            word = request.form['review_action']
            action = request.form[f'action_{word}']
            start_date = datetime.datetime.strptime(data[word]["start_date"], "%Y-%m-%d").date()
            days_since = (datetime.date.today() - start_date).days
            data[word]["reviews"].append(days_since)
            if action == 'no':
                data[word]["wrong"] = True
            if sorted(data[word]["reviews"]) == REVIEW_DAYS:
                data[word]["completed"] = True

        elif 'delete_word' in request.form:
            word = request.form['delete_word']
            if word in data:
                del data[word]
                message = f"🗑️ 已删除：{word}"

        elif 'export_errors' in request.form:
            errors = get_error_words(data)
            export_errors(errors)
            return send_file(ERROR_FILE, as_attachment=True)

    save_data(data)
    review_words = get_review_words(data)
    errors = get_error_words(data)
    stats = {
        "total": len(data),
        "completed": sum(1 for v in data.values() if v["completed"]),
        "errors": len(errors),
        "pending": len(review_words)
    }
    return render_template("index.html", data=data, review_words=review_words, errors=errors, stats=stats, message=message)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)


