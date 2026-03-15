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




