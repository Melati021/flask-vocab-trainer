from flask import Flask, render_template, request, redirect, send_file
import json, os, datetime
from io import BytesIO

app = Flask(__name__)

DATA_FILE = "vocab_data.json"
REVIEW_DAYS = 3

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_review_words(data):
    today = datetime.date.today()
    review = []
    for word, info in data.items():
        if info.get("completed"):
            continue
        start_date = datetime.datetime.strptime(info["start_date"], "%Y-%m-%d").date()
        days_since = (today - start_date).days
        if len(info["reviews"]) < REVIEW_DAYS:
            review.append((word, info))
    return review

def get_error_words(data):
    return [(word, info) for word, info in data.items() if info.get("wrong")]

@app.route("/", methods=["GET", "POST"])
def index():
    data = load_data()
    message = ""
    show_meaning = []

    if request.method == "POST":
        if "new_word" in request.form:
            word = request.form["new_word"].strip()
            meaning = request.form["meaning"].strip()
            if word and word not in data:
                data[word] = {
                    "meaning": meaning,
                    "start_date": datetime.date.today().strftime("%Y-%m-%d"),
                    "reviews": [],
                    "completed": False,
                    "wrong": False
                }
                message = f"添加成功：{word}"
            else:
                message = "单词已存在或无效"

        elif "review_action" in request.form:
            word = request.form["review_action"]
            action = request.form.get(f"action_{word}")
            if word in data:
                start_date = datetime.datetime.strptime(data[word]["start_date"], "%Y-%m-%d").date()
                days_since = (datetime.date.today() - start_date).days
                data[word]["reviews"].append(days_since)
                if action == "no":
                    data[word]["wrong"] = True
                    show_meaning.append(word)
                if len(data[word]["reviews"]) >= REVIEW_DAYS:
                    data[word]["completed"] = True

        elif "delete_word" in request.form:
            word = request.form["delete_word"]
            if word in data:
                del data[word]
                message = f"已删除：{word}"

        elif "export_errors" in request.form:
            error_lines = [f"{w}: {info['meaning']}" for w, info in get_error_words(data)]
            output = BytesIO()
            output.write("\n".join(error_lines).encode("utf-8"))
            output.seek(0)
            return send_file(output, as_attachment=True, download_name="error_summary.txt", mimetype="text/plain")

        save_data(data)

    review_words = get_review_words(data)
    errors = get_error_words(data)
    stats = {
        "total": len(data),
        "completed": sum(1 for v in data.values() if v.get("completed")),
        "errors": len(errors),
        "pending": len(review_words)
    }
    return render_template("index.html", data=data, review_words=review_words, errors=errors, stats=stats, message=message, show_meaning=show_meaning)

@app.route("/import_vocab", methods=["POST"])
def import_vocab():
    data = load_data()
    file = request.files.get("vocab_file")
    if file and file.filename.endswith(".json"):
        new_data = json.load(file)
        for word, meaning in new_data.items():
            if word not in data:
                data[word] = {
                    "meaning": meaning,
                    "start_date": datetime.date.today().strftime("%Y-%m-%d"),
                    "reviews": [],
                    "completed": False,
                    "wrong": False
                }
        save_data(data)
    return redirect("/")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

