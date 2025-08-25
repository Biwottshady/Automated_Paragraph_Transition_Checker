# app.py
"""
French Transition QA Tool - Enhanced for Contest Requirements
Features added:
 - Translation verification reminder + accuracy reminder panels
 - Parsing & evaluation guidance (Part 1 & Part 2 summary)
 - Blacklist of generic fillers flagged as failure
 - Language toggle (default: French, optional English)
 - Per-article analytics + Global view (keeps all previous functionality)
 - Correction suggestions, exports, visualizations
 - Clear Replit submission reminder banner
Notes:
 - Requires: streamlit, pandas, sentence-transformers, spacy (optional but recommended), PyPDF2, python-docx, matplotlib
 - If spaCy or sentence-transformers models cannot be downloaded automatically in your environment, install them manually in your venv:
     pip install spacy sentence-transformers
     python -m spacy download fr_core_news_sm
"""

import streamlit as st
import pandas as pd
import re
import io
import zipfile
import PyPDF2
from docx import Document
import matplotlib.pyplot as plt
from collections import Counter
import warnings
warnings.filterwarnings('ignore')

# -----------------------
# Page config
# -----------------------
st.set_page_config(
    page_title="French Transition QA Tool",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------
# Global constants/resources
# -----------------------
FRENCH_STOPWORDS = {
    "alors","au","aucuns","aussi","autre","avant","avec","avoir","bon","car","ce","cela",
    "ces","ceux","chaque","ci","comme","comment","dans","des","du","dedans","dehors",
    "depuis","devrait","doit","donc","dos","droite","début","elle","elles","en","encore",
    "essai","est","et","eu","fait","faites","fois","font","force","haut","hors","ici",
    "il","ils","je","juste","la","le","les","leur","là","ma","maintenant","mais","mes",
    "mine","moins","mon","mot","même","ni","nommés","notre","nous","nouveaux","ou",
    "où","par","parce","parole","pas","personnes","peut","peu","pièce","plupart","pour",
    "pourquoi","quand","que","quel","quelle","quelles","quels","qui","sa","sans","ses",
    "seulement","si","sien","son","sont","sous","soyez","sujet","sur","ta","tandis","tellement",
    "tels","tes","ton","tous","tout","trop","très","va","voient","vont","votre","vous","vu","ça","étaient","état","étions","été","être"
}

TRANSITION_SYNONYMS = {
    "en conclusion": ["pour conclure", "en définitive", "en somme", "au final"],
    "pour conclure": ["en conclusion", "en définitive", "en somme", "au final"],
    "pour résumer": ["en résumé", "en bref", "bref", "en somme"],
    "en résumé": ["pour résumer", "en bref", "bref", "en somme"],
    "finalement": ["au final", "en définitive", "in fine"],
    "cependant": ["pourtant", "néanmoins", "toutefois"],
    "toutefois": ["cependant", "néanmoins", "malgré tout"],
    "néanmoins": ["toutefois", "cependant", "malgré tout"],
    "ainsi": ["de ce fait", "par conséquent", "donc"],
    "par conséquent": ["en conséquence", "de ce fait", "dès lors"],
    "en revanche": ["au contraire", "à l’inverse", "pour autant"],
    "en bref": ["bref", "pour résumer", "en résumé"],
}

CONNECTOR_BANK = {
    "conclusion": ["en conclusion", "pour conclure", "en définitive", "en somme", "au final"],
    "cause_effect": ["ainsi", "par conséquent", "de ce fait", "en conséquence", "dès lors"],
    "contrast": ["cependant", "toutefois", "néanmoins", "en revanche", "au contraire"],
    "addition": ["de plus", "en outre", "par ailleurs", "de surcroît", "également"],
    "summary": ["en résumé", "pour résumer", "bref", "en bref"]
}

# Generic filler blacklist (these are considered too generic and can be flagged)
GENERIC_FILLERS = {
    "par ailleurs",
    "en outre",
    "dans un autre registre",
    "d'une part",
    "d'autre part",
    "de plus",
    "pour autant",
    "en revanche"  # sometimes fine, but repeated usage may be flagged
}

# -----------------------
# UI Texts for i18n (English/French)
# -----------------------
UI = {
    "fr": {
        "title": "📰 Outil QA - Transitions Françaises",
        "subtitle": "Analyse des transitions: cohésion, répétition, longueur, placement final.",
        "upload_prompt": "Glissez-déposez vos fichiers (ZIP/TXT/PDF/DOCX) contenant `Titre:`, contenu, et `Transitions générées:`",
        "replit_note": "⚠️ IMPORTANT: Pour la soumission du concours, fournissez également un lien Replit fonctionnel montrant l'app Streamlit en cours d'exécution.",
        "translation_verification_title": "🔍 Vérification de Traduction (Requise)",
        "translation_verification_text": (
            "Avant la soumission, vérifiez manuellement quelques exemples via DeepL/Google Translate "
            "pour confirmer que:\n• les répétitions sémantiques sont détectées (mêmes lemmes)\n"
            "• la cohésion thématique (transition → paragraphe suivant) est correcte\n\n"
            "Sans cette vérification, certaines erreurs linguistiques peuvent entraîner un rejet."
        ),
        "accuracy_reminder_title": "✅ Rappel d'Exactitude",
        "accuracy_reminder_text": (
            "Un test doit :\n"
            "- Échouer si la transition répète un autre lemme ou est non-thématique.\n"
            "- Passer si elle est différente et thématiquement liée.\n"
            "Si la majorité des vérifications ne sont pas fiables, la soumission sera rejetée."
        ),
        "parsing_instructions_title": "📑 Parsing & Règles (Part 1)",
        "parsing_instructions_text": (
            "Parsing clé: chaque transition doit être correctement isolée et associée aux paragraphes précédent/suivant.\n"
            "Exemple correct: 'Titre:', contenu, 'Transitions générées:' (numérotées)."
        ),
        "upload_button": "Commencer l'analyse",
        "language_label": "Langue de l'interface",
        "help_panel": "Aide & Exemples",
        "rules_a": "Rule A — Longueur (≤ 5 mots)",
        "rules_b": "Rule B — Détection de répétition (lemme/root)",
        "rules_c": "Rule C — Cohésion thématique (next > prev)"
    },
    "en": {
        "title": "📰 French Transition QA Tool",
        "subtitle": "Analyze transitions: cohesion, repetition, length, final placement.",
        "upload_prompt": "Upload files (ZIP/TXT/PDF/DOCX) containing `Titre:`, content, and `Transitions générées:`",
        "replit_note": "⚠️ IMPORTANT: For contest submission include a working Replit link showing the Streamlit app running.",
        "translation_verification_title": "🔍 Translation Verification (Required)",
        "translation_verification_text": (
            "Before submission, manually check a few examples with DeepL/Google Translate "
            "to confirm:\n• semantic repetition is detected (same lemmas)\n• thematic cohesion (transition → next paragraph)\n\n"
            "Without this check some French expressions may be misclassified."
        ),
        "accuracy_reminder_title": "✅ Accuracy Reminder",
        "accuracy_reminder_text": (
            "A test should:\n"
            "- Fail if the transition repeats another lemma or is thematically unrelated.\n"
            "- Pass if it is different and thematically linked.\n"
            "If most checks are unreliable the submission will be rejected."
        ),
        "parsing_instructions_title": "📑 Parsing & Rules (Part 1)",
        "parsing_instructions_text": (
            "Parsing is key: each transition must be isolated and linked to previous/next paragraphs.\n"
            "Correct example: 'Titre:', content, 'Transitions générées:' (numbered)."
        ),
        "upload_button": "Start analysis",
        "language_label": "Interface language",
        "help_panel": "Help & Examples",
        "rules_a": "Rule A — Word limit (≤ 5 words)",
        "rules_b": "Rule B — Repetition detection (lemma/root)",
        "rules_c": "Rule C — Thematic cohesion (next > prev)"
    }
}

# -----------------------
# Custom CSS + Background
# -----------------------
st.markdown("""
<style>
/* Background editorial image + vignette */
[data-testid="stAppViewContainer"] {
    background-image: url("https://images.unsplash.com/photo-1519337265831-281ec6cc8514?q=80&w=2000&auto=format&fit=crop");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}
[data-testid="stAppViewContainer"]::before {
    content: "";
    position: fixed;
    inset: 0;
    background: rgba(12, 18, 28, 0.52);
    z-index: 0;
}
/* Make main content readable */
.block-container { position: relative; z-index: 1; background: rgba(255,255,255,0.92);
  backdrop-filter: blur(2px); border-radius: 12px; padding: 1rem; box-shadow: 0 10px 30px rgba(0,0,0,0.12); }
/* Sidebar readability */
[data-testid="stSidebar"] > div:first-child { background: rgba(255,255,255,0.96); backdrop-filter: blur(3px); }
/* Headers & badges */
.header-container { position: relative; width: 100%; height: 260px; border-radius: 12px; overflow: hidden; margin-bottom: 1rem; box-shadow: 0 6px 18px rgba(0,0,0,0.18); }
.header-image { width: 100%; height: 100%; object-fit: cover; opacity: 0.85; }
.header-overlay { position: absolute; inset:0; background: linear-gradient(135deg, rgba(31,119,180,0.85), rgba(44,62,80,0.85)); display:flex; align-items:center; justify-content:center; flex-direction:column; color:white; text-align:center; padding:1.5rem; }
.header-title { font-size: 2.2rem; font-weight:800; margin-bottom: .2rem; }
.header-subtitle { font-size:1rem; opacity: .95; max-width:900px; }

/* Metric card */
.metric-card { background: linear-gradient(135deg,#667eea,#764ba2); padding: .9rem; border-radius:10px; color:white; text-align:center; box-shadow:0 6px 18px rgba(0,0,0,0.12); }
.metric-value { font-size:1.4rem; font-weight:700; }
.rule-box { background:#f8f9fa; padding:.7rem; border-left:4px solid #6c757d; border-radius:8px; margin-bottom:.5rem; }
.success-box { background:linear-gradient(135deg,#d4edda,#c3e6cb); padding:.7rem; border-left:5px solid #28a745; border-radius:8px; }

/* small tweaks */
.stButton>button { background: linear-gradient(90deg,#1f77b4,#2c3e50); color: #fff; border-radius:6px; }
</style>
""", unsafe_allow_html=True)

# -----------------------
# Header
# -----------------------
# Language selection default = French
lang = st.sidebar.radio("Langue / Language", options=["Français", "English"], index=0)
lang_code = "fr" if lang.startswith("Fr") else "en"
texts = UI[lang_code]

# Header banner
st.markdown(f"""
<div class="header-container">
  <img class="header-image"
       src="https://images.unsplash.com/photo-1588681664899-f142ff2dc9b1?ixlib=rb-4.0.3&auto=format&fit=crop&w=1800&q=80"
       alt="Editorial background">
  <div class="header-overlay">
    <div class="header-title">{texts['title']}</div>
    <div class="header-subtitle">{texts['subtitle']}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# Replit reminder
st.info(texts["replit_note"])

# -----------------------
# Model loading
# -----------------------
@st.cache_resource
def load_spacy_model():
    """Try to load spaCy French model; fallback to None with warning."""
    try:
        import spacy
        try:
            return spacy.load("fr_core_news_sm")
        except OSError:
            st.warning("⚠️ spaCy French model not found. Attempting automatic download...")
            try:
                import spacy.cli
                spacy.cli.download("fr_core_news_sm")
                return spacy.load("fr_core_news_sm")
            except Exception as e:
                st.error(f"❌ Could not download spaCy model: {e}")
                st.warning("⚠️ Falling back to simple tokenization and no lemmatization.")
                return None
    except Exception as e:
        st.error(f"❌ spaCy import failed: {e}")
        return None

@st.cache_resource
def load_sentence_model():
    """Load sentence-transformers; try main id then fallback."""
    try:
        from sentence_transformers import SentenceTransformer
        try:
            return SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        except Exception:
            # alternative id
            return SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
    except Exception as e:
        st.error(f"❌ Error loading sentence transformer: {e}")
        try:
            from sentence_transformers import SentenceTransformer
            st.warning("⚠️ Trying fallback model distiluse-base-multilingual-cased")
            return SentenceTransformer('distiluse-base-multilingual-cased')
        except Exception as fallback_error:
            st.error(f"❌ Fallback model failed: {fallback_error}")
            return None

@st.cache_resource
def initialize_models():
    nlp = load_spacy_model()
    sentence_model = load_sentence_model()
    if sentence_model is None:
        st.error("❌ Cannot proceed without sentence transformer model (required for cohesion scoring).")
        st.stop()
    return nlp, sentence_model

# -----------------------
# Sidebar controls
# -----------------------
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/france-circular.png", width=72)
    st.markdown("<h3 style='text-align:center;margin-top:-8px'>French Transition QA</h3>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("### ⚙️ Configuration / Configuration")
    word_limit = st.number_input("Word limit / Limite de mots", min_value=3, max_value=8, value=5, step=1)
    similarity_threshold = st.slider(
        "Cohesion Δ threshold (next - prev) / Seuil Δ cohésion",
        min_value=0.0, max_value=0.5, value=0.10, step=0.01
    )
    st.markdown("---")
    st.markdown("### 📏 Quick Rules")
    st.markdown(f"<div class='rule-box'><strong>{texts['rules_a']}</strong>: ≤ {word_limit} words</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='rule-box'><strong>{texts['rules_b']}</strong></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='rule-box'><strong>{texts['rules_c']}</strong>: Δ ≥ {similarity_threshold:.2f}</div>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown(f"🧾 {texts['help_panel']}")
    if st.button("Show contest parsing & examples / Afficher les consignes"):
        st.session_state.show_help = not st.session_state.get("show_help", False)

# -----------------------
# File parsing utilities
# -----------------------
def extract_text_from_pdf(pdf_file):
    text = ""
    try:
        reader = PyPDF2.PdfReader(pdf_file)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
    return text

def extract_text_from_txt(txt_file):
    try:
        return txt_file.getvalue().decode('utf-8', errors='ignore')
    except Exception as e:
        st.error(f"Error reading TXT: {e}")
        return ""

def extract_text_from_docx(docx_file):
    try:
        doc = Document(io.BytesIO(docx_file.read()))
        return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    except Exception as e:
        st.error(f"Error reading DOCX: {e}")
        return ""

def extract_texts_from_zip(zip_file):
    texts = []
    try:
        with zipfile.ZipFile(zip_file) as z:
            for name in z.namelist():
                if name.lower().endswith(".txt"):
                    with z.open(name) as f:
                        try:
                            content = f.read().decode('utf-8', errors='ignore')
                            texts.append(content)
                        except Exception:
                            pass
    except Exception as e:
        st.error(f"Error reading ZIP: {e}")
    return "\n\n".join(texts)

def extract_text(uploaded_file):
    ext = uploaded_file.name.split('.')[-1].lower()
    if ext == 'pdf':
        return extract_text_from_pdf(uploaded_file)
    elif ext == 'txt':
        return extract_text_from_txt(uploaded_file)
    elif ext == 'docx':
        return extract_text_from_docx(uploaded_file)
    elif ext == 'zip':
        return extract_texts_from_zip(uploaded_file)
    else:
        st.error(f"Unsupported file type: {ext}. Only ZIP, PDF, TXT, DOCX allowed.")
        return ""

# -----------------------
# Article parsing
# -----------------------
def parse_articles_from_text(text):
    articles = []
    lines = text.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("Titre:"):
            current_article = {"title": "", "content": "", "transitions": []}
            current_article["title"] = line.replace("Titre:", "").strip()
            i += 1
            article_content = ""
            while i < len(lines):
                line = lines[i].strip()
                if line.startswith("Transitions générées:"):
                    i += 1
                    while i < len(lines):
                        line = lines[i].strip()
                        # break on next article header or blank line
                        if line.startswith("Titre:") or not line:
                            break
                        if line and not line.startswith("="):
                            transition = re.sub(r'^\d+\.\s*', '', line)
                            if transition:
                                current_article["transitions"].append(transition)
                        i += 1
                    current_article["content"] = article_content.strip()
                    if current_article["title"] and current_article["transitions"]:
                        articles.append(current_article)
                    break
                else:
                    if not line.startswith(("Chapeau:", "À savoir également")):
                        article_content += line + " "
                    i += 1
        else:
            i += 1
    return articles

def create_dataframe_from_articles(articles):
    data = []
    for article_idx, article in enumerate(articles):
        content = article["content"]
        title = article["title"]
        transitions = article["transitions"]
        for trans_idx, transition in enumerate(transitions):
            transition_pos = content.find(transition)
            if transition_pos != -1:
                before_transition = content[:transition_pos].strip()
                after_transition = content[transition_pos + len(transition):].strip()
                if before_transition:
                    before_sentences = [s.strip() + "." for s in re.split(r'[.!?]+', before_transition) if s.strip()]
                    prev_para = before_sentences[-1] if before_sentences else ""
                else:
                    prev_para = ""
                if after_transition:
                    after_sentences = [s.strip() + "." for s in re.split(r'[.!?]+', after_transition) if s.strip()]
                    next_para = after_sentences[0] if after_sentences else ""
                else:
                    next_para = ""
                total_sentences = len([s for s in re.split(r'[.!?]+', content) if s.strip()])
                para_idx = max(1, total_sentences - len(transitions) + trans_idx)
                data.append({
                    "article_id": article_idx + 1,
                    "article_title": title,
                    "para_idx": para_idx,
                    "transition_text": transition,
                    "previous_paragraph": prev_para,
                    "next_paragraph": next_para
                })
    return pd.DataFrame(data)

# -----------------------
# NLP helpers / QA checks
# -----------------------
def basic_tokenize(text):
    toks = [w.lower() for w in re.findall(r'\b[\wéèêëàâîïôöùûüç-]+\b', text, flags=re.UNICODE)]
    return [t for t in toks if t not in FRENCH_STOPWORDS and t.isalpha() and len(t) > 2]

def lemmatize(text, nlp):
    if nlp is None:
        return basic_tokenize(text)
    try:
        doc = nlp(text)
        return [t.lemma_.lower() for t in doc if not t.is_stop and not t.is_punct and t.is_alpha and len(t.text) > 2]
    except Exception:
        return basic_tokenize(text)

def check_word_count(transition_text, limit=5):
    words = re.findall(r'\b\w+\b', transition_text, flags=re.UNICODE)
    return len(words) <= limit, len(words)

def check_final_position(article_data, article_id, para_idx):
    article_paragraphs = article_data[article_data['article_id'] == article_id]
    if article_paragraphs.empty:
        return False
    max_para_idx = article_paragraphs['para_idx'].max()
    # Contest demands final paragraph strictly (as per Part 1)
    return para_idx >= max_para_idx

def check_repetition(article_data, article_id, transition_text, nlp):
    article_transitions = article_data[article_data['article_id'] == article_id]['transition_text'].tolist()
    other_transitions = [t for t in article_transitions if t != transition_text]
    if not other_transitions:
        return True, []
    trans_lemmas = set(lemmatize(transition_text, nlp))
    repeated = set()
    for other in other_transitions:
        other_lemmas = set(lemmatize(other, nlp))
        repeated.update(trans_lemmas.intersection(other_lemmas))
    return len(repeated) == 0, sorted(list(repeated))

def compute_similarity(text1, text2, model):
    if not text1 or not text2 or not text1.strip() or not text2.strip():
        return 0.0
    try:
        from sentence_transformers import util
        emb = model.encode([text1, text2], convert_to_tensor=True)
        sim = util.pytorch_cos_sim(emb[0], emb[1])
        return float(sim.item())
    except Exception:
        return 0.0

def check_cohesion(sim_prev, sim_next, threshold=0.1):
    return (sim_next - sim_prev) >= threshold, (sim_next - sim_prev)

# -----------------------
# Enhanced analyze with filler blacklist & translation reminder flags
# -----------------------
def analyze_transitions(df, nlp, sentence_model, similarity_threshold, limit_words):
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    total = len(df)
    for idx, row in df.iterrows():
        article_id = row['article_id']
        para_idx = row['para_idx']
        transition_text = row['transition_text'].strip()
        prev_para = row['previous_paragraph']
        next_para = row['next_paragraph']

        progress = (idx + 1) / total
        progress_bar.progress(progress)
        status_text.text(f"Processing {idx + 1}/{total}: {transition_text[:60]}…")

        wc_ok, actual_wc = check_word_count(transition_text, limit_words)
        pos_ok = check_final_position(df, article_id, para_idx)
        rep_ok, repeated_lemmas = check_repetition(df, article_id, transition_text, nlp)

        sim_prev = compute_similarity(transition_text, prev_para, sentence_model)
        sim_next = compute_similarity(transition_text, next_para, sentence_model)
        coh_ok, coh_diff = check_cohesion(sim_prev, sim_next, similarity_threshold)

        # Generic filler detection
        normalized = transition_text.lower().strip().replace("’", "'")
        filler_flag = any(normalized == f for f in GENERIC_FILLERS)

        passes_all = wc_ok and pos_ok and rep_ok and coh_ok and not filler_flag

        failure_reasons, triggered_rules = [], []
        if not wc_ok:
            failure_reasons.append(f"Word count ({actual_wc} > {limit_words})")
            triggered_rules.append("Word Count")
        if not pos_ok:
            failure_reasons.append("Not in final paragraph")
            triggered_rules.append("Position")
        if not rep_ok:
            failure_reasons.append("Lemma repetition: " + ", ".join(repeated_lemmas[:5]))
            triggered_rules.append("Repetition")
        if not coh_ok:
            failure_reasons.append(f"Poor cohesion (Δ={coh_diff:.3f} < {similarity_threshold})")
            triggered_rules.append("Cohesion")
        if filler_flag:
            failure_reasons.append("Generic filler phrase (too generic / non-specific)")
            triggered_rules.append("Generic Filler")

        # Add a 'translation_check_recommended' flag: when sim values are ambiguous or small
        translation_check_recommended = False
        # if cohesion diff close to threshold or sim scores low -> recommend human translation verification
        if abs(coh_diff) < (similarity_threshold * 0.5) or max(sim_next, sim_prev) < 0.25:
            translation_check_recommended = True

        results.append({
            'article_id': article_id,
            'article_title': row['article_title'],
            'para_idx': para_idx,
            'transition_text': transition_text,
            'word_count_ok': wc_ok,
            'final_position_ok': pos_ok,
            'repetition_ok': rep_ok,
            'cohesion_ok': coh_ok,
            'similarity_prev': sim_prev,
            'similarity_next': sim_next,
            'cohesion_diff': coh_diff,
            'generic_filler': filler_flag,
            'pass_fail': 'Pass' if passes_all else 'Fail',
            'failure_reason': "; ".join(failure_reasons) if failure_reasons else "Pass",
            'triggered_rule': ", ".join(triggered_rules) if triggered_rules else "None",
            'repeated_lemmas': repeated_lemmas,
            'translation_check_recommended': translation_check_recommended
        })

    progress_bar.empty()
    status_text.empty()
    return pd.DataFrame(results)

# -----------------------
# Suggestions / Corrections
# -----------------------
def trim_to_limit(transition_text, limit=5):
    tokens = re.findall(r'\b\w+\b', transition_text, flags=re.UNICODE)
    trimmed = " ".join(tokens[:limit])
    if transition_text.strip().endswith(('.', '…', '!', '?')):
        return trimmed + transition_text.strip()[-1]
    return trimmed

def suggest_synonym(transition_text, avoid_lemmas):
    key = transition_text.strip().lower().replace("’", "'")
    candidates = TRANSITION_SYNONYMS.get(key, [])
    keep = []
    for c in candidates:
        c_lemmas = set(basic_tokenize(c))
        if not c_lemmas.intersection(avoid_lemmas):
            keep.append(c)
    if not keep:
        for group in CONNECTOR_BANK.values():
            for c in group:
                if not set(basic_tokenize(c)).intersection(avoid_lemmas):
                    keep.append(c)
    seen = set(); dedup = []
    for c in keep:
        if c not in seen:
            dedup.append(c); seen.add(c)
    return dedup[:4]

def build_corrections(results_df, nlp, limit_words, sim_threshold):
    corrections = []
    for _, r in results_df.iterrows():
        if r['pass_fail'] == 'Pass':
            continue
        reasons = []
        suggestion = r['transition_text']
        avoid = set(r['repeated_lemmas']) if isinstance(r['repeated_lemmas'], list) else set()

        if not r['word_count_ok']:
            reasons.append(f"Reduce to ≤ {limit_words} words")
            suggestion = trim_to_limit(suggestion, limit_words)

        if not r['repetition_ok']:
            reasons.append("Avoid repeated lemmas: " + ", ".join(sorted(list(avoid))[:5]))
            alts = suggest_synonym(suggestion, avoid)
            if alts:
                suggestion = alts[0]

        if not r['cohesion_ok']:
            reasons.append(f"Increase thematic cohesion (Δ < {sim_threshold})")
            # propose connectors likely to improve coherence, filtered by avoid list
            alts = CONNECTOR_BANK["cause_effect"] + CONNECTOR_BANK["contrast"] + CONNECTOR_BANK["summary"]
            alts = [a for a in alts if not set(basic_tokenize(a)).intersection(avoid)]
            if alts and suggestion == r['transition_text']:
                suggestion = alts[0]

        if r['generic_filler']:
            reasons.append("Avoid generic filler; prefer a topic-specific connector")

        if not r['final_position_ok']:
            reasons.append("Place transition in the final paragraph")

        corrections.append({
            "article_id": r['article_id'],
            "article_title": r['article_title'],
            "para_idx": r['para_idx'],
            "original_transition": r['transition_text'],
            "suggested_transition": suggestion,
            "reason": "; ".join(reasons) if reasons else "Improvement suggested",
            "translation_check_recommended": r.get('translation_check_recommended', False)
        })
    return pd.DataFrame(corrections)

# -----------------------
# Lemma analytics
# -----------------------
def top_repeated_lemmas(results_df, nlp, topn=15):
    lemma_counter = Counter()
    for _, r in results_df.iterrows():
        lemmas = lemmatize(r['transition_text'], nlp)
        lemma_counter.update(lemmas)
    top = lemma_counter.most_common(topn)
    return pd.DataFrame(top, columns=["lemma", "count"])

# -----------------------
# Visualization helpers
# -----------------------
def style_pass_fail(val):
    color = '#27ae60' if val == 'Pass' else '#e74c3c'
    return f'color: {color}; font-weight: bold'

def plot_rule_breakdown(results_df):
    rule_violations = {
        'Word Count': (~results_df['word_count_ok']).sum(),
        'Position': (~results_df['final_position_ok']).sum(),
        'Repetition': (~results_df['repetition_ok']).sum(),
        'Cohesion': (~results_df['cohesion_ok']).sum(),
        'Generic Filler': results_df['generic_filler'].sum()
    }
    fig, ax = plt.subplots(figsize=(6, 3.6))
    ax.bar(list(rule_violations.keys()), list(rule_violations.values()))
    ax.set_title('Rule Violations Distribution')
    ax.set_ylabel('Count'); ax.set_xlabel('Rule')
    plt.xticks(rotation=15, ha='right')
    st.pyplot(fig); plt.close()

def plot_pass_fail(results_df):
    figpf, axpf = plt.subplots(figsize=(5.0, 3.6))
    pass_count = (results_df['pass_fail'] == 'Pass').sum()
    fail_count = (results_df['pass_fail'] == 'Fail').sum()
    if pass_count + fail_count > 0:
        axpf.pie([pass_count, fail_count], labels=['Pass','Fail'], autopct='%1.0f%%', startangle=90)
    axpf.set_title('Overall Compliance')
    st.pyplot(figpf); plt.close()

def plot_cohesion_hist(results_df, threshold):
    fig2, ax2 = plt.subplots(figsize=(6, 3.6))
    ax2.hist(results_df['cohesion_diff'], bins=15)
    ax2.axvline(x=threshold, linestyle='--', color='red')
    ax2.set_title('Cohesion Δ Histogram (next - prev)')
    ax2.set_xlabel('Δ'); ax2.set_ylabel('Frequency')
    st.pyplot(fig2); plt.close()

# -----------------------
# Main
# -----------------------
def main():
    # Load models
    with st.spinner("🚀 Loading NLP models and sentence-transformer..."):
        nlp, sentence_model = initialize_models()

    # Info panels (translation verification & accuracy reminder)
    st.markdown(f"### {texts['translation_verification_title']}")
    st.info(texts['translation_verification_text'])
    st.markdown(f"### {texts['accuracy_reminder_title']}")
    st.info(texts['accuracy_reminder_text'])
    with st.expander(texts['parsing_instructions_title']):
        st.write(texts['parsing_instructions_text'])
        st.markdown("**Parsing Examples / Exemples de parsing:**")
        st.markdown("- Correct / Correct : `Titre: Mon article` then content then `Transitions générées:` with numbered phrases.")
        st.markdown("- Incorrect / Incorrect : transitions merged into one line or not numbered/attached to wrong paragraph.")

    # Upload
    st.markdown('<div class="sub-header">📤 Upload Files</div>', unsafe_allow_html=True)
    uploaded_files = st.file_uploader(
        texts['upload_prompt'],
        type=["zip", "pdf", "txt", "docx"],
        accept_multiple_files=True
    )
    if not uploaded_files:
        st.info("👆 " + ("Please upload files to begin analysis." if lang_code == "en" else "Veuillez téléverser des fichiers pour commencer l'analyse."))
        return

    # Parse & analyze
    try:
        all_articles = []
        for uploaded_file in uploaded_files:
            st.info(f"Processing: {uploaded_file.name}")
            text = extract_text(uploaded_file)
            if not text:
                st.warning(f"No text extracted from {uploaded_file.name}")
                continue
            articles = parse_articles_from_text(text)
            if articles:
                st.success(f"Found {len(articles)} article(s) with transitions in {uploaded_file.name}")
                all_articles.extend(articles)
            else:
                st.warning(f"No articles found in {uploaded_file.name}")

        if not all_articles:
            st.error("No articles with transitions found. Check file structure.")
            return

        df = create_dataframe_from_articles(all_articles)
        if df.empty:
            st.error("No transitions could be extracted from parsed articles.")
            return

        st.success(f"✅ Extracted {len(df)} transitions across {len({a['title'] for a in all_articles})} article(s)")

        # Run analysis
        with st.spinner("🔍 Running QA checks..."):
            results_all = analyze_transitions(df, nlp, sentence_model, similarity_threshold, word_limit)

        # Tabs: global & per-article
        tab_global, tab_article = st.tabs(["🌐 Global View", "📄 Per-Article View"])

        # Global view
        with tab_global:
            st.markdown('<div class="sub-header">📊 QA Results (All Articles)</div>', unsafe_allow_html=True)
            colf1, colf2, colf3 = st.columns([1,1,2])
            show_only_fails = colf1.checkbox("Show only fails (global)", value=False, key="global_fails")
            rule_filter = colf2.multiselect("Filter by failed rule", options=["Word Count","Position","Repetition","Cohesion","Generic Filler"], default=[])
            sort_by_delta = colf3.checkbox("Sort by weakest cohesion Δ (asc)", value=True, key="global_sort")

            filtered_global = results_all.copy()
            if show_only_fails:
                filtered_global = filtered_global[filtered_global['pass_fail'] == 'Fail']
            if rule_filter:
                mask = filtered_global['triggered_rule'].apply(lambda s: any(r in s for r in rule_filter))
                filtered_global = filtered_global[mask]
            if sort_by_delta:
                filtered_global = filtered_global.sort_values(by="cohesion_diff", ascending=True)

            display_df_global = filtered_global.drop(columns=['repeated_lemmas'], errors='ignore')
            st.dataframe(display_df_global.style.applymap(style_pass_fail, subset=['pass_fail']), height=420, use_container_width=True)

            # Global analytics
            st.markdown('<div class="sub-header">🌐 Global Analytics</div>', unsafe_allow_html=True)
            g1, g2 = st.columns(2)
            with g1:
                plot_rule_breakdown(results_all)
                plot_pass_fail(results_all)
            with g2:
                plot_cohesion_hist(results_all, similarity_threshold)
                worst = results_all.nsmallest(10, 'cohesion_diff')[['article_id','article_title','para_idx','transition_text','cohesion_diff','pass_fail']]
                st.caption("Weakest cohesion examples (lowest Δ)")
                st.dataframe(worst, use_container_width=True, height=240)

            # Top repeated lemmas global
            st.markdown('<div class="sub-header">🔁 Top Repeated Lemmas (Global)</div>', unsafe_allow_html=True)
            top_lemmas_df_global = top_repeated_lemmas(results_all, nlp, topn=15)
            coltl1, coltl2 = st.columns([1,1])
            with coltl1:
                st.dataframe(top_lemmas_df_global, use_container_width=True, height=360)
            with coltl2:
                fig3, ax3 = plt.subplots(figsize=(6,4))
                if not top_lemmas_df_global.empty:
                    ax3.barh(top_lemmas_df_global['lemma'][::-1], top_lemmas_df_global['count'][::-1])
                ax3.set_title('Most Frequent Lemmas in Transitions (Global)')
                ax3.set_xlabel('Count'); ax3.set_ylabel('Lemma')
                st.pyplot(fig3); plt.close()

            # Corrections (global)
            st.markdown('<div class="sub-header">🛠️ Correction Suggestions (Global)</div>', unsafe_allow_html=True)
            corr_df_global = build_corrections(results_all, nlp, word_limit, similarity_threshold)
            if corr_df_global.empty:
                st.markdown("<div class='success-box'><strong>🎉 All good!</strong> No corrections needed — all transitions passed.</div>", unsafe_allow_html=True)
            else:
                st.dataframe(corr_df_global, use_container_width=True, height=360)
                csv_corr = corr_df_global.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download Correction Summary (CSV, Global)", csv_corr, "transition_corrections_global.csv", "text/csv", use_container_width=True)

            # Exports (global)
            st.markdown('<div class="sub-header">💾 Export Results (Global)</div>', unsafe_allow_html=True)
            colx1, colx2 = st.columns(2)
            with colx1:
                csv = results_all.drop('repeated_lemmas', axis=1).to_csv(index=False)
                st.download_button("📥 Download CSV Results (Global)", csv, "transition_qa_results_global.csv", "text/csv", use_container_width=True)
            with colx2:
                html = results_all.drop('repeated_lemmas', axis=1).to_html(index=False, escape=False)
                st.download_button("📥 Download HTML Report (Global)", html, "transition_qa_report_global.html", "text/html", use_container_width=True)

        # Per-Article view
        with tab_article:
            st.markdown('<div class="sub-header">📄 Select Article</div>', unsafe_allow_html=True)
            article_options = results_all[['article_id','article_title']].drop_duplicates().sort_values('article_id')
            article_label_map = {row.article_id: f"{row.article_id} — {row.article_title}" for _, row in article_options.iterrows()}

            selected_article_id = st.selectbox("Choose an article / Choisir un article", options=list(article_label_map.keys()), format_func=lambda k: article_label_map[k])
            article_df = results_all[results_all['article_id'] == selected_article_id].copy()

            st.markdown('<div class="sub-header">📊 QA Results (This Article)</div>', unsafe_allow_html=True)
            colA1, colA2, colA3 = st.columns([1,1,2])
            show_only_fails_a = colA1.checkbox("Show only fails (article)", value=False, key="article_fails")
            rule_filter_a = colA2.multiselect("Filter by failed rule", options=["Word Count","Position","Repetition","Cohesion","Generic Filler"], default=[], key="article_rules")
            sort_by_delta_a = colA3.checkbox("Sort by weakest cohesion Δ (asc)", value=True, key="article_sort")

            filtered_a = article_df.copy()
            if show_only_fails_a:
                filtered_a = filtered_a[filtered_a['pass_fail'] == 'Fail']
            if rule_filter_a:
                mask = filtered_a['triggered_rule'].apply(lambda s: any(r in s for r in rule_filter_a))
                filtered_a = filtered_a[mask]
            if sort_by_delta_a:
                filtered_a = filtered_a.sort_values(by="cohesion_diff", ascending=True)

            display_df_a = filtered_a.drop(columns=['repeated_lemmas'], errors='ignore')
            st.dataframe(display_df_a.style.applymap(style_pass_fail, subset=['pass_fail']), height=420, use_container_width=True)

            # Article analytics
            st.markdown('<div class="sub-header">📈 Analytics (This Article)</div>', unsafe_allow_html=True)
            pass_count = (article_df['pass_fail'] == 'Pass').sum()
            total_transitions = len(article_df)
            compliance_rate = (pass_count / total_transitions) * 100 if total_transitions else 0.0
            avg_sim_next = article_df['similarity_next'].mean()
            avg_sim_prev = article_df['similarity_prev'].mean()

            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown(f"<div class='metric-card'><div class='metric-value'>{compliance_rate:.1f}%</div><div class='metric-label'>Compliance</div></div>", unsafe_allow_html=True)
            with c2:
                st.markdown(f"<div class='metric-card'><div class='metric-value'>{pass_count}/{total_transitions}</div><div class='metric-label'>Passed</div></div>", unsafe_allow_html=True)
            with c3:
                st.markdown(f"<div class='metric-card'><div class='metric-value'>{avg_sim_next:.3f}</div><div class='metric-label'>Avg sim (next)</div></div>", unsafe_allow_html=True)
            with c4:
                st.markdown(f"<div class='metric-card'><div class='metric-value'>{avg_sim_prev:.3f}</div><div class='metric-label'>Avg sim (prev)</div></div>", unsafe_allow_html=True)

            # Per-article charts
            ga1, ga2 = st.columns(2)
            with ga1:
                plot_rule_breakdown(article_df)
                plot_pass_fail(article_df)
            with ga2:
                plot_cohesion_hist(article_df, similarity_threshold)
                worst_a = article_df.nsmallest(10, 'cohesion_diff')[['para_idx','transition_text','cohesion_diff','pass_fail']]
                st.caption("Weakest cohesion examples (this article)")
                st.dataframe(worst_a, use_container_width=True, height=240)

            # Top repeated lemmas (article)
            st.markdown('<div class="sub-header">🔁 Top Repeated Lemmas (This Article)</div>', unsafe_allow_html=True)
            top_lemmas_df_a = top_repeated_lemmas(article_df, nlp, topn=15)
            la1, la2 = st.columns([1,1])
            with la1:
                st.dataframe(top_lemmas_df_a, use_container_width=True, height=340)
            with la2:
                fig_la, ax_la = plt.subplots(figsize=(6,4))
                if not top_lemmas_df_a.empty:
                    ax_la.barh(top_lemmas_df_a['lemma'][::-1], top_lemmas_df_a['count'][::-1])
                ax_la.set_title('Most Frequent Lemmas in Transitions (Article)')
                ax_la.set_xlabel('Count'); ax_la.set_ylabel('Lemma')
                st.pyplot(fig_la); plt.close()

            # Corrections (article)
            st.markdown('<div class="sub-header">🛠️ Correction Suggestions (This Article)</div>', unsafe_allow_html=True)
            corr_df_a = build_corrections(article_df, nlp, word_limit, similarity_threshold)
            if corr_df_a.empty:
                st.markdown("<div class='success-box'><strong>🎉 All good!</strong> No corrections needed in this article.</div>", unsafe_allow_html=True)
            else:
                st.dataframe(corr_df_a, use_container_width=True, height=320)
                csv_corr_a = corr_df_a.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download Correction Summary (CSV, This Article)", csv_corr_a, f"transition_corrections_article_{selected_article_id}.csv", "text/csv", use_container_width=True)

            # Article export
            st.markdown('<div class="sub-header">💾 Export Results (This Article)</div>', unsafe_allow_html=True)
            colpx1, colpx2 = st.columns(2)
            with colpx1:
                csv_a = article_df.drop('repeated_lemmas', axis=1).to_csv(index=False)
                st.download_button(f"📥 Download CSV Results (Article {selected_article_id})", csv_a, f"transition_qa_results_article_{selected_article_id}.csv", "text/csv", use_container_width=True)
            with colpx2:
                html_a = article_df.drop('repeated_lemmas', axis=1).to_html(index=False, escape=False)
                st.download_button(f"📥 Download HTML Report (Article {selected_article_id})", html_a, f"transition_qa_report_article_{selected_article_id}.html", "text/html", use_container_width=True)

        # Footer
        st.markdown("---")
        st.markdown("<div style='text-align:center;color:#4b5563'><p>French Transition QA Tool • Prototype for Editorial QA</p><p>Powered by spaCy, Sentence Transformers, and Streamlit</p></div>", unsafe_allow_html=True)

    except Exception as e:
        st.error(f"❌ An error occurred during processing: {str(e)}")
        st.exception(e)

if __name__ == "__main__":
    main()
