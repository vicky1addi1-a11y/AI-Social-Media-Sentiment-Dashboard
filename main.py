import os
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse
import json
import random

# ---------- LOAD JSON OR FALLBACK ----------
def load_data(brand):
    filename = f"{brand}_data.json"

    if os.path.exists(filename):
        try:
            with open(filename, "r") as f:
                return json.load(f)
        except:
            pass

    # fallback if file missing
    pos = random.randint(40, 70)
    neu = random.randint(10, 30)
    neg = 100 - pos - neu

    return {
        "pos": pos,
        "neu": neu,
        "neg": neg,
        "reddit": random.randint(50, 120),
        "x": random.randint(40, 100),
        "posts": {
            "reddit": ["Sample Reddit post", "User feedback here"],
            "x": ["Trending topic", "Quick reaction"]
        }
    }

# ---------- HANDLER ----------
class Handler(BaseHTTPRequestHandler):

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        brand = params.get("brand", [""])[0].lower()

        if brand:
            data = load_data(brand)

            content = f"""
<html>
<head>
<title>Sentiment Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<style>
body {{
    font-family: Arial;
    margin: 0;
    background: #f5f7fb;
}}

.container {{
    max-width: 1100px;
    margin: auto;
    padding: 20px;
}}

.card {{
    background: white;
    padding: 15px;
    border-radius: 10px;
    margin: 10px 0;
}}

.row {{
    display: flex;
    gap: 15px;
    flex-wrap: wrap;
}}

.box {{
    flex: 1;
    min-width: 150px;
    text-align: center;
}}

h1 {{
    text-align: center;
}}

button {{
    padding: 8px 12px;
    border-radius: 5px;
    border: none;
    background: #4f46e5;
    color: white;
    cursor: pointer;
}}

.brand-btn {{
    margin: 5px;
    background: #111827;
}}

canvas {{
    max-height: 250px !important;
}}
</style>
</head>

<body>
<div class="container">

<h1>{brand.upper()} Sentiment Dashboard</h1>

<div style="text-align:center;">
<a href="/?brand=nike"><button class="brand-btn">Nike</button></a>
<a href="/?brand=apple"><button class="brand-btn">Apple</button></a>
<a href="/?brand=tesla"><button class="brand-btn">Tesla</button></a>
</div>

<div class="row">
<div class="card box">Positive<br><b>{data['pos']}%</b></div>
<div class="card box">Neutral<br><b>{data['neu']}%</b></div>
<div class="card box">Negative<br><b>{data['neg']}%</b></div>
</div>

<div class="row">
<div class="card">
<canvas id="pie"></canvas>
</div>

<div class="card">
<canvas id="bar"></canvas>
</div>
</div>

<div class="card">
<canvas id="trend"></canvas>
</div>

<div class="row">
<div class="card">
<h3>Reddit</h3>
{"".join(f"<p>• {p}</p>" for p in data["posts"]["reddit"])}
</div>

<div class="card">
<h3>X</h3>
{"".join(f"<p>• {p}</p>" for p in data["posts"]["x"])}
</div>
</div>

<div class="card" style="text-align:center;">
<button onclick="downloadReport()">Download Report</button>
<br><br>
<a href="/">Back</a>
</div>

</div>

<script>
new Chart(document.getElementById('pie'), {{
type: 'pie',
data: {{
labels: ['Positive','Neutral','Negative'],
datasets: [{{
data: [{data['pos']},{data['neu']},{data['neg']}]
}}]
}}
}});

new Chart(document.getElementById('bar'), {{
type: 'bar',
data: {{
labels: ['Reddit','X'],
datasets: [{{
label: 'Posts',
data: [{data['reddit']},{data['x']}]
}}]
}}
}});

new Chart(document.getElementById('trend'), {{
type: 'line',
data: {{
labels: ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'],
datasets: [{{
label: 'Trend',
data: [60,50,45,42,48,66,51]
}}]
}}
}});

function downloadReport() {{
    const data = `{json.dumps(data)}`;
    const blob = new Blob([data], {{type:'application/json'}});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = "report.json";
    a.click();
}}
</script>

</body>
</html>
"""
        else:
            content = """
<html>
<head>
<title>AI Sentiment Dashboard</title>

<style>
body {
    font-family: Arial;
    background: linear-gradient(to right, #4f46e5, #3b82f6);
    color: white;
    text-align: center;
    padding-top: 100px;
}

input {
    padding: 10px;
    width: 250px;
    border-radius: 5px;
    border: none;
}

button {
    padding: 10px;
    border-radius: 5px;
    background: black;
    color: white;
}
</style>
</head>

<body>

<h1>AI Social Media Sentiment</h1>
<p>Analyze brand sentiment across Reddit & X</p>

<form method="GET">
<input name="brand" placeholder="nike, apple, tesla">
<button>Analyze</button>
</form>

</body>
</html>
"""

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(content.encode("utf-8"))

# ---------- RUN ----------
port = int(os.environ.get("PORT", 10000))
server = HTTPServer(("0.0.0.0", port), Handler)

print("Running on port", port)

server.serve_forever()
