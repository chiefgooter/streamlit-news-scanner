import streamlit as st
import feedparser
from datetime import datetime, timezone, timedelta # Added timedelta
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
st.header("💰 Real-Time Financial News Scanner 🚀") 
st.markdown("A consolidated feed of the latest business, tech, and market news from multiple sources.")

# Cache the results for 10 minutes (600 seconds). 
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

# Helper function to determine the visual style based on article age
def get_article_style(article):
    now_utc = datetime.now(timezone.utc)
    age = now_utc - article['published_utc']
    
    # Border colors based on age
    if age < timedelta(minutes=15):
        # Very New (last 15 minutes) - Highlight Green
        return {"border_color": "#28A745", "border_width": "2px"} 
    elif age < timedelta(minutes=60):
        # New (last 1 hour) - Highlight Yellow
        return {"border_color": "#FFC107", "border_width": "1px"}
    else:
        # Older - Default neutral border
        return {"border_color": "gray", "border_width": "0px"} 

try:
    # --- SIDEBAR CONTROLS ---
    with st.sidebar:
        st.title("⚙️ Scanner Controls")
        
        # NEW: Manual Refresh Button 
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
        ).strip().upper() 

        # 2. Dynamic Feed Construction
        dynamic_feeds = []
        if ticker_search:
            ticker_url = f'https://news.google.com/rss/search?q={ticker_search}&hl=en-US&gl=US&ceid=US:en'
            dynamic_feeds.append(ticker_url)
            st.success(f"Fetching news for **{ticker_search}**...")

        full_feed_list = FEEDS + dynamic_feeds
        
        # 3. FETCH DATA 
        all_articles = get_all_news(full_feed_list)

        # 4. Article Count 
        st.info(f"Total Articles Found: **{len(all_articles)}**")

        st.markdown("---")
        
        # 5. Dedicated Publisher Filter 
        unique_publishers = sorted(list(set(article['publisher'] for article in all_articles)))
        selected_publishers = st.multiselect(
            "Filter by Publisher:",
            options=unique_publishers,
            default=unique_publishers, # Select all by default
            key="publisher_filter"
        )
        
        # 6. Sorting Control
        sort_option = st.selectbox(
            "Sort Articles By:",
            ("Newest First", "Publisher Name (A-Z)"),
            key="sort_select"
        )

        st.markdown("---")
        
        # 7. General Filter Widget (Filters the articles that were already loaded)
        search_term = st.text_input(
            "Filter Loaded Articles:",
            placeholder="Filter by keyword (e.g., AI, Earnings)",
            help="Type a keyword to filter the articles that are already loaded in the list above."
        )

    # --- INITIAL FILTERING LOGIC (Publisher Filter) ---
    # Apply publisher filter first
    publisher_filtered_articles = [
        article for article in all_articles
        if article['publisher'] in selected_publishers
    ]

    # --- SECONDARY FILTERING LOGIC (Keyword Filter) ---
    if search_term:
        search_term_lower = search_term.lower()
        
        filtered_articles = [
            article for article in publisher_filtered_articles 
            if search_term_lower in article['title'].lower() or \
               search_term_lower in article['publisher'].lower()
        ]
        # Display results count in the main area
        st.info(f"Showing **{len(filtered_articles)}** results for: **{search_term}**")
    else:
        filtered_articles = publisher_filtered_articles
        
    # --- SORTING LOGIC (Applied after filtering) ---
    if sort_option == "Newest First":
        filtered_articles.sort(key=lambda x: x['published_utc'], reverse=True)
    elif sort_option == "Publisher Name (A-Z)":
        filtered_articles.sort(key=lambda x: x['publisher'])
    
    # --- DISPLAY FILTERED ARTICLES ---
    for article in filtered_articles[:1000]: 
        style = get_article_style(article)
        
        # Apply custom styling via st.markdown for the container border
        st.markdown(
            f"""
            <style>
            .article-container-{article['title'].replace(' ', '')[:10]} {{
                border: {style['border_width']} solid {style['border_color']} !important;
                border-radius: 0.5rem;
                padding: 1rem;
                margin-bottom: 1rem;
            }}
            </style>
            """,
            unsafe_allow_html=True
        )

        # The container uses the custom CSS class we just defined
        with st.container():
            st.markdown(
                f"<div class='article-container-{article['title'].replace(' ', '')[:10]}'>",
                unsafe_allow_html=True
            )
            # 1. Headline as a large, clickable link
            st.markdown(f"### [{article['title']}]({article['url']})") 
            
            # 2. Source and Date on a single line with enhanced styling
            st.caption(
                f"**<span style='color: #1E90FF;'>{article['publisher']}</span>** | *{article['published_utc'].strftime('%Y-%m-%d %H:%M:%S %Z')}*",
                unsafe_allow_html=True
            )
            
            # 3. Use an Expander to hide the description until clicked
            with st.expander("Click here to read summary..."):
                st.write(article['description'])
                st.markdown(f"**[Read Full Article at {article['publisher']}]({article['url']})**")
            
            st.markdown("</div>", unsafe_allow_html=True) # Close the custom container div

    st.divider()

except Exception as e:
    # A generic, user-friendly error message is displayed in the app
    st.error(f"A critical error occurred while fetching news. Please try again or check the ticker symbol.")
    # Log the full error to the console for debugging
    print(f"ERROR: {e}")
