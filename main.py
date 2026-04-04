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
    weekly_data = [random.randint(40, 80) for _ in range(7)]

    # fake realistic posts
    reddit_samples = [
        "I’ve been using this product for months and it’s amazing!",
        "Honestly not worth the price in my opinion.",
        "Customer service was helpful but slow.",
        "This completely changed my workflow!",
        "I wouldn’t recommend this to beginners."
    ]

    x_samples = [
        "Loving this brand lately 🔥",
        "Worst experience ever with this company.",
        "It’s okay… nothing special.",
        "Super impressed with the quality!",
        "Not bad, but could be better."
    ]

    return positive, neutral, negative, reddit_posts, x_posts, weekly_data, reddit_samples, x_samples


class Handler(BaseHTTPRequestHandler):

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        brand = params.get("brand", [""])[0]

        if brand:
            pos, neu, neg, reddit, x, weekly, reddit_posts_list, x_posts_list = simulate_sentiment()

            # CSV download
            if "download" in params:
                csv = f"Brand,Positive,Neutral,Negative,Reddit,X\n{brand},{pos},{neu},{neg},{reddit},{x}"
                self.send_response(200)
                self.send_header("Content-type", "text/csv")
                self.send_header("Content-Disposition", "attachment; filename=report.csv")
                self.end_headers()
                self.wfile.write(csv.encode())
                return

            content = f"""
            <html>
            <head>
            <title>AI Sentiment Dashboard</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            </head>

            <body style="font-family:Arial; margin:0; background:#f4f6f9;">

            <!-- NAVBAR -->
            <div style="background:#111827; color:white; padding:15px; display:flex; justify-content:space-between;">
                <h2>SentimentAI</h2>
                <p>Dashboard</p>
            </div>

            <div style="padding:30px;">

            <h1>Analysis for "{brand}"</h1>

            <!-- SUMMARY -->
            <div style="display:flex; gap:20px;">
                <div style="background:white; padding:20px; border-radius:10px; width:30%;">
                    <h3>Positive</h3>
                    <h2 style="color:green;">{pos}%</h2>
                </div>

                <div style="background:white; padding:20px; border-radius:10px; width:30%;">
                    <h3>Neutral</h3>
                    <h2 style="color:gray;">{neu}%</h2>
                </div>

                <div style="background:white; padding:20px; border-radius:10px; width:30%;">
                    <h3>Negative</h3>
                    <h2 style="color:red;">{neg}%</h2>
                </div>
            </div>

            <br>

            <!-- CHARTS -->
            <div style="background:white; padding:20px; border-radius:10px;">
                <canvas id="pieChart"></canvas>
            </div>

            <br>

            <div style="background:white; padding:20px; border-radius:10px;">
                <canvas id="barChart"></canvas>
            </div>

            <br>

            <div style="background:white; padding:20px; border-radius:10px;">
                <canvas id="lineChart"></canvas>
            </div>

            <br>

            <!-- SAMPLE POSTS -->
            <div style="display:flex; gap:20px;">
                
                <div style="background:white; padding:20px; border-radius:10px; width:50%;">
                    <h3>Reddit Posts</h3>
                    {"".join([f"<p>• {p}</p>" for p in reddit_posts_list])}
                </div>

                <div style="background:white; padding:20px; border-radius:10px; width:50%;">
                    <h3>X Posts</h3>
                    {"".join([f"<p>• {p}</p>" for p in x_posts_list])}
                </div>

            </div>

            <br>

            <!-- DOWNLOAD BUTTON -->
            <a href="/?brand={brand}&download=true">
                <button style="padding:12px 20px; background:#3b82f6; color:white; border:none; border-radius:8px;">
                    Download Report (CSV)
                </button>
            </a>

            <br><br>

            <a href="/">← Back</a>

            </div>

            <!-- CHARTS -->
            <script>
            new Chart(document.getElementById('pieChart'), {{
                type: 'pie',
                data: {{
                    labels: ['Positive','Neutral','Negative'],
                    datasets: [{{
                        data: [{pos},{neu},{neg}],
                        backgroundColor: ['green','gray','red']
                    }}]
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
            <title>SentimentAI</title>
            </head>

            <body style="font-family:Arial; margin:0; background:#111827; color:white;">

            <div style="text-align:center; padding:120px;">
                <h1 style="font-size:45px;">SentimentAI</h1>
                <p style="color:#9ca3af;">AI-powered social media sentiment analysis</p>

                <br><br>

                <form method="GET">
                    <input type="text" name="brand"
                    placeholder="Enter brand (Nike, Apple...)"
                    style="padding:15px; width:300px; border-radius:8px; border:none;">

                    <br><br>

                    <button type="submit"
                    style="padding:15px 30px; background:#3b82f6; color:white; border:none; border-radius:8px;">
                    Analyze
                    </button>
                </form>

                <br><br>

                <p style="color:#6b7280;">Built with Python • Hosted on Render • Version-controlled on GitHub</p>
            </div>

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
