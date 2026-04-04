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

    weekly = [random.randint(40, 70) for _ in range(7)]

    reddit_samples = [
        "Love this brand!",
        "Could be better.",
        "Great quality.",
        "Shipping was slow.",
        "Highly recommend!"
    ]

    x_samples = [
        "Trending now 🔥",
        "Not impressed.",
        "Pretty good overall.",
        "Needs improvement.",
        "Love it!"
    ]

    return positive, neutral, negative, reddit_posts, x_posts, weekly, reddit_samples, x_samples


class Handler(BaseHTTPRequestHandler):

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        brand = params.get("brand", [""])[0]

        if brand:
            pos, neu, neg, reddit, x, weekly, reddit_list, x_list = simulate_sentiment()

            content = f"""
<html>
<head>
<meta charset="UTF-8">
<title>Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>

<body style="margin:0; font-family:Arial; background:#f4f6f9;">

<div style="background:#111827; color:white; padding:15px;">
<h2 style="margin:0;">SentimentAI</h2>
</div>

<div style="max-width:900px; margin:auto; padding:20px;">

<h2>Analysis for "{brand}"</h2>

<div style="display:flex; gap:10px;">
<div style="background:white; padding:10px; flex:1; border-radius:6px;">
<b>Positive</b><br><span style="color:green;">{pos}%</span>
</div>

<div style="background:white; padding:10px; flex:1; border-radius:6px;">
<b>Neutral</b><br><span style="color:gray;">{neu}%</span>
</div>

<div style="background:white; padding:10px; flex:1; border-radius:6px;">
<b>Negative</b><br><span style="color:red;">{neg}%</span>
</div>
</div>

<br>

<div style="display:grid; grid-template-columns:1fr 1fr; gap:15px;">

<div style="background:white; padding:10px; border-radius:6px;">
<canvas id="pieChart" style="max-height:200px;"></canvas>
</div>

<div style="background:white; padding:10px; border-radius:6px;">
<canvas id="barChart" style="max-height:200px;"></canvas>
</div>

<div style="background:white; padding:10px; border-radius:6px; grid-column: span 2;">
<canvas id="lineChart" style="max-height:150px;"></canvas>
</div>

</div>

<br>

<div style="display:flex; gap:10px;">
<div style="background:white; padding:10px; flex:1; border-radius:6px;">
<b>Reddit</b>
{"".join([f"<p>• {p}</p>" for p in reddit_list])}
</div>

<div style="background:white; padding:10px; flex:1; border-radius:6px;">
<b>X</b>
{"".join([f"<p>• {p}</p>" for p in x_list])}
</div>
</div>

<br>
<a href="/">← Back</a>

</div>

<script>
new Chart(document.getElementById('pieChart'), {{
    type: 'pie',
    data: {{
        labels: ['Positive','Neutral','Negative'],
        datasets: [{{
            data: [{pos},{neu},{neg}]
        }}]
    }},
    options: {{
        responsive:true,
        maintainAspectRatio:false
    }}
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
    options: {{
        responsive:true,
        maintainAspectRatio:false
    }}
}});

new Chart(document.getElementById('lineChart'), {{
    type: 'line',
    data: {{
        labels: ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'],
        datasets: [{{
            label: 'Trend',
            data: {weekly}
        }}]
    }},
    options: {{
        responsive:true,
        maintainAspectRatio:false
    }}
}});
</script>

</body>
</html>
"""

        else:
            content = """
<html>
<head>
<meta charset="UTF-8">
<title>Sentiment Dashboard</title>
</head>

<body style="margin:0; font-family:Arial; background:linear-gradient(to right, #1f2937, #3b82f6); color:white;">

<div style="padding:20px; font-size:20px; font-weight:bold;">
SentimentAI
</div>

<div style="display:flex; justify-content:center; align-items:center; height:80vh;">

<div style="
background:white;
color:black;
padding:40px;
border-radius:12px;
width:400px;
text-align:center;
box-shadow:0 10px 25px rgba(0,0,0,0.2);
">

<h1>AI Sentiment Dashboard</h1>

<p style="color:gray;">
Analyze sentiment from Reddit & X instantly
</p>

<form method="GET">
<input 
type="text" 
name="brand" 
placeholder="Enter brand (Nike, Apple...)" 
style="padding:12px; width:100%; border-radius:8px; border:1px solid #ccc; margin-bottom:15px;">

<button 
type="submit" 
style="padding:12px; width:100%; background:#3b82f6; color:white; border:none; border-radius:8px;">
Analyze
</button>
</form>

<p style="font-size:12px; color:gray;">
Powered by AI • Real-time insights
</p>

</div>

</div>

</body>
</html>
"""

        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(content.encode("utf-8"))


port = int(os.environ.get("PORT", 10000))
server = HTTPServer(("0.0.0.0", port), Handler)
server.serve_forever()
