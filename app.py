import streamlit as st
import feedparser
from datetime import datetime, timezone # <-- NEW IMPORT
from concurrent.futures import ThreadPoolExecutor

# --- Configuration ---
FEEDS = [
    'https://feeds.feedburner.com/Techcrunch',
    'https://rss.cnn.com/rss/money_latest.rss',
    'https://feeds.a.dj.com/rss/RSSMarketsMain.xml',
    'https://www.reuters.com/arc/outboundfeeds/newsroom/all/?outputType=xml',
    # New feeds previously discussed
    'https://finance.yahoo.com/news/rss',
    'https://rss.nytimes.com/services/xml/rss/nyt/Economy.xml',
    'https://feeds.feedburner.com/venturebeat/feed',
    'https://www.forbes.com/business/feed/',
]

# Function to fetch and parse a single RSS feed (includes User-Agent fix)
def fetch_feed(url):
    # Using HTTP headers to mimic a browser, similar to the User-Agent fix
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    return feedparser.parse(url, request_headers=headers)

# --- Streamlit App Layout ---

st.set_page_config(layout="wide")
st.title("📰 Real-Time Financial News Scanner (Streamlit)")

# Cache the results for 10 minutes (600 seconds) to speed up user interactions
@st.cache_data(ttl=600) 
def get_all_news():
    articles = []
    
    # Use ThreadPoolExecutor for concurrent fetching (like Promise.all in JavaScript)
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(fetch_feed, FEEDS))
    
    for feed in results:
        publisher_name = feed.feed.get('title', 'Unknown Source')
        # Increased per-source fetch limit
        for entry in feed.entries[:300]: 
            try:
                # Safely parse the published date
                published_time = datetime.strptime(entry.published, '%a, %d %b %Y %H:%M:%S %z')
            except:
                # --- CORRECTED FIX: Create an offset-aware datetime for comparison ---
                published_time = datetime.now(timezone.utc) # <-- CORRECTED
                
            articles.append({
                'title': entry.title,
                'url': entry.link,
                'publisher': publisher_name,
                'published_utc': published_time,
                'description': getattr(entry, 'summary', entry.get('content', [{}])[0].get('value', 'No description available'))
            })

    # Sort articles by time (most recent first)
    return sorted(articles, key=lambda x: x['published_utc'], reverse=True)

try:
    all_articles = get_all_news()

    if not all_articles:
        st.error("Error: Could not load news from any sources. The feeds might be blocking the server.")
    else:
        st.subheader(f"Total Articles Found: {len(all_articles)}")

        # --- SEARCH WIDGET ---
        search_term = st.text_input(
            "Filter Articles:",
            placeholder="Search headlines (e.g., Tesla, AI, Earnings)",
            help="Type a keyword to filter the articles."
        )

        # --- FILTERING LOGIC ---
        if search_term:
            # Convert search term to lowercase for case-insensitive matching
            search_term_lower = search_term.lower()
            
            # Filter articles based on the search term in the title or publisher name
            filtered_articles = [
                article for article in all_articles 
                if search_term_lower in article['title'].lower() or \
                   search_term_lower in article['publisher'].lower()
            ]
            st.info(f"Showing {len(filtered_articles)} results for: **{search_term}**")
        else:
            # If no search term, show all articles
            filtered_articles = all_articles
        
        # --- DISPLAY FILTERED ARTICLES ---
        # Display up to 1000 articles after filtering
        for article in filtered_articles[:1000]: 
            st.markdown("---")
            
            # Format title as a clickable link
            st.markdown(
                f"### [{article['title']}]({article['url']})"
            )
            
            # Display publisher and time
            st.markdown(
                f"**{article['publisher']}** | *{article['published_utc'].strftime('%Y-%m-%d %H:%M:%S %Z')}*"
            )
            
            # Display description
            st.write(article['description'][:300] + '...') 

except Exception as e:
    st.error(f"A critical error occurred while fetching news. Details: {e}")
