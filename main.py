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
<title>Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>

<body style="margin:0; font-family:Arial; background:#f4f6f9;">

<!-- NAV -->
<div style="background:#111827; color:white; padding:15px;">
<h2 style="margin:0;">SentimentAI</h2>
</div>

<!-- MAIN CONTAINER -->
<div style="max-width:900px; margin:auto; padding:20px;">

<h2>Analysis: "{brand}"</h2>

<!-- CARDS -->
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

<!-- CHARTS -->
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

<!-- POSTS -->
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
<head></head>
<body style="font-family:Arial; text-align:center; margin-top:120px; background:#f4f6f9;">
<h1>Sentiment Dashboard</h1>
<form method="GET">
<input name="brand" placeholder="Enter brand" style="padding:8px;">
<button type="submit">Analyze</button>
</form>
</body>
</html>
"""

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(content.encode())


port = int(os.environ.get("PORT", 10000))
server = HTTPServer(("0.0.0.0", port), Handler)
server.serve_forever()
