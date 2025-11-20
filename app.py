import streamlit as st
import feedparser
from datetime import datetime, timezone 
from concurrent.futures import ThreadPoolExecutor

# --- Configuration ---
# Static feeds that are always fetched (removed the individual stock feeds as they are now dynamic)
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
st.header("💰 Real-Time Financial News Scanner 🚀") # Changed to st.header for better hierarchy
st.markdown("A consolidated feed of the latest business, tech, and market news from multiple sources.")

# Cache the results for 10 minutes (600 seconds). 
# The cache key now depends on the 'feed_list' argument.
@st.cache_data(ttl=600) 
def get_all_news(feed_list):
    articles = []
    
    # Use ThreadPoolExecutor to fetch all feeds concurrently
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(fetch_feed, feed_list))
    
    for feed in results:
        publisher_name = feed.feed.get('title', 'Unknown Source')
        for entry in feed.entries[:300]: 
            try:
                # Attempt to parse publication date
                published_time = datetime.strptime(entry.published, '%a, %d %b %Y %H:%M:%S %z')
            except:
                # Fallback to current time in UTC if parsing fails
                published_time = datetime.now(timezone.utc)
                
            articles.append({
                'title': entry.title,
                'url': entry.link,
                'publisher': publisher_name,
                'published_utc': published_time,
                'description': getattr(entry, 'summary', entry.get('content', [{}])[0].get('value', 'No description available'))
            })

    # Initial sort by date (Newest First) for performance
    return sorted(articles, key=lambda x: x['published_utc'], reverse=True)

try:
    # --- SIDEBAR CONTROLS ---
    with st.sidebar:
        st.title("⚙️ Scanner Controls")
        
        # NEW: Manual Refresh Button (First in sidebar for quick access)
        if st.button("Manual Data Refresh 🔄", help="Clear cache and fetch all news feeds now."):
             st.cache_data.clear()
             st.rerun()

        st.markdown("---")
        # 1. Stock Ticker Search (This input drives the fetching logic)
        ticker_search = st.text_input(
            "Search by Stock Ticker (e.g., AAPL)",
            placeholder="Enter Ticker Symbol",
            max_chars=5,
            help="Enter a ticker (e.g., TSLA) to fetch the latest news specifically about that company.",
            key="ticker_input"
        ).strip().upper() # Clean and capitalize the input

        # 2. Dynamic Feed Construction
        dynamic_feeds = []
        if ticker_search:
            # Generate the custom Google News RSS link for the ticker
            ticker_url = f'https://news.google.com/rss/search?q={ticker_search}&hl=en-US&gl=US&ceid=US:en'
            dynamic_feeds.append(ticker_url)
            st.success(f"Fetching news for **{ticker_search}**...")

        # Combine static feeds and dynamic feeds
        full_feed_list = FEEDS + dynamic_feeds
        
        # 3. FETCH DATA (Call the cached function with the dynamic feed list)
        all_articles = get_all_news(full_feed_list)

        # 4. Article Count 
        st.info(f"Total Articles Found: **{len(all_articles)}**")

        st.markdown("---")
        
        # 5. Sorting Control
        sort_option = st.selectbox(
            "Sort Articles By:",
            ("Newest First", "Publisher Name (A-Z)"),
            key="sort_select"
        )

        st.markdown("---")
        
        # 6. General Filter Widget (This filters the articles that were already loaded)
        search_term = st.text_input(
            "Filter Loaded Articles:",
            placeholder="Filter by keyword (e.g., AI, Earnings)",
            help="Type a keyword to filter the articles that are already loaded in the list above."
        )

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
        
    # --- SORTING LOGIC (Applied after filtering) ---
    if sort_option == "Newest First":
        filtered_articles.sort(key=lambda x: x['published_utc'], reverse=True)
    elif sort_option == "Publisher Name (A-Z)":
        filtered_articles.sort(key=lambda x: x['publisher'])
    
    # --- DISPLAY FILTERED ARTICLES ---
    for article in filtered_articles[:1000]: 
        with st.container(border=True): 
            # 1. Headline as a large, clickable link
            st.markdown(f"### [{article['title']}]({article['url']})") 
            
            # 2. Source and Date on a single line with enhanced styling
            # Styled the publisher with bold blue text for better visual appeal
            st.caption(
                f"**<span style='color: #1E90FF;'>{article['publisher']}</span>** | *{article['published_utc'].strftime('%Y-%m-%d %H:%M:%S %Z')}*",
                unsafe_allow_html=True
            )
            
            # 3. Use an Expander to hide the description until clicked
            with st.expander("Click here to read summary..."):
                st.write(article['description'])
                st.markdown(f"**[Read Full Article at {article['publisher']}]({article['url']})**")
            
    st.divider()

except Exception as e:
    # A generic, user-friendly error message is displayed in the app
    st.error(f"A critical error occurred while fetching news. Please try again or check the ticker symbol.")
    # Log the full error to the console for debugging
    print(f"ERROR: {e}")
