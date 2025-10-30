import os
import random
import string
from flask import Flask, render_template, request
import pdfplumber
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize

nltk.download('punkt')

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


def extract_text_from_pdf(pdf_path):
    """Extract readable text from PDF using pdfplumber"""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                content = page.extract_text()
                if content:
                    clean_content = ''.join(ch for ch in content if ch.isprintable())
                    text += clean_content + " "
    except Exception as e:
        print("Error reading PDF:", e)
    return text


def pick_keyword(sentence):
    """Pick a keyword (important word) from a sentence"""
    words = word_tokenize(sentence)
    candidates = [w for w in words if w.isalpha() and len(w) > 4]
    if not candidates:
        return None
    return random.choice(candidates)


def generate_distractors(correct_word, all_words, num=3):
    """Pick real words from the text as distractors (not random nonsense)"""
    all_words = list(set([w for w in all_words if w.isalpha() and w.lower() != correct_word.lower()]))
    random.shuffle(all_words)
    distractors = []
    for w in all_words:
        if len(distractors) >= num:
            break
        if abs(len(w) - len(correct_word)) <= 3:  # similar size words
            distractors.append(w)
    if len(distractors) < num:
        distractors += random.sample(all_words[:10], num - len(distractors))
    return distractors[:num]


def generate_mcqs(text, num_questions=5):
    """Generate improved MCQs with realistic options"""
    sentences = sent_tokenize(text)
    all_words = word_tokenize(text)
    mcqs = []

    if not sentences:
        return []

    random.shuffle(sentences)

    for sentence in sentences:
        if len(mcqs) >= num_questions:
            break
        keyword = pick_keyword(sentence)
        if not keyword:
            continue
        question = sentence.replace(keyword, "_____", 1)
        distractors = generate_distractors(keyword, all_words, num=3)
        options = [keyword] + distractors
        random.shuffle(options)
        mcqs.append({
            "question": question,
            "options": options,
            "answer": keyword
        })
    return mcqs


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("pdf")
    num_q = request.form.get("num_questions", "5")

    try:
        num_q = int(num_q)
    except:
        num_q = 5

    if not file or file.filename == "":
        return "⚠️ No PDF selected. Please go back and try again."

    filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(filepath)

    text = extract_text_from_pdf(filepath)
    try:
        os.remove(filepath)
    except:
        pass

    if not text.strip():
        return "⚠️ No readable text found in this PDF. Try another file."

    mcqs = generate_mcqs(text, num_questions=num_q)

    if not mcqs:
        return "⚠️ Could not generate MCQs. Try a different PDF."

    return render_template("results.html", mcqs=mcqs)


if __name__ == "__main__":
    app.run(debug=True)
