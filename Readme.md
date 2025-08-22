# French Transition QA Tool

A **Streamlit application** for quality assurance checks on French transition phrases between news paragraphs.

---

## ✨ Features
- **Word Count Check**: Transitions ≤ 5 words  
- **Position Validation**: Only allowed in final paragraphs  
- **Repetition Detection**: spaCy lemmatization to catch repeated words  
- **Semantic Similarity**: Sentence-transformers for cohesion scoring  
- **Interactive Results**: Color-coded table + summary stats  
- **Export Options**: Download results as CSV or HTML  

---

## ⚙️ Installation
```bash
✅pip install -r requirements.txt
✅python -m spacy download fr_core_news_md


🧩 Models
✅spaCy: fr_core_news_md (French lemmatization & parsing)
✅Sentence Transformers: paraphrase-multilingual-MiniLM-L12-v2 (semantic similarity)

📊 Thresholds
Word Count: ≤ 5
✅Semantic Similarity: Next > Previous
✅Repetition: Zero tolerance within same article
✅Position: Must be in final paragraph

▶️ Running Locally
✅QA Tool Prototype App.py
✅Open http://localhost:8501  in your browser.

💻 Running on Replit
✅pip install -r requirements.txt
✅python -m spacy download fr_core_news_md
✅streamlit run app.py --server.enableCORS=false --server.enableXsrfProtection=false

📂 Input Format
CSV file with columns:
  ✅article_id
  ✅para_idx
  ✅transition_text
  ✅previous_paragraph
  ✅next_paragraph

📤 Output
✅Pass/Fail results table with explanations
✅Compliance statistics
✅Most repeated lemmas visualization
✅Export options (CSV/HTML)

📜 License
✅This project was created for contest submission purposes.