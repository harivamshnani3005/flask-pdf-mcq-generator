from flask import Flask, render_template, request
import pdfplumber
import nltk
import random
import os

# Make sure NLTK punkt tokenizer is available
nltk.download('punkt', quiet=True)

app = Flask(__name__)

# ---- Function to extract text from uploaded PDF ----
def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text

# ---- Function to generate simple MCQs from extracted text ----
def generate_mcqs(text, num_questions=5):
    sentences = nltk.sent_tokenize(text)
    if len(sentences) == 0:
        return []

    questions = []
    for _ in range(min(num_questions, len(sentences))):
        sentence = random.choice(sentences)
        sentences.remove(sentence)

        # Pick a random word to hide
        words = sentence.split()
        if len(words) < 4:
            continue
        answer = random.choice(words)
        blank_sentence = sentence.replace(answer, "______", 1)

        # Generate dummy options
        options = [answer]
        while len(options) < 4:
            opt = random.choice(random.choice(sentences).split())
            if opt not in options and opt.isalpha():
                options.append(opt)
        random.shuffle(options)

        questions.append({
            "question": blank_sentence,
            "options": options,
            "answer": answer
        })
    return questions


# ---- Routes ----
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'pdf' not in request.files:
        return "No PDF file uploaded"

    pdf = request.files['pdf']
    num_questions = int(request.form.get('num_questions', 5))

    upload_path = os.path.join("uploads", pdf.filename)
    pdf.save(upload_path)

    text = extract_text_from_pdf(upload_path)
    mcqs = generate_mcqs(text, num_questions)
    return render_template('results.html', mcqs=mcqs)


# ---- Deployment-ready section ----
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
