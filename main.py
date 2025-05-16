from flask import Flask, render_template, request, redirect, url_for
import json
import os
import datetime

app = Flask(__name__)

REVIEW_DAYS = [1, 2, 3, 5, 7, 9, 12, 14, 17, 21]
DATA_FILE = "vocab_data.json"
ERROR_FILE = "error_summary.txt"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_review_words(data):
    today = datetime.date.today()
    review = []
    for word, info in data.items():
        if info.get("completed"):
            continue
        reviews = info.get("reviews", [])
        if not reviews:
            review.append((word, info))
        else:
            days_since = (today - datetime.datetime.strptime(info["start_date"], "%Y-%m-%d").date()).days
            if REVIEW_DAYS and (not set(REVIEW_DAYS).isdisjoint(set([days_since]))):
                review.append((word, info))
    return review

def get_error_words(data):
    return [(word, info) for word, info in data.items() if info.get("wrong")]

@app.route("/", methods=["GET", "POST"])
def index():
    data = load_data()
    message = ""

    if request.method == "POST":
        if "new_word" in request.form:
            word = request.form["new_word"].strip()
            meaning = request.form["meaning"].strip()
            if word and word not in data:
                data[word] = {
                    "meaning": meaning,
                    "start_date": str(datetime.date.today()),
                    "reviews": [],
                    "completed": False,
                    "wrong": False
                }
                message = f"添加成功：{word}"
            else:
                message = "单词已存在或无效"

        elif "review_action" in request.form:
            word = request.form["review_action"]
            action = request.form[f"action_{word}"]
            start_date = datetime.datetime.strptime(data[word]["start_date"], "%Y-%m-%d").date()
            days_since = (datetime.date.today() - start_date).days
            data[word]["reviews"].append(days_since)
            if action == "no":
                data[word]["wrong"] = True
            if sorted(data[word]["reviews"]) == REVIEW_DAYS:
                data[word]["completed"] = True

        elif "delete_word" in request.form:
            word = request.form["delete_word"]
            if word in data:
                del data[word]

        elif "export_errors" in request.form:
            with open(ERROR_FILE, "w", encoding="utf-8") as f:
                for word, info in get_error_words(data):
                    f.write(f"{word} - {info['meaning']}\n")
            message = "错词已导出为 error_summary.txt"

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

@app.route("/import_vocab", methods=["POST"])
def import_vocab():
    file = request.files.get("vocab_file")
    if file and file.filename.endswith(".json"):
        try:
            imported_data = json.load(file)
            data = load_data()
            data.update(imported_data)
            save_data(data)
            return redirect("/")
        except Exception as e:
            return f"导入失败：{e}", 400
    return "无效的文件类型", 400

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)


