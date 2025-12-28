import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import plotly.express as px

# --- UVOZ TRANSFORMERS & WORDCLOUD (ZA BONUS) ---
from transformers import pipeline
from wordcloud import WordCloud
import matplotlib.pyplot as plt

# ==========================================
# PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="E-Commerce Dashboard",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# CUSTOM CSS
# ==========================================
st.markdown("""
    <style>
    .main {
        background-color: #f5f7fa;
    }
    .stMetric {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# LOAD DATA
# ==========================================
@st.cache_data
def load_data():
    """Naloži scraped podatke iz JSON datotek"""
    # Za Render deployment moramo preveriti, kje so datoteke.
    # Predvidevamo, da so naložene v isti mapi ali podmapi.
    data_folder = 'scraped_data' 
    
    # Če mape ni (na Renderju včasih), preveri trenutno mapo
    if not os.path.exists(data_folder):
        data_folder = '.'

    try:
        # Prilagoditev poti za GitHub/Render strukturo
        p_path = os.path.join(data_folder, 'products.json')
        r_path = os.path.join(data_folder, 'reviews.json')
        t_path = os.path.join(data_folder, 'testimonials.json')

        # Če datotek ni v mapi, poskusi direktno (fallback)
        if not os.path.exists(p_path): p_path = 'products.json'
        if not os.path.exists(r_path): r_path = 'reviews.json'
        if not os.path.exists(t_path): t_path = 'testimonials.json'

        with open(p_path, 'r', encoding='utf-8') as f: products = json.load(f)
        with open(r_path, 'r', encoding='utf-8') as f: reviews = json.load(f)
        with open(t_path, 'r', encoding='utf-8') as f: testimonials = json.load(f)
        
        # Parse datume v reviews
        for review in reviews:
            try:
                date_str = review.get('date', '')
                for fmt in ['%B %d, %Y', '%b %d, %Y', '%Y-%m-%d', '%d.%m.%Y']:
                    try:
                        parsed_date = datetime.strptime(date_str, fmt)
                        review['date_parsed'] = parsed_date
                        review['month'] = parsed_date.month
                        review['year'] = parsed_date.year
                        review['month_name'] = parsed_date.strftime('%B')
                        break
                    except:
                        continue
                if 'date_parsed' not in review:
                    review['date_parsed'] = datetime(2023, 6, 1)
                    review['month'] = 6
                    review['year'] = 2023
                    review['month_name'] = 'June'
            except:
                review['date_parsed'] = datetime(2023, 6, 1)
                review['month'] = 6
                review['year'] = 2023
                review['month_name'] = 'June'
        
        return {'products': products, 'reviews': reviews, 'testimonials': testimonials}
    
    except Exception as e:
        # Če napaka, vrni prazne strukture, da app ne crashne takoj
        return {'products': [], 'reviews': [], 'testimonials': []}

data = load_data()

# ==========================================
# --- LOAD AI MODEL ---
# ==========================================
@st.cache_resource
def load_sentiment_model():
    """Naloži Hugging Face pipeline (samo enkrat)"""
    # Uporaba manjšega modela za hitrejši load na Renderju
    return pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def display_stars(rating):
    return "⭐" * int(rating)

# ==========================================
# SIDEBAR NAVIGATION
# ==========================================
st.sidebar.title("🧭 Navigation")
st.sidebar.markdown("---")
page = st.sidebar.radio("Izberi sekcijo:", ["🏠 Home", "📦 Products", "💬 Testimonials", "⭐ Reviews"])

st.sidebar.markdown("---")
st.sidebar.info("**Podatki:** Leto 2023\n**Vir:** web-scraping.dev")

# ==========================================
# PAGE: HOME
# ==========================================
if page == "🏠 Home":
    st.title("🛍️ E-Commerce Dashboard")
    st.markdown("### Dobrodošli v analitičnem dashboardu")
    col1, col2, col3 = st.columns(3)
    col1.metric("📦 Products", len(data['products']))
    col2.metric("⭐ Reviews", len(data['reviews']))
    col3.metric("💬 Testimonials", len(data['testimonials']))

# ==========================================
# PAGE: PRODUCTS
# ==========================================
elif page == "📦 Products":
    st.title("📦 Products")
    if data['products']:
        df_products = pd.DataFrame(data['products'])
        st.metric("Skupaj produktov", len(df_products))
        
        search_term = st.text_input("🔍 Iskanje produkta:", "")
        if search_term:
            df_products = df_products[df_products['name'].str.contains(search_term, case=False, na=False)]
        
        st.dataframe(df_products, use_container_width=True)
        csv = df_products.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Prenesi CSV", csv, "products.csv", "text/csv")

# ==========================================
# PAGE: TESTIMONIALS
# ==========================================
elif page == "💬 Testimonials":
    st.title("💬 Testimonials")
    if data['testimonials']:
        df_testimonials = pd.DataFrame(data['testimonials'])
        col1, col2 = st.columns(2)
        col1.metric("Skupaj", len(df_testimonials))
        col2.metric("Povprečna ocena", f"{df_testimonials['rating'].mean():.2f} ⭐")
        
        rating_filter = st.multiselect("Filtriraj po oceni:", sorted(df_testimonials['rating'].unique()), default=sorted(df_testimonials['rating'].unique()))
        df_filtered = df_testimonials[df_testimonials['rating'].isin(rating_filter)]
        
        for idx, row in df_filtered.iterrows():
            with st.container():
                st.markdown(f"**Testimonial #{idx+1}** ({display_stars(row['rating'])})")
                st.write(row['text'])
                st.markdown("---")
        
        fig = px.bar(df_filtered['rating'].value_counts().sort_index(), title='Porazdelitev ocen')
        st.plotly_chart(fig, use_container_width=True)

# ==========================================
# PAGE: REVIEWS (AI + WORDCLOUD BONUS)
# ==========================================
elif page == "⭐ Reviews":
    st.title("⭐ Reviews - AI Sentiment Analiza")
    st.markdown("### Filtriraj reviews po mesecu (2023) in analiziraj z AI")
    
    if data['reviews']:
        df_reviews = pd.DataFrame(data['reviews'])
        
        months_2023 = ["January 2023", "February 2023", "March 2023", "April 2023", "May 2023", "June 2023", "July 2023", "August 2023", "September 2023", "October 2023", "November 2023", "December 2023"]
        selected_month = st.select_slider("Izberi mesec:", options=months_2023, value="June 2023")
        month_number = months_2023.index(selected_month) + 1
        
        filtered_reviews = df_reviews[(df_reviews['month'] == month_number) & (df_reviews['year'] == 2023)].copy()
        
        st.write(f"Najdenih mnenj: **{len(filtered_reviews)}**")
        
        if len(filtered_reviews) > 0:
            st.markdown("---")
            with st.spinner("🤖 AI analizira sentiment..."):
                sentiment_pipeline = load_sentiment_model()
                texts = filtered_reviews['review_text'].astype(str).tolist()
                results = sentiment_pipeline(texts)
                
                filtered_reviews['AI Sentiment'] = [r['label'] for r in results]
                filtered_reviews['AI Confidence'] = [r['score'] for r in results]
            
            st.success("Analiza končana! ✅")

            # --- 4. VISUALIZATION (BAR CHART) ---
            st.subheader(f"📊 Sentiment Analiza za {selected_month}")
            
            chart_data = filtered_reviews.groupby('AI Sentiment').agg(
                Count=('AI Sentiment', 'count'),
                Avg_Confidence=('AI Confidence', 'mean')
            ).reset_index()

            fig_bar = px.bar(
                chart_data,
                x='AI Sentiment',
                y='Count',
                color='AI Sentiment',
                title="Število Positive/Negative ocen (z Avg Confidence)",
                color_discrete_map={'POSITIVE': '#4CAF50', 'NEGATIVE': '#F44336'},
                text='Count',
                hover_data={'AI Sentiment': False, 'Count': True, 'Avg_Confidence': ':.2%'}
            )
            fig_bar.update_traces(hovertemplate="<b>%{x}</b><br>Število: %{y}<br>Avg Confidence: %{customdata[0]:.2%}<extra></extra>")
            st.plotly_chart(fig_bar, use_container_width=True)

            # --- BONUS: WORD CLOUD ---
            st.subheader("☁️ Word Cloud (Bonus)")
            st.write(f"Najpogostejše besede v mesecu {selected_month}")
            
            # Združi ves tekst v en string
            all_text = " ".join(review for review in filtered_reviews['review_text'])
            
            # Generiraj WordCloud
            wordcloud = WordCloud(width=800, height=400, background_color='white').generate(all_text)
            
            # Prikaži z matplotlib
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.imshow(wordcloud, interpolation='bilinear')
            ax.axis("off")
            st.pyplot(fig)

            # --- PODROBNA TABELA ---
            st.subheader("📝 Podrobni podatki")
            st.dataframe(
                filtered_reviews[['date', 'review_text', 'rating', 'AI Sentiment', 'AI Confidence']],
                use_container_width=True,
                column_config={
                    "AI Confidence": st.column_config.ProgressColumn("Confidence", format="%.2f", min_value=0, max_value=1),
                    "rating": st.column_config.NumberColumn("Ocena", format="%d ⭐")
                }
            )
        else:
            st.warning(f"Ni mnenj za {selected_month}.")