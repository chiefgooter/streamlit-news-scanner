import streamlit as st
import feedparser
from datetime import datetime, timezone, timedelta 
from concurrent.futures import ThreadPoolExecutor
import html
import re 

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

# --- Sentiment Analysis & Utility Functions ---

# Helper function to remove HTML tags and unescape entities for clean text
def clean_html_description(raw_description):
    # 1. Unescape HTML entities first (e.g., &amp; -> &)
    unescaped = html.unescape(raw_description)
    
    # 2. Strip all remaining HTML tags using a more reliable regex
    clean_text = re.sub('<.*?>', '', unescaped)
    
    # 3. Remove excess whitespace and newlines for clean display
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    
    return clean_text

# Simple, rule-based sentiment scoring to avoid external dependencies
def get_sentiment(text):
    text_lower = text.lower()
    
    positive_keywords = ['gain', 'profit', 'rise', 'boost', 'upbeat', 'soar', 'strong', 'growth', 'rally', 'win', 'success', 'record', 'outperform', 'expansion', 'bullish']
    negative_keywords = ['loss', 'drop', 'fall', 'slump', 'plunge', 'sell-off', 'weak', 'decline', 'miss', 'dip', 'cut', 'downgrade', 'crisis', 'risk', 'bearish', 'uncertainty']

    positive_count = sum(1 for keyword in positive_keywords if keyword in text_lower)
    negative_count = sum(1 for keyword in negative_keywords if keyword in text_lower)
    
    if positive_count > negative_count:
        return 'Positive'
    elif negative_count > positive_count:
        return 'Negative'
    else:
        return 'Neutral'

# Returns style for displaying sentiment
def get_sentiment_style(sentiment):
    if sentiment == 'Positive':
        return 'background-color: #D4EDDA; color: #155724; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 0.8em;'
    elif sentiment == 'Negative':
        return 'background-color: #F8D7DA; color: #721C24; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 0.8em;'
    else:
        return 'background-color: #E9ECEF; color: #495057; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 0.8em;'


# --- Streamlit App Layout ---

st.set_page_config(layout="wide")

# NEW: Custom CSS adjustments 
st.markdown("""
<style>
/* Use a cleaner, system-default font for a modern look */
html, body, [class*="st-"] {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol";
}
/* Reduce vertical space above the main title */
.css-1g5lmd {
    margin-top: -30px; 
}
/* Tighter spacing for the article list (Streamlit containers) */
.st-emotion-cache-1kyxoe7 > div > div {
    margin-bottom: 0.5rem; /* Reduced margin */
}

/* FIX 1: RESTORES THE SIDEBAR TOGGLE ICON */
/* This specific selector was hiding the icon itself. We only want to hide the expander text now. */
/* Removing this block ensures the sidebar button renders correctly as an icon. */
/* button[title="Open sidebar"], button[title*="keyboard_double_arrow_right"], [data-testid="stSidebarContent"] ~ button { 
    display: none !important;
    visibility: hidden !important;
} */


/* --- CRITICAL FIX 2: HIDES THE FAILING ICON/TEXT INSIDE THE ARTICLE EXPANDER --- */

/* Hides the Streamlit icon element itself */
[data-testid="stExpanderToggleIcon"] {
    display: none !important;
}

/* Hides the *underlying text* that is causing the overlap/visibility issue */
/* This targets the span that holds the internal icon name (like 'keyboard_arrow_right') */
button[data-testid="stExpander"] > div > div > span:first-child { 
    display: none !important;
}

/* Ensures the text part of the expander is visible and styled correctly */
[data-testid="stExpander"] > div > div > button > div:nth-child(2) {
    font-size: 1.1em !important; 
    font-weight: bold !important;
}

</style>
""", unsafe_allow_html=True)


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
            raw_description = getattr(entry, 'summary', entry.get('content', [{}])[0].get('value', 'No description available'))
            
            published_time = datetime.now(timezone.utc) # Default to aware fallback

            try:
                # 1. Attempt the standard robust parse with timezone (%z)
                published_time = datetime.strptime(entry.published, '%a, %d %b %Y %H:%M:%S %z')
            except ValueError:
                # 2. If the first parse fails (missing timezone data), attempt a simpler naive parse.
                try:
                    published_time = datetime.strptime(entry.published, '%a, %d %b %Y %H:%M:%S')
                except ValueError:
                    # 3. Final fallback: use current UTC time (already aware)
                    pass

            # --- CRITICAL FIX: ENSURE ALL DATES ARE AWARE (UTC) ---
            # The error means a date object made it through as "naive" (tzinfo is None).
            if published_time.tzinfo is None or published_time.tzinfo.utcoffset(published_time) is None:
                # If naive, localize it to UTC. This is what prevents the comparison error.
                published_time = published_time.replace(tzinfo=timezone.utc)
            
            # Clean description for display and sentiment analysis
            cleaned_description = clean_html_description(raw_description)
            
            # Calculate sentiment using title and cleaned description (Feature 3)
            combined_text = entry.title + ' ' + cleaned_description
            sentiment = get_sentiment(combined_text)
                
            articles.append({
                'title': entry.title,
                'url': entry.link,
                'publisher': publisher_name,
                'published_utc': published_time,
                'description': cleaned_description,
                'sentiment': sentiment 
            })

    # Initial sort by date (Newest First) for performance
    sorted_articles = sorted(articles, key=lambda x: x['published_utc'], reverse=True)
    
    # Return articles and the current time of the fetch
    return sorted_articles, datetime.now(timezone.utc)


# Helper function to determine the visual style based on article age
def get_article_style(article):
    now_utc = datetime.now(timezone.utc)
    age = now_utc - article['published_utc']
    
    # Border colors based on age
    if age < timedelta(minutes=15):
        # Very New (last 15 minutes) - Highlight Green
        return {"border_color": "#28A745", "border_width": "3px"} 
    elif age < timedelta(minutes=60):
        # New (last 1 hour) - Highlight Yellow
        return {"border_color": "#FFC107", "border_width": "2px"}
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
        
        # 3. FETCH DATA (Now returns articles and last update time)
        all_articles, last_update_time = get_all_news(full_feed_list)
        
        # NEW: Last Update Status
        if all_articles:
             st.info(f"Last successful fetch: **{last_update_time.strftime('%H:%M:%S %Z')}**")
        
        # 4. Article Count 
        st.info(f"Total Articles Found: **{len(all_articles)}**")

        st.markdown("---")
        
        # 5. Dedicated Publisher Filter 
        unique_publishers = sorted(list(set(article['publisher'] for article in all_articles)))
        selected_publishers = st.multiselect(
            "Filter by Publisher:",
            options=unique_publishers,
            default=unique_publishers, 
            key="publisher_filter"
        )
        
        # NEW Feature 3: Sentiment Filter
        sentiment_options = ['Positive', 'Neutral', 'Negative']
        selected_sentiment = st.multiselect(
            "Filter by Sentiment:",
            options=sentiment_options,
            default=sentiment_options,
            key="sentiment_filter",
            help="Filter articles based on automated sentiment analysis."
        )

        # NEW Feature 1: Advanced Time Filtering
        time_options = {
            "All Time": timedelta(days=365 * 10),  # Effectively 'All Time'
            "Last 24 Hours": timedelta(hours=24),
            "Last 4 Hours": timedelta(hours=4),
            "Last 1 Hour": timedelta(hours=1),
            "Last 30 Minutes": timedelta(minutes=30),
        }
        selected_time_range_name = st.selectbox(
            "Filter by Time Range:",
            list(time_options.keys()),
            index=3, # Default to Last 1 Hour
            key="time_filter"
        )
        # Convert selected name to timedelta object
        time_limit = time_options[selected_time_range_name]
        
        st.markdown("---")
        
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

    # --- FILTERING LOGIC ---
    now_utc = datetime.now(timezone.utc)
    
    # 1. Time Filter (Feature 1)
    time_filtered_articles = [
        article for article in all_articles
        if (now_utc - article['published_utc']) <= time_limit
    ]
    
    # 2. Publisher Filter
    publisher_filtered_articles = [
        article for article in time_filtered_articles
        if article['publisher'] in selected_publishers
    ]

    # 3. Sentiment Filter (Feature 3)
    sentiment_filtered_articles = [
        article for article in publisher_filtered_articles
        if article['sentiment'] in selected_sentiment
    ]

    # 4. Keyword Filter (Feature 2 - Now searches description)
    if search_term:
        search_term_lower = search_term.lower()
        
        filtered_articles = [
            article for article in sentiment_filtered_articles
            if search_term_lower in article['title'].lower() or \
               search_term_lower in article['publisher'].lower() or \
               search_term_lower in article['description'].lower() # NEW: Search Description
        ]
        # Display results count in the main area
        st.info(f"Showing **{len(filtered_articles)}** results for: **{search_term}**")
    else:
        filtered_articles = sentiment_filtered_articles
        
    # --- SORTING LOGIC (Applied after filtering) ---
    if sort_option == "Newest First":
        filtered_articles.sort(key=lambda x: x['published_utc'], reverse=True)
    elif sort_option == "Publisher Name (A-Z)":
        filtered_articles.sort(key=lambda x: x['publisher'])
    
    # --- DISPLAY FILTERED ARTICLES ---
    if not filtered_articles:
        st.warning("No articles found matching your current filters.")
    else:
        for article in filtered_articles[:1000]: 
            style = get_article_style(article)
            sentiment_style = get_sentiment_style(article['sentiment'])
            
            with st.container(border=True): 
                # 1. Colored Border
                st.markdown(
                    f'<div style="height: {style["border_width"]}; background-color: {style["border_color"]}; margin: -1rem -1rem 0.5rem -1rem; border-radius: 0.4rem 0.4rem 0 0;"></div>', 
                    unsafe_allow_html=True
                )
                
                # 2. Headline as a large, clickable link + Sentiment Tag
                # Display sentiment tag right next to the headline
                st.markdown(
                    f"<span style='{sentiment_style}'>{article['sentiment']}</span> "
                    f"**[{article['title']}]({article['url']})**", 
                    unsafe_allow_html=True
                ) 
                
                # 3. Source and Date on a single line with enhanced styling
                st.caption(
                    f"**<span style='color: #1E90FF;'>{article['publisher']}</span>** | *{article['published_utc'].strftime('%Y-%m-%d %H:%M:%S %Z')}*",
                    unsafe_allow_html=True
                )
                
                # 4. Expander to hide the description
                # The text is now bold, slightly larger, and only shows the emoji and custom text.
                with st.expander("🔍 Click here to read summary..."): 
                    st.markdown(article['description']) 
                    st.markdown(f"**[Read Full Article at {article['publisher']}]({article['url']})**")
                
        st.divider()

except Exception as e:
    # A generic, user-friendly error message is displayed in the app
    st.error(f"A critical error occurred while fetching news. Please try again or check the ticker symbol. Details: {e}")
    # Log the full error to the console for debugging
    print(f"ERROR: {e}")
