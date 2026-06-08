import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import feedparser
import requests

# ===== CONFIGURATION =====
EMAIL_ADDRESS = "your.email@gmail.com"
EMAIL_PASSWORD = "your.gmail.app.password"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
RECIPIENT_EMAIL = "your.email@gmail.com"
MAX_ARTICLES = 10  # Limit to top 10 articles

# ===== FUNCTIONS =====

def calculate_relevance_score(article_title, article_content, source):
    """Calculate a relevance score for the article"""
    title = article_title.lower()
    content = article_content.lower()
    
    score = 0
    
    # High relevance keywords (GIS + AI combination)
    high_relevance_terms = [
        "ai gis", "gis ai", "ai and gis", "gis and ai",
        "machine learning gis", "gis machine learning",
        "deep learning geospatial", "geospatial deep learning",
        "computer vision gis", "gis computer vision",
        "ai remote sensing", "remote sensing ai",
        "artificial intelligence gis", "gis artificial intelligence"
    ]
    
    # Medium relevance keywords
    medium_relevance_terms = [
        "spatial ai", "ai spatial", "geospatial ai", "ai geospatial",
        "satellite imagery ai", "ai satellite imagery",
        "drone mapping ai", "ai drone mapping",
        "urban planning ai", "ai urban planning",
        "environmental monitoring ai", "ai environmental monitoring"
    ]
    
    # Check for high relevance terms
    for term in high_relevance_terms:
        if term in title:
            score += 10
        if term in content:
            score += 5
    
    # Check for medium relevance terms
    for term in medium_relevance_terms:
        if term in title:
            score += 5
        if term in content:
            score += 2
    
    # Individual keyword matches
    gis_terms = ["gis", "geospatial", "spatial", "mapping", "cartography"]
    ai_terms = ["ai", "artificial intelligence", "machine learning", "deep learning", "computer vision"]
    
    for term in gis_terms:
        if term in title:
            score += 3
        if term in content:
            score += 1
    
    for term in ai_terms:
        if term in title:
            score += 3
        if term in content:
            score += 1
    
    # Source weighting
    if "arxiv" in source:
        score += 5
    elif "esri" in source:
        score += 4
    elif "nasa" in source:
        score += 3
    
    return score


def get_news():
    """Fetch news from RSS feeds only (no webpage scraping)"""
    articles = []
    
    feeds = [
        "https://news.google.com/rss/search?q=%22AI+GIS%22+OR+%22GIS+AI%22+OR+%22machine+learning+GIS%22&ceid=US:en&hl=en-US&gl=US",
        "https://news.google.com/rss/search?q=geospatial+artificial+intelligence+OR+spatial+AI&ceid=US:en&hl=en-US&gl=US",
        "https://arxiv.org/rss/cs.AI",
        "https://arxiv.org/rss/cs.CV",
        "https://www.esri.com/arcgis-blog/feed/",
        "https://blog.mapbox.com/rss",
        "https://towardsdatascience.com/feed/tagged/geospatial",
    ]
    
    keywords = [
        "gis", "geospatial", "spatial",
        "ai", "artificial intelligence", "machine learning", "deep learning",
        "remote sensing", "satellite", "imagery",
        "computer vision", "neural network"
    ]
    
    seen_links = set()
    
    for feed_url in feeds:
        try:
            print(f"Checking feed: {feed_url}")
            feed = feedparser.parse(feed_url)
            
            if not feed.entries:
                continue
            
            for entry in feed.entries[:20]:
                if entry.link in seen_links:
                    continue
                
                title = entry.title.lower()
                if not any(keyword in title for keyword in keywords):
                    continue
                
                summary = entry.get('summary', '')
                content = summary if summary else "No summary available."
                
                relevance_score = calculate_relevance_score(entry.title, content, feed_url)
                
                articles.append({
                    'title': entry.title,
                    'link': entry.link,
                    'summary': content[:250] + "..." if len(content) > 250 else content,
                    'source': feed_url,
                    'published': entry.get('published', datetime.now().strftime('%Y-%m-%d')),
                    'score': relevance_score
                })
                
                seen_links.add(entry.link)
        
        except Exception as e:
            print(f"Error parsing feed {feed_url}: {e}")
    
    return articles


def select_top_articles(articles, max_articles=MAX_ARTICLES):
    return sorted(articles, key=lambda x: x['score'], reverse=True)[:max_articles]


def generate_email_content(articles):
    if not articles:
        return "<p>No relevant articles found today.</p>"
    
    html = f"""
    <html>
    <body>
        <h1>🌍 AI & GIS Digest — {datetime.now().strftime('%A, %B %d, %Y')}</h1>
        <p>Top {len(articles)} articles:</p>
    """
    
    for i, article in enumerate(articles, 1):
        html += f"""
        <h3>{i}. {article['title']}</h3>
        <p><strong>Published:</strong> {article['published']}</p>
        <p>{article['summary']}</p>
        <p><a href="{article['link']}">Read full article</a></p>
        <hr>
        """
    
    html += "</body></html>"
    return html


def send_email_smtp(content):
    msg = MIMEMultipart("alternative")
    msg['Subject'] = f"AI & GIS Digest — {datetime.now().strftime('%Y-%m-%d')}"
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = RECIPIENT_EMAIL
    msg.attach(MIMEText(content, "html"))
    
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        print("Email sent successfully.")
    except Exception as e:
        print(f"Error sending email: {e}")


def run_once():
    articles = get_news()
    top_articles = select_top_articles(articles)
    content = generate_email_content(top_articles)
    send_email_smtp(content)


# ===== MAIN EXECUTION =====
if __name__ == "__main__":
    run_once()
