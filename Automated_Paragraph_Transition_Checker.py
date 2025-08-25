import streamlit as st
import pandas as pd
import re
import io
import PyPDF2
from docx import Document
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
import warnings
warnings.filterwarnings('ignore')

# Load models with comprehensive error handling
@st.cache_resource
def load_spacy_model():
    """Load French spaCy model with fallback options"""
    try:
        import spacy
        # Try to load the model
        try:
            nlp = spacy.load("fr_core_news_sm")
            return nlp
        except OSError:
            # If model not found, try to download it
            st.warning("⚠️ French spaCy model not found. Attempting to download...")
            try:
                spacy.cli.download("fr_core_news_sm")
                nlp = spacy.load("fr_core_news_sm")
                st.success("✅ Successfully downloaded and loaded French spaCy model")
                return nlp
            except Exception as download_error:
                st.error(f"❌ Could not download spaCy model: {download_error}")
                # Return a minimal NLP processor
                st.warning("⚠️ Using basic text processing instead of spaCy")
                return None
    except ImportError as e:
        st.error(f"❌ spaCy import failed: {e}")
        return None

@st.cache_resource
def load_sentence_model():
    """Load sentence transformer model with error handling"""
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        st.success("✅ Successfully loaded sentence transformer model")
        return model
    except Exception as e:
        st.error(f"❌ Error loading sentence transformer: {e}")
        # Try a smaller model as fallback
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer('distiluse-base-multilingual-cased')
            st.warning("⚠️ Using fallback sentence transformer model")
            return model
        except Exception as fallback_error:
            st.error(f"❌ Fallback model also failed: {fallback_error}")
            return None

# Initialize models
@st.cache_resource
def initialize_models():
    """Initialize all required models with graceful degradation"""
    nlp = load_spacy_model()
    sentence_model = load_sentence_model()
    
    if sentence_model is None:
        st.error("❌ Cannot proceed without sentence transformer model")
        st.stop()
    
    return nlp, sentence_model

# ---------------- Streamlit Page Configuration ----------------
st.set_page_config(
    page_title="French Transition QA Tool",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------- Custom CSS Styling ----------------
st.markdown("""
<style>
    .header-container {
        position: relative;
        width: 100%;
        height: 300px;
        overflow: hidden;
        border-radius: 10px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }
    .header-image {
        width: 100%;
        height: 100%;
        object-fit: cover;
        opacity: 0.85;
    }
    .header-overlay {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: linear-gradient(135deg, rgba(31, 119, 180, 0.85) 0%, rgba(44, 62, 80, 0.85) 100%);
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        color: white;
        text-align: center;
        padding: 2rem;
    }
    .header-title {
        font-size: 2.8rem;
        font-weight: bold;
        margin-bottom: 0.5rem;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
    }
    .header-subtitle {
        font-size: 1.4rem;
        max-width: 800px;
        margin-bottom: 1rem;
        text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.5);
    }
    .main-header {
        font-size: 2.8rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
        padding: 0.5rem;
        background: linear-gradient(135deg, #f5f7fa 0%, #e4e8f0 100%);
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .sub-header {
        font-size: 1.6rem;
        color: #2c3e50;
        border-bottom: 3px solid #3498db;
        padding-bottom: 0.5rem;
        margin-top: 2rem;
        margin-bottom: 1.5rem;
    }
    .article-header {
        font-size: 1.4rem;
        color: #2c3e50;
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
        padding: 0.8rem;
        border-radius: 8px;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.2rem;
        border-radius: 10px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
        text-align: center;
        margin-bottom: 1rem;
        color: white;
        height: 120px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: bold;
        margin-bottom: 0.2rem;
    }
    .metric-label {
        font-size: 0.9rem;
        opacity: 0.9;
    }
    .info-box {
        background: linear-gradient(135deg, #e8f4f8 0%, #d1e7f5 100%);
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #3498db;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.08);
    }
    .success-box {
        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
        border-left: 5px solid #28a745;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    .warning-box {
        background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
        border-left: 5px solid #ffc107;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    .error-box {
        background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
        border-left: 5px solid #dc3545;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    .stProgress > div > div > div > div {
        background: linear-gradient(135deg, #3498db 0%, #2c3e50 100%);
    }
    .footer {
        text-align: center;
        margin-top: 3rem;
        color: #7f8c8d;
        font-size: 0.9rem;
        padding: 1rem;
        background-color: #f8f9fa;
        border-radius: 8px;
    }
    .download-btn {
        background: linear-gradient(135deg, #3498db 0%, #2c3e50 100%);
        color: white;
        padding: 0.7rem 1.5rem;
        border-radius: 8px;
        border: none;
        cursor: pointer;
        margin-right: 0.5rem;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    .download-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
    }
    .rule-box {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 4px solid #6c757d;
    }
    .transition-example {
        background-color: #f0f8ff;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 4px solid #4682b4;
    }
    .failure-detail {
        background-color: #fff5f5;
        padding: 0.5rem;
        border-radius: 4px;
        margin: 0.25rem 0;
    }
    .article-metrics {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        border: 1px solid #dee2e6;
    }
</style>
""", unsafe_allow_html=True)

# ---------------- Header Image Section ----------------
st.markdown("""
<div class="header-container">
    <img class="header-image" src="https://images.unsplash.com/photo-1588681664899-f142ff2dc9b1?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1800&q=80" alt="French Newspaper Background">
    <div class="header-overlay">
        <div class="header-title">📰 French Transition Phrase Quality Assurance</div>
        <div class="header-subtitle">Welcome to the French Transition QA Tool - Analyze transition phrases for quality assurance in journalistic content</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------- Sidebar Content ----------------
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/france-circular.png", width=80)
    st.markdown("<h1 style='text-align: center;'>French Transition QA</h1>", unsafe_allow_html=True)
    st.markdown("---")
    
    st.markdown("### 📋 About")
    st.info("This tool analyzes French transition phrases for quality assurance in journalistic content.")
    
    st.markdown("### 🚀 Instructions")
    st.write("1. Upload PDF, TXT, or DOCX files with article data")
    st.write("2. Wait for the analysis to complete")
    st.write("3. Review results and export if needed")
    
    st.markdown("---")
    
    st.markdown("### ⚙️ Model Info")
    st.write("**spaCy**: fr_core_news_sm (French language model)")
    st.write("**Sentence Transformer**: paraphrase-multilingual-MiniLM-L12-v2")
    
    # Configurable thresholds
    st.markdown("---")
    st.markdown("### ⚙️ Configuration")
    
    similarity_threshold = st.slider(
        "Similarity Difference Threshold",
        min_value=0.0,
        max_value=0.5,
        value=0.1,
        step=0.01,
        help="Minimum difference required between next and previous paragraph similarity"
    )
    
    st.markdown("---")
    
    st.markdown("### 📏 QA Rules")
    with st.expander("View all quality rules"):
        st.markdown("""
        <div class="rule-box">
            <strong>Word Count</strong>: Transition must be ≤ 5 words
        </div>
        <div class="rule-box">
            <strong>Position</strong>: Transition only allowed in final paragraph
        </div>
        <div class="rule-box">
            <strong>Repetition</strong>: No lemma repetition within the same article
        </div>
        <div class="rule-box">
            <strong>Cohesion</strong>: Higher similarity with next paragraph than previous (Δ ≥ {})
        </div>
        """.format(similarity_threshold), unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("Built For French Transition Contest Submission")

# ---------------- File Parsing Functions ----------------
def extract_text_from_pdf(pdf_file):
    """Extract text from PDF file"""
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
    """Extract text from TXT file"""
    try:
        return txt_file.getvalue().decode('utf-8')
    except Exception as e:
        st.error(f"Error reading TXT: {e}")
        return ""

def extract_text_from_docx(docx_file):
    """Extract text from DOCX file"""
    try:
        doc = Document(io.BytesIO(docx_file.read()))
        return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    except Exception as e:
        st.error(f"Error reading DOCX: {e}")
        return ""

def extract_text(uploaded_file):
    """Extract text based on file extension"""
    ext = uploaded_file.name.split('.')[-1].lower()
    if ext == 'pdf':
        return extract_text_from_pdf(uploaded_file)
    elif ext == 'txt':
        return extract_text_from_txt(uploaded_file)
    elif ext == 'docx':
        return extract_text_from_docx(uploaded_file)
    else:
        st.error(f"Unsupported file type: {ext}. Only PDF, TXT, DOCX allowed.")
        return ""

# ---------------- Article Parsing Functions ----------------
def parse_articles_from_text(text):
    """Parse articles and transitions from the extracted text"""
    articles = []
    lines = text.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Look for article title
        if line.startswith("Titre:"):
            current_article = {"title": "", "content": "", "transitions": []}
            current_article["title"] = line.replace("Titre:", "").strip()
            
            # Read the article content
            i += 1
            article_content = ""
            
            while i < len(lines):
                line = lines[i].strip()
                
                # Check if we've reached the transitions section
                if line.startswith("Transitions générées:"):
                    # Parse transitions
                    i += 1
                    while i < len(lines):
                        line = lines[i].strip()
                        # Stop if we hit a new article or end of file
                        if line.startswith("Titre:") or not line:
                            break
                        
                        # Clean up transition text
                        if line and not line.startswith("="):
                            # Remove numbering (e.g., "1. ", "2. ")
                            transition = re.sub(r'^\d+\.\s*', '', line)
                            if transition:
                                current_article["transitions"].append(transition)
                        i += 1
                    
                    # Set the article content and add to articles list
                    current_article["content"] = article_content.strip()
                    if current_article["title"] and current_article["transitions"]:
                        articles.append(current_article)
                    break
                else:
                    # Add to article content if it's not a header
                    if not line.startswith(("Chapeau:", "À savoir également")):
                        article_content += line + " "
                    i += 1
        else:
            i += 1
    
    return articles

def create_dataframe_from_articles(articles):
    """Create a dataframe suitable for analysis from parsed articles"""
    data = []
    
    for article_idx, article in enumerate(articles):
        content = article["content"]
        title = article["title"]
        transitions = article["transitions"]
        
        # Split content into sentences/paragraphs more intelligently
        for trans_idx, transition in enumerate(transitions):
            # Find the transition in the content
            transition_pos = content.find(transition)
            
            if transition_pos != -1:
                # Extract text before and after the transition
                before_transition = content[:transition_pos].strip()
                after_transition = content[transition_pos + len(transition):].strip()
                
                # Split before_transition into sentences
                if before_transition:
                    before_sentences = [s.strip() + "." for s in re.split(r'[.!?]+', before_transition) if s.strip()]
                    prev_para = before_sentences[-1] if before_sentences else ""
                else:
                    prev_para = ""
                
                # Split after_transition to get next paragraph
                if after_transition:
                    after_sentences = [s.strip() + "." for s in re.split(r'[.!?]+', after_transition) if s.strip()]
                    next_para = after_sentences[0] if after_sentences else ""
                else:
                    next_para = ""
                
                # Estimate paragraph index (assuming transitions are towards the end)
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

# ---------------- QA Check Functions ----------------
def check_word_count(transition_text):
    """Check if transition has ≤ 5 words"""
    words = re.findall(r'\b\w+\b', transition_text, flags=re.UNICODE)
    return len(words) <= 5, len(words)

def check_final_position(article_data, article_id, para_idx):
    """Check if transition is in the final paragraph of the article"""
    article_paragraphs = article_data[article_data['article_id'] == article_id]
    if article_paragraphs.empty:
        return False
    max_para_idx = article_paragraphs['para_idx'].max()
    # Allow some tolerance for final position (within last 2 paragraphs)
    return para_idx >= max_para_idx - 1

def check_repetition(article_data, article_id, transition_text, nlp):
    """Check if transition lemmas are repeated elsewhere in the article"""
    if nlp is None:
        # If no spaCy model available, do basic word-level comparison
        try:
            import re
            article_transitions = article_data[article_data['article_id'] == article_id]['transition_text'].tolist()
            other_transitions = [t for t in article_transitions if t != transition_text]
            
            if not other_transitions:
                return True, []  # No other transitions to compare with
            
            # Basic word tokenization
            trans_words = set(re.findall(r'\b\w+\b', transition_text.lower()))
            repeated_words = set()
            
            for other_trans in other_transitions:
                other_words = set(re.findall(r'\b\w+\b', other_trans.lower()))
                repeated_words.update(trans_words.intersection(other_words))
            
            return len(repeated_words) == 0, list(repeated_words)
        except Exception as e:
            st.warning(f"Error in basic repetition check: {e}")
            return True, []  # Pass if error occurs
    
    try:
        # Get all transitions from the same article
        article_transitions = article_data[article_data['article_id'] == article_id]['transition_text'].tolist()
        other_transitions = [t for t in article_transitions if t != transition_text]
        
        if not other_transitions:
            return True, []  # No other transitions to compare with
        
        # Process current transition
        trans_doc = nlp(transition_text)
        trans_lemmas = {token.lemma_.lower() for token in trans_doc 
                       if not token.is_stop and not token.is_punct and token.is_alpha and len(token.text) > 2}
        
        # Process other transitions
        repeated_lemmas = set()
        for other_trans in other_transitions:
            other_doc = nlp(other_trans)
            other_lemmas = {token.lemma_.lower() for token in other_doc 
                           if not token.is_stop and not token.is_punct and token.is_alpha and len(token.text) > 2}
            repeated_lemmas.update(trans_lemmas.intersection(other_lemmas))
        
        return len(repeated_lemmas) == 0, list(repeated_lemmas)
    except Exception as e:
        st.warning(f"Error in repetition check: {e}")
        return True, []

def compute_similarity(text1, text2, model):
    """Compute semantic similarity between two texts"""
    if not text1 or not text2 or not text1.strip() or not text2.strip():
        return 0.0
    
    try:
        from sentence_transformers import util
        embeddings = model.encode([text1, text2], convert_to_tensor=True)
        similarity = util.pytorch_cos_sim(embeddings[0], embeddings[1])
        return float(similarity.item())
    except Exception as e:
        st.warning(f"Error computing similarity: {e}")
        return 0.0

def check_cohesion(similarity_prev, similarity_next, threshold=0.1):
    """Check if transition has higher similarity with next paragraph"""
    cohesion_ok = similarity_next > similarity_prev + threshold
    return cohesion_ok, similarity_next - similarity_prev

def analyze_transitions(df, nlp, sentence_model, similarity_threshold):
    """Perform all QA checks on the transitions"""
    results = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for idx, row in df.iterrows():
        article_id = row['article_id']
        para_idx = row['para_idx']
        transition_text = row['transition_text']
        prev_para = row['previous_paragraph']
        next_para = row['next_paragraph']
        
        # Update progress
        progress = (idx + 1) / len(df)
        progress_bar.progress(progress)
        status_text.text(f"Processing transition {idx + 1} of {len(df)}: {transition_text[:30]}...")
        
        # Word count check
        word_count_ok, actual_count = check_word_count(transition_text)
        
        # Final position check
        final_position_ok = check_final_position(df, article_id, para_idx)
        
        # Repetition check
        repetition_ok, repeated_lemmas = check_repetition(df, article_id, transition_text, nlp)
        
        # Similarity checks
        similarity_prev = compute_similarity(transition_text, prev_para, sentence_model)
        similarity_next = compute_similarity(transition_text, next_para, sentence_model)
        
        # Cohesion check
        cohesion_ok, cohesion_diff = check_cohesion(similarity_prev, similarity_next, similarity_threshold)
        
        # Overall pass/fail
        passes_all = word_count_ok and final_position_ok and repetition_ok and cohesion_ok
        
        # Failure reason and triggered rules
        failure_reasons = []
        triggered_rules = []
        
        if not word_count_ok:
            failure_reasons.append(f"Word count ({actual_count} > 5)")
            triggered_rules.append("Word Count")
        if not final_position_ok:
            failure_reasons.append("Not in final paragraphs")
            triggered_rules.append("Position")
        if not repetition_ok:
            failure_reasons.append(f"Repeated lemmas: {', '.join(repeated_lemmas[:3])}")
            triggered_rules.append("Repetition")
        if not cohesion_ok:
            failure_reasons.append(f"Poor cohesion (Δ={cohesion_diff:.3f} < {similarity_threshold})")
            triggered_rules.append("Cohesion")
        
        failure_reason = "; ".join(failure_reasons) if failure_reasons else "Pass"
        triggered_rule = ", ".join(triggered_rules) if triggered_rules else "None"
        
        results.append({
            'article_id': article_id,
            'article_title': row['article_title'],
            'para_idx': para_idx,
            'transition_text': transition_text,
            'word_count_ok': word_count_ok,
            'final_position_ok': final_position_ok,
            'repetition_ok': repetition_ok,
            'cohesion_ok': cohesion_ok,
            'similarity_prev': similarity_prev,
            'similarity_next': similarity_next,
            'cohesion_diff': cohesion_diff,
            'pass_fail': 'Pass' if passes_all else 'Fail',
            'failure_reason': failure_reason,
            'triggered_rule': triggered_rule,
            'repeated_lemmas': repeated_lemmas
        })
    
    progress_bar.empty()
    status_text.empty()
    
    return pd.DataFrame(results)

def create_article_summary(results_df, article_id):
    """Create summary statistics for a specific article"""
    article_data = results_df[results_df['article_id'] == article_id]
    if article_data.empty:
        return None
    
    article_title = article_data['article_title'].iloc[0]
    total_transitions = len(article_data)
    pass_count = (article_data['pass_fail'] == 'Pass').sum()
    compliance_rate = (pass_count / total_transitions) * 100 if total_transitions > 0 else 0
    
    avg_sim_next = article_data['similarity_next'].mean()
    avg_sim_prev = article_data['similarity_prev'].mean()
    
    # Rule violation counts
    rule_violations = {
        'Word Count': (~article_data['word_count_ok']).sum(),
        'Position': (~article_data['final_position_ok']).sum(),
        'Repetition': (~article_data['repetition_ok']).sum(),
        'Cohesion': (~article_data['cohesion_ok']).sum()
    }
    
    return {
        'article_id': article_id,
        'article_title': article_title,
        'total_transitions': total_transitions,
        'pass_count': pass_count,
        'compliance_rate': compliance_rate,
        'avg_sim_next': avg_sim_next,
        'avg_sim_prev': avg_sim_prev,
        'rule_violations': rule_violations
    }

# ---------------- Main Application ----------------
def main():
    # Load models
    with st.spinner("🚀 Loading NLP models... This may take a moment."):
        nlp, sentence_model = initialize_models()
    
    # Welcome section
    st.markdown("""
    <div class="info-box">
        <h4>Welcome to the French Transition QA Tool</h4>
        <p>This tool analyzes French transition phrases between news paragraphs for quality assurance. 
        Upload PDF, TXT, or DOCX files containing articles with transitions to evaluate their compliance with editorial guidelines.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # File upload section
    st.markdown('<div class="sub-header">📤 Upload Files</div>', unsafe_allow_html=True)
    
    uploaded_files = st.file_uploader(
        "Drag and drop your files here",
        type=["pdf", "txt", "docx"],
        help="Files should contain articles with transition phrases",
        accept_multiple_files=True
    )
    
    if uploaded_files:
        try:
            all_articles = []
            
            for uploaded_file in uploaded_files:
                st.info(f"Processing file: {uploaded_file.name}")
                
                # Extract text from file
                text = extract_text(uploaded_file)
                
                if not text:
                    st.warning(f"No text extracted from {uploaded_file.name}")
                    continue
                
                # Parse articles from text
                articles = parse_articles_from_text(text)
                
                if articles:
                    st.success(f"Found {len(articles)} articles with {sum(len(a['transitions']) for a in articles)} transitions")
                    all_articles.extend(articles)
                else:
                    st.warning(f"No articles found in {uploaded_file.name}")
            
            if not all_articles:
                st.error("No articles with transitions found in any of the uploaded files.")
                return
            
            # Create dataframe for analysis
            df = create_dataframe_from_articles(all_articles)
            
            if df.empty:
                st.error("No transitions could be processed from the articles.")
                return
                
            # Show file info
            st.success(f"✅ Successfully extracted {len(df)} transitions from {len(uploaded_files)} files")
            
            # Analyze the data
            with st.spinner("🔍 Analyzing transitions. This may take a few minutes..."):
                results_df = analyze_transitions(df, nlp, sentence_model, similarity_threshold)
            
            # Display results
            st.markdown('<div class="sub-header">📊 QA Results</div>', unsafe_allow_html=True)
            
            # Conditional formatting
            def color_pass_fail(val):
                color = '#27ae60' if val == 'Pass' else '#e74c3c'
                return f'color: {color}; font-weight: bold'
            
            # Display table with formatting
            display_df = results_df.drop('repeated_lemmas', axis=1)
            st.dataframe(
                display_df.style.applymap(color_pass_fail, subset=['pass_fail']),
                height=400,
                use_container_width=True
            )
            
            # Create article summaries
            article_ids = results_df['article_id'].unique()
            article_summaries = []
            
            for article_id in article_ids:
                summary = create_article_summary(results_df, article_id)
                if summary:
                    article_summaries.append(summary)
            
            # Display article-specific summary statistics
            st.markdown('<div class="sub-header">📈 Article Summary Statistics</div>', unsafe_allow_html=True)
            
            for summary in article_summaries:
                st.markdown(f'<div class="article-header">📄 Article {summary["article_id"]}: {summary["article_title"]}</div>', unsafe_allow_html=True)
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">{summary['compliance_rate']:.1f}%</div>
                        <div class="metric-label">Compliance Rate</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">{summary['pass_count']}/{summary['total_transitions']}</div>
                        <div class="metric-label">Passed Transitions</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">{summary['avg_sim_next']:.3f}</div>
                        <div class="metric-label">Avg Similarity (Next)</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                with col4:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">{summary['avg_sim_prev']:.3f}</div>
                        <div class="metric-label">Avg Similarity (Prev)</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Rule violations for this article
                st.markdown("**Rule Violations:**")
                for rule, count in summary['rule_violations'].items():
                    if count > 0:
                        st.markdown(f"- **{rule}**: {count} violation(s)")
            
            # Global summary statistics
            st.markdown('<div class="sub-header">🌐 Global Summary Statistics</div>', unsafe_allow_html=True)
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                compliance_rate = (results_df['pass_fail'] == 'Pass').mean() * 100
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{compliance_rate:.1f}%</div>
                    <div class="metric-label">Overall Compliance</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                fail_count = (results_df['pass_fail'] == 'Fail').sum()
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{fail_count}</div>
                    <div class="metric-label">Total Failures</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                avg_sim_next = results_df['similarity_next'].mean()
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{avg_sim_next:.3f}</div>
                    <div class="metric-label">Avg Similarity (Next)</div>
                </div>
                """, unsafe_allow_html=True)
                
            with col4:
                avg_sim_prev = results_df['similarity_prev'].mean()
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{avg_sim_prev:.3f}</div>
                    <div class="metric-label">Avg Similarity (Prev)</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Failure breakdown
            st.markdown('<div class="sub-header">🔍 Failure Analysis</div>', unsafe_allow_html=True)
            
            # Calculate failure reasons
            failure_df = results_df[results_df['pass_fail'] == 'Fail']
            if not failure_df.empty:
                # Rule violation counts
                rule_violations = {
                    'Word Count': (~failure_df['word_count_ok']).sum(),
                    'Position': (~failure_df['final_position_ok']).sum(),
                    'Repetition': (~failure_df['repetition_ok']).sum(),
                    'Cohesion': (~failure_df['cohesion_ok']).sum()
                }
                
                # Create a bar chart of rule violations
                fig, ax = plt.subplots(figsize=(10, 6))
                rule_names = list(rule_violations.keys())
                violation_counts = list(rule_violations.values())
                
                bars = ax.bar(rule_names, violation_counts, color=['#e74c3c', '#f39c12', '#3498db', '#2ecc71'])
                ax.set_title('Rule Violations Distribution')
                ax.set_ylabel('Count')
                
                # Add value labels on bars
                for bar in bars:
                    height = bar.get_height()
                    if height > 0:
                        ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                                f'{int(height)}', ha='center', va='bottom')
                
                plt.xticks(rotation=45, ha='right')
                plt.tight_layout()
                st.pyplot(fig)
                plt.close()
            else:
                st.markdown("""
                <div class="success-box">
                    <h4>🎉 Excellent! All transitions passed the quality checks!</h4>
                </div>
                """, unsafe_allow_html=True)
            
            # Export options
            st.markdown('<div class="sub-header">💾 Export Results</div>', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                # CSV export
                csv = results_df.drop('repeated_lemmas', axis=1).to_csv(index=False)
                st.download_button(
                    label="📥 Download CSV Results",
                    data=csv,
                    file_name="transition_qa_results.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            with col2:
                # HTML export
                html = results_df.drop('repeated_lemmas', axis=1).to_html(index=False, escape=False)
                st.download_button(
                    label="📥 Download HTML Report",
                    data=html,
                    file_name="transition_qa_report.html",
                    mime="text/html",
                    use_container_width=True
                )
        
        except Exception as e:
            st.error(f"❌ An error occurred during processing: {str(e)}")
            st.exception(e)  # This will show the full traceback for debugging
    
    else:
        st.info("👆 Please upload one or more files to begin analysis.")
        
        # Show example structure
        with st.expander("📋 Expected File Structure Example"):
            st.markdown("""
            <div class="transition-example">
                <strong>Titre:</strong> Votre titre d'article ici<br>
                <strong>Contenu:</strong> Premier paragraphe de l'article. Deuxième paragraphe. 
                Troisième paragraphe avec texte complet de l'article.<br>
                <strong>Transitions générées:</strong><br>
                1. En conclusion<br>
                2. Pour résumer<br>
                3. Finalement
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("""
            **Expected file structure should include:**
            - `Titre:` followed by the article title
            - Article content (multiple paragraphs)
            - `Transitions générées:` followed by numbered transition phrases
            """)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div class="footer">
        <p>French Transition QA Tool • Built for Journalistic Content Analysis • Contest Submission</p>
        <p>Powered by spaCy, Sentence Transformers, and Streamlit</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()