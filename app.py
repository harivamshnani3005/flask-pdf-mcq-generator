from flask import Flask, render_template, request
import pdfplumber, nltk, random, os, re
from nltk.corpus import wordnet

app = Flask(__name__)
os.makedirs("uploads", exist_ok=True)

# ------------------ NLTK Setup ------------------
nltk.download("punkt", quiet=True)
nltk.download("wordnet", quiet=True)
nltk.download("omw-1.4", quiet=True)

# ------------------ UTILITIES ------------------
def extract_text(path):
    """Extract text from a PDF file."""
    text = ""
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text += t + " "
    return re.sub(r"\s+", " ", text).strip()

def pick_concept(sentence):
    """Pick a strong concept word from the sentence."""
    words = re.findall(r"\b[A-Za-z']+\b", sentence)
    cand = [w for w in words if len(w) >= 8] or [w for w in words if len(w) >= 6] or words
    return sorted(cand, key=len, reverse=True)[0] if cand else None

def get_related_concepts(concept, global_used, limit=10):
    """Fetch related words for MCQ options."""
    related = set()
    try:
        for syn in wordnet.synsets(concept):
            for lemma in syn.lemmas():
                w = lemma.name().replace("_", " ").lower()
                if w.isalpha() and w != concept.lower():
                    related.add(w)
                for ant in lemma.antonyms():
                    related.add(ant.name().replace("_", " ").lower())
                if len(related) >= limit:
                    break
            if len(related) >= limit:
                break
    except Exception:
        pass

    base_words = [
        "framework", "method", "process", "system", "model", "principle",
        "strategy", "approach", "function", "definition", "application",
        "analysis", "mechanism", "structure", "evaluation", "concept"
    ]
    while len(related) < 6:
        related.add(random.choice(base_words))
    final = [r for r in related if r not in global_used]
    random.shuffle(final)
    return final[:limit]

# ------------------ GENERATE QUESTIONS ------------------
def generate_blank_mcqs(text, count=5):
    """Generate fill-in-the-blank questions with 4 options each."""
    sentences = nltk.sent_tokenize(text)
    sentences = [s.strip() for s in sentences if len(s.split()) >= 6]
    if not sentences:
        return []

    def complexity(s):
        words = len(s.split())
        clauses = s.count(",") + s.count("that") + s.count("which") + s.count("because")
        return words + 2 * clauses

    sentences = sorted(sentences, key=lambda x: complexity(x), reverse=True)
    pool = sentences[:max(count * 15, 300)]

    mcqs, used_concepts = [], set()
    random.shuffle(pool)

    for sent in pool:
        if len(mcqs) >= count:
            break
        concept = pick_concept(sent)
        if not concept:
            continue
        c_lower = concept.lower()
        if c_lower in used_concepts:
            continue
        used_concepts.add(c_lower)

        # Replace one concept word with a blank
        pattern = re.compile(r"\b" + re.escape(concept) + r"\b", re.IGNORECASE)
        blank_sentence = pattern.sub("_____", sent, count=1)

        # Create 4 options
        related = get_related_concepts(concept, used_concepts, limit=10)
        distractors = [r for r in related if r.lower() != c_lower]
        while len(distractors) < 3:
            filler = random.choice(["process", "method", "principle", "framework"])
            if filler not in distractors:
                distractors.append(filler)
        options = random.sample(distractors, 3) + [c_lower]
        random.shuffle(options)

        mcqs.append({
            "q_no": len(mcqs) + 1,
            "question": blank_sentence,
            "options": options,
            "answer": c_lower
        })

    return mcqs

# ------------------ FLASK ROUTES ------------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    f = request.files.get("pdf")
    if not f:
        return "No file uploaded", 400
    n = min(int(request.form.get("num_questions", 5)), 100)
    path = os.path.join("uploads", f.filename)
    f.save(path)
    text = extract_text(path)
    mcqs = generate_blank_mcqs(text, n)
    return render_template("results.html", mcqs=mcqs, total=len(mcqs))

@app.route("/submit", methods=["POST"])
def submit():
    total = int(request.form.get("total_questions", 0))
    score = 0
    results = []
    for i in range(1, total + 1):
        user = request.form.get(f"q{i}", "No Answer")
        correct = request.form.get(f"a{i}")
        qtext = request.form.get(f"text{i}")
        opts = request.form.getlist(f"opt{i}")
        if user.lower() == correct.lower():
            score += 1
        results.append({
            "qno": i,
            "question": qtext,
            "options": opts,
            "user": user,
            "correct": correct
        })
    return render_template("score.html", score=score, total=total, results=results)

if __name__ == "__main__":
    app.run(debug=True)
