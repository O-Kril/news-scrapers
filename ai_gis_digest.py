import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import feedparser
import requests
from bs4 import BeautifulSoup
import re

# ===== CONFIGURATION =====
EMAIL_ADDRESS = "your.email@gmail.com"  # Your Gmail address
EMAIL_PASSWORD = "your.gmail.app.password"    # Your Gmail app password 
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
RECIPIENT_EMAIL = "your.email@gmail.com"
MAX_ARTICLES = 10  # Limit to top 10 articles

# ===== FUNCTIONS =====
def extract_content_from_url(url):
    """Extract content from a URL"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove unwanted elements
        for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
            element.decompose()
        
        # Get text and clean it up
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text[:250] + "..." if len(text) > 250 else text
    except Exception as e:
        print(f"Error extracting content from {url}: {e}")
        return "Content not available"

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
    
    # Medium relevance keywords (specific applications)
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
    
    # Source weighting (prefer certain sources)
    if "arxiv" in source:
        score += 5  # Academic papers are highly relevant
    elif "esri" in source:
        score += 4  # Esri content is very GIS-focused
    elif "nasa" in source:
        score += 3  # NASA has quality geospatial content
    
    # Recency bonus (if we can parse the date)
    try:
        published_date = article.get('published', '')
        if '2025' in published_date or '2024' in published_date:
            score += 2
    except:
        pass
    
    return score

def get_news():
    """Fetch news from various sources based on AI and GIS keywords"""
    articles = []
    
    # Define RSS feeds - focused on highest quality sources
    feeds = [
        # Google News searches (more specific)
        "https://news.google.com/rss/search?q=%22AI+GIS%22+OR+%22GIS+AI%22+OR+%22machine+learning+GIS%22&ceid=US:en&hl=en-US&gl=US",
        "https://news.google.com/rss/search?q=geospatial+artificial+intelligence+OR+spatial+AI&ceid=US:en&hl=en-US&gl=US",
        
        # Academic sources
        "https://arxiv.org/rss/cs.AI",  # AI papers
        "https://arxiv.org/rss/cs.CV",  # Computer Vision papers
        
        # GIS blogs
        "https://www.esri.com/arcgis-blog/feed/",
        "https://blog.mapbox.com/rss",
        
        # Quality tech blogs
        "https://towardsdatascience.com/feed/tagged/geospatial",
    ]
    
    # Keywords to look for
    keywords = [
        "gis", "geospatial", "spatial", 
        "ai", "artificial intelligence", "machine learning", "deep learning",
        "remote sensing", "satellite", "imagery",
        "computer vision", "neural network", "QGIS", "ArcGIS", "Remote Sensing", 
    ]
    
    seen_links = set()
    
    # Process RSS feeds
    for feed_url in feeds:
        try:
            print(f"Checking feed: {feed_url}")
            feed = feedparser.parse(feed_url)
            
            if not feed.entries:
                print(f"  No entries found in this feed")
                continue
                
            for entry in feed.entries[:20]:  # Limit to first 20 entries per feed
                # Check if we've seen this link before
                if entry.link in seen_links:
                    continue
                
                # Check if the title contains any of our keywords
                title = entry.title.lower()
                if any(keyword in title for keyword in keywords):
                    # Get summary/content
                    summary = entry.get('summary', '')
                    if not summary or len(summary) < 50:
                        content = extract_content_from_url(entry.link)
                    else:
                        content = summary
                    
                    # Calculate relevance score
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
                    print(f"  Added: {entry.title} (Score: {relevance_score})")
        except Exception as e:
            print(f"Error parsing feed {feed_url}: {e}")
    
    return articles

def select_top_articles(articles, max_articles=MAX_ARTICLES):
    """Select the top N most relevant articles"""
    # Sort by relevance score (descending)
    sorted_articles = sorted(articles, key=lambda x: x['score'], reverse=True)
    
    # Return top N articles
    return sorted_articles[:max_articles]

def generate_email_content(articles):
    """Generate HTML email content from articles"""
    if not articles:
        return "<p>No relevant articles found today. Check back tomorrow!</p>"
    
    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; }}
            .header {{ background-color: #f8f9fa; padding: 20px; text-align: center; border-bottom: 2px solid #4CAF50; }}
            .article {{ margin-bottom: 25px; padding: 15px; border-left: 4px solid #4CAF50; background-color: #f9f9f9; }}
            .article h3 {{ margin-top: 0; color: #2c3e50; }}
            .article a {{ color: #3498db; text-decoration: none; }}
            .article a:hover {{ text-decoration: underline; }}
            .meta {{ font-size: 0.9em; color: #7f8c8d; margin-bottom: 10px; }}
            .score {{ float: right; background-color: #4CAF50; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; }}
            .footer {{ margin-top: 30px; padding: 15px; text-align: center; font-size: 0.9em; color: #7f8c8d; border-top: 1px solid #eee; }}
            .source-badge {{ display: inline-block; padding: 3px 8px; border-radius: 4px; font-size: 0.8em; margin-right: 8px; }}
            .source-arxiv {{ background-color: #b6e3ff; color: #005c9e; }}
            .source-google {{ background-color: #fce8e6; color: #c5221f; }}
            .source-esri {{ background-color: #e6f4ea; color: #137333; }}
            .source-medium {{ background-color: #000; color: white; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🌍 AI & GIS Daily Digest</h1>
            <p>{datetime.now().strftime('%A, %B %d, %Y')}</p>
            <p>Top {len(articles)} most relevant articles curated for you</p>
        </div>
    """
    
    for i, article in enumerate(articles, 1):
        # Determine source type for styling
        source_class = ""
        source_name = "Other"
        
        if "arxiv" in article['source']:
            source_class = "source-arxiv"
            source_name = "arXiv"
        elif "google" in article['source']:
            source_class = "source-google"
            source_name = "Google News"
        elif "esri" in article['source']:
            source_class = "source-esri"
            source_name = "Esri"
        elif "medium" in article['source'] or "towardsdatascience" in article['source']:
            source_class = "source-medium"
            source_name = "Blog"
            
        html_content += f"""
        <div class="article">
            <span class="score">Relevance: {article['score']}</span>
            <h3>{i}. {article['title']}</h3>
            <div class="meta">
                <span class="source-badge {source_class}">{source_name}</span>
                <strong>Published:</strong> {article['published']}
            </div>
            <p>{article['summary']}</p>
            <p><a href="{article['link']}">📖 Read full article</a></p>
        </div>
        """
    
    html_content += f"""
        <div class="footer">
            <p>Curated from {len(articles)} most relevant articles found today</p>
            <p>This digest was automatically generated for Giovanni Bwayo</p>
        </div>
    </body>
    </html>
    """
    return html_content

def send_email_smtp(content):
    """Send email using SMTP"""
    msg = MIMEMultipart("alternative")
    msg['Subject'] = f"AI & GIS Daily Digest - {datetime.now().strftime('%Y-%m-%d')}"
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = RECIPIENT_EMAIL
    
    msg.attach(MIMEText(content, "html"))
    
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        print(f"{datetime.now()}: Email sent successfully to {RECIPIENT_EMAIL}")
        return True
    except Exception as e:
        print(f"{datetime.now()}: Error sending email: {e}")
        return False

def send_daily_digest():
    """Main function to fetch news and send email"""
    print(f"{datetime.now()}: Starting to fetch AI & GIS news...")
    
    # Get news articles
    articles = get_news()
    print(f"{datetime.now()}: Found {len(articles)} potential articles")
    
    # Select top articles
    top_articles = select_top_articles(articles)
    print(f"{datetime.now()}: Selected top {len(top_articles)} articles")
    
    # Generate email content
    email_content = generate_email_content(top_articles)
    
    # Send email
    success = send_email_smtp(email_content)
    
    if success:
        print(f"{datetime.now()}: Digest sent with {len(top_articles)} articles")
    else:
        print(f"{datetime.now()}: Failed to send digest")

def run_once():
    """Run the digest once (for testing)"""
    send_daily_digest()

# ===== MAIN EXECUTION =====
if __name__ == "__main__":
    print("AI & GIS Daily Digest System")
    print("============================")
    
    # Run once and exit (GitHub Actions will schedule it)
    run_once()

