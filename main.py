import os
import random
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse

# --- SIMULATED DATA ---
def simulate_sentiment():
    positive = random.randint(40, 70)
    neutral = random.randint(10, 30)
    negative = 100 - positive - neutral
    reddit_posts = random.randint(50, 120)
    x_posts = random.randint(40, 100)

    weekly = [random.randint(40, 70) for _ in range(7)]

    reddit_samples = [
        "Love this brand, quality is amazing!",
        "Customer service could be better.",
        "Best purchase I made this year.",
        "Shipping was slow but product is good.",
        "Highly recommend to everyone!"
    ]

    x_samples = [
        "🔥 This brand is trending right now!",
        "Not impressed with the latest release.",
        "Decent overall experience.",
        "Customer support needs improvement.",
        "Absolutely love it!"
    ]

    return positive, neutral, negative, reddit_posts, x_posts, weekly, reddit_samples, x_samples


class Handler(BaseHTTPRequestHandler):

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        brand = params.get("brand", [""])[0]
        download = params.get("download", [""])[0]

        if brand and download:
            # --- DOWNLOAD REPORT ---
            pos, neu, neg, reddit, x, weekly, _, _ = simulate_sentiment()
            report = f"""
Sentiment Report for {brand}

Positive: {pos}%
Neutral: {neu}%
Negative: {neg}%

Reddit Posts: {reddit}
X Posts: {x}
"""
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.send_header("Content-Disposition", f"attachment; filename={brand}_report.txt")
            self.end_headers()
            self.wfile.write(report.encode())
            return

        if brand:
            pos, neu, neg, reddit, x, weekly, reddit_posts_list, x_posts_list = simulate_sentiment()

            content = f"""
<html>
<head>
<title>Sentiment Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>

<body style="font-family:Arial; margin:0; background:#f4f6f9;">

<!-- NAVBAR -->
<div style="background:#111827; color:white; padding:15px;">
<h2 style="margin:0;">SentimentAI Dashboard</h2>
</div>

<div style="max-width:1100px; margin:auto; padding:30px;">

<h1>Analysis for "{brand}"</h1>

<!-- CARDS -->
<div style="display:flex; gap:15px; margin-bottom:20px;">
<div style="background:white; padding:15px; border-radius:8px; flex:1;">
<h4>Positive</h4>
<h2 style="color:green;">{pos}%</h2>
</div>

<div style="background:white; padding:15px; border-radius:8px; flex:1;">
<h4>Neutral</h4>
<h2 style="color:gray;">{neu}%</h2>
</div>

<div style="background:white; padding:15px; border-radius:8px; flex:1;">
<h4>Negative</h4>
<h2 style="color:red;">{neg}%</h2>
</div>
</div>

<!-- CHARTS -->
<div style="display:grid; grid-template-columns:1fr 1fr; gap:20px;">

<div style="background:white; padding:15px; border-radius:8px;">
<h4>Sentiment Breakdown</h4>
<canvas id="pieChart" height="200"></canvas>
</div>

<div style="background:white; padding:15px; border-radius:8px;">
<h4>Platform Comparison</h4>
<canvas id="barChart" height="200"></canvas>
</div>

<div style="background:white; padding:15px; border-radius:8px; grid-column: span 2;">
<h4>Weekly Trend</h4>
<canvas id="lineChart" height="120"></canvas>
</div>

</div>

<br>

<!-- POSTS -->
<div style="display:flex; gap:20px;">

<div style="background:white; padding:15px; border-radius:8px; flex:1;">
<h4>Reddit Posts</h4>
{"".join([f"<p>• {p}</p>" for p in reddit_posts_list])}
</div>

<div style="background:white; padding:15px; border-radius:8px; flex:1;">
<h4>X Posts</h4>
{"".join([f"<p>• {p}</p>" for p in x_posts_list])}
</div>

</div>

<br>

<!-- BUTTON -->
<a href="/?brand={brand}&download=true">
<button style="padding:10px 18px; background:#3b82f6; color:white; border:none; border-radius:6px;">
Download Report
</button>
</a>

<br><br>
<a href="/">← Back</a>

</div>

<!-- CHARTS SCRIPT -->
<script>
new Chart(document.getElementById('pieChart'), {{
    type: 'pie',
    data: {{
        labels: ['Positive','Neutral','Negative'],
        datasets: [{{
            data: [{pos},{neu},{neg}],
            backgroundColor: ['green','gray','red']
        }}]
    }},
    options: {{ responsive:true, maintainAspectRatio:false }}
}});

new Chart(document.getElementById('barChart'), {{
    type: 'bar',
    data: {{
        labels: ['Reddit','X'],
        datasets: [{{
            label: 'Posts',
            data: [{reddit},{x}]
        }}]
    }},
    options: {{ responsive:true, maintainAspectRatio:false }}
}});

new Chart(document.getElementById('lineChart'), {{
    type: 'line',
    data: {{
        labels: ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'],
        datasets: [{{
            label: 'Trend',
            data: {weekly},
            tension: 0.3
        }}]
    }},
    options: {{ responsive:true, maintainAspectRatio:false }}
}});
</script>

</body>
</html>
"""

        else:
            # --- HOME PAGE ---
            content = """
<html>
<head>
<title>AI Sentiment Dashboard</title>
</head>

<body style="font-family:Arial; background:#f4f6f9; text-align:center; padding-top:100px;">

<h1>AI Social Media Sentiment Dashboard</h1>

<p>Analyze brand sentiment from Reddit & X</p>

<form method="GET">
<input type="text" name="brand" placeholder="Enter brand (Nike, Apple...)" 
style="padding:10px; width:250px; border-radius:5px;">
<br><br>
<button type="submit" style="padding:10px 20px; background:#3b82f6; color:white; border:none; border-radius:5px;">
Analyze
</button>
</form>

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
