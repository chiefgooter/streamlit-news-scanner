import streamlit as st
import feedparser
from datetime import datetime, timezone 
from concurrent.futures import ThreadPoolExecutor

# --- Configuration ---
FEEDS = [
    'https://feeds.feedburner.com/Techcrunch',
    'https://rss.cnn.com/rss/money_latest.rss',
    'https://feeds.a.dj.com/rss/RSSMarketsMain.xml',
    'https://www.reuters.com/arc/outboundfeeds/newsroom/all/?outputType=xml',
    'https://finance.yahoo.com/news/rss',
    'https://rss.nytimes.com/services/xml/rss/nyt/Economy.xml',
    'https://feeds.feedburner.com/venturebeat/feed',
    'https://www.forbes.com/business/feed/',
    'https://feeds.marketwatch.com/marketwatch/public/rss/mw_latestnews',
    'https://www.cnbc.com/id/10000664/device/rss/rss.html',
    'http://feeds.bbci.co.uk/news/business/rss.xml',
    'https://www.reuters.com/arc/outboundfeeds/tag/finance/?outputType=xml',
]

# Function to fetch and parse a single RSS feed (includes User-Agent fix)
def fetch_feed(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    return feedparser.parse(url, request_headers=headers)

# --- Streamlit App Layout ---

st.set_page_config(layout="wide")
st.title("💰 Real-Time Financial News Scanner 🚀") 

# Cache the results for 10 minutes (600 seconds) to speed up user interactions
@st.cache_data(ttl=600) 
def get_all_news():
    articles = []
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(fetch_feed, FEEDS))
    
    for feed in results:
        publisher_name = feed.feed.get('title', 'Unknown Source')
        for entry in feed.entries[:300]: 
            try:
                published_time = datetime.strptime(entry.published, '%a, %d %b %Y %H:%M:%S %z')
            except:
                # Corrected: Create an offset-aware datetime for comparison
                published_time = datetime.now(timezone.utc)
                
            articles.append({
                'title': entry.title,
                'url': entry.link,
                'publisher': publisher_name,
                'published_utc': published_time,
                'description': getattr(entry, 'summary', entry.get('content', [{}])[0].get('value', 'No description available'))
            })

    return sorted(articles, key=lambda x: x['published_utc'], reverse=True)

try:
    all_articles = get_all_news()

    if not all_articles:
        st.error("Error: Could not load news from any sources. The feeds might be blocking the server.")
    else:
        # --- SIDEBAR CONTROLS ---
        with st.sidebar:
            st.title("⚙️ Scanner Controls")
            
            # 1. Search Widget 
            search_term = st.text_input(
                "Filter Articles:",
                placeholder="Search headlines (e.g., Tesla, AI, Earnings)",
                help="Type a keyword to filter the articles."
            )
            
            # 2. Article Count 
            st.info(f"Total Articles Found: **{len(all_articles)}**")
        
        # --- FILTERING LOGIC ---
        if search_term:
            search_term_lower = search_term.lower()
            
            filtered_articles = [
                article for article in all_articles 
                if search_term_lower in article['title'].lower() or \
                   search_term_lower in article['publisher'].lower()
            ]
            # Display results count in the main area
            st.info(f"Showing **{len(filtered_articles)}** results for: **{search_term}**")
        else:
            filtered_articles = all_articles
        
        # --- DISPLAY FILTERED ARTICLES (with Expander and Container Layout) ---
        for article in filtered_articles[:1000]: 
            # Use st.container() for a clean visual block per article
            with st.container(border=True): 
                # 1. Headline as a large, clickable link
                st.markdown(f"### [{article['title']}]({article['url']})") 
                
                # 2. Source and Date on a single line with a divider
                st.caption(
                    f"**{article['publisher']}** | *{article['published_utc'].strftime('%Y-%m-%d %H:%M:%S %Z')}*"
                )
                
                # 3. Use an Expander to hide the description until clicked
                with st.expander("Click here to read summary..."):
                    st.write(article['description'])
                    st.markdown(f"**[Read Full Article at {article['publisher']}]({article['url']})**")
                
        st.divider()

except Exception as e:
    st.error(f"A critical error occurred while fetching news. Details: {e}")
