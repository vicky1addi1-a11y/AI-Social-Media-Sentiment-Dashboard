import os
import random
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse

def simulate_sentiment():
 positive = random.randint(40, 70)
 neutral = random.randint(10, 30)
 negative = 100 - positive - neutral
 reddit_posts = random.randint(50, 120)
 x_posts = random.randint(40, 100)
 return positive, neutral, negative, reddit_posts, x_posts
class Handler(BaseHTTPRequestHandler):
def do_GET(self):
parsed = urllib.parse.urlparse(self.path)
params = urllib.parse.parse_qs(parsed.query)
brand = params.get("brand", [""])[0]
if brand:
pos, neu, neg, reddit, x = simulate_sentiment()
content = f"""
<html>
<head>
<title>Sentiment Dashboard</title>
</head>
<body style="font-family:Arial; margin:40px; background:#f4f4f4">
<h1>Sentiment Analysis for "{brand}"</h1>
<h2>Sentiment Summary</h2>
<p>Positive: {pos}%</p>
<p>Neutral: {neu}%</p>
<p>Negative: {neg}%</p>
<h2>Platform Activity</h2>
<p>Reddit Posts: {reddit}</p>
<p>X Posts: {x}</p>
<h2>Insights</h2>
<ul>
<li>Overall sentiment appears {"positive" if pos > neg else "negative"}.</li>
<li>Reddit conversations show deeper discussions.</li>
<li>X shows quick public reactions.</li>
</ul>
<br>
<a href="/">Back to Dashboard</a>
</body>
</html>
"""
else:
content = """
<html>
<head>
</head>
<title>AI Social Media Sentiment Dashboard</title>
<body style="font-family:Arial; margin:40px; background:#f4f4f4">
<h1>AI Social Media Sentiment Dashboard</h1>
<form method="GET">
<label>Enter Brand or Keyword</label><br><br>
<input type="text" name="brand" placeholder="Example: Nike" style="padding:8px; width:300px;">
<button type="submit" style="padding:8px;">Analyze</button>
</form>
<p>This dashboard simulates sentiment results from Reddit and X.</p>
</body>
</html>
"""
self.send_response(200)
self.send_header("Content-type", "text/html")
self.end_headers()
self.wfile.write(content.encode())
port = int(os.environ.get("PORT", 10000))
print("Server running on port", port)
server = HTTPServer(("0.0.0.0", port), Handler)
server.serve_forever()


