import os
import random
import time
from TikTokApi import TikTokApi
from bs4 import BeautifulSoup
import requests
import json
from datetime import datetime

# Configuration
ACCOUNTS_FILE = "accounts.txt"  # Format: username:password or sessionid
MESSAGE_FILE = "message.txt"
TARGETS_FILE = "targets.txt"
PROXY_FILE = "proxies.txt"
SLEEP_BETWEEN_ACCOUNTS = 120  # seconds
MAX_ATTEMPTS = 3
MESSAGE_DELAY = 30  # seconds between messages

def scrape_proxies():
    """Scrape HTTPS proxies suitable for TikTok"""
    print("Scraping proxies...")
    proxy_urls = [
        "https://www.sslproxies.org/",
        "https://free-proxy-list.net/",
        "https://hidemy.name/en/proxy-list/"
    ]
    
    proxies = []
    
    for url in proxy_urls:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Parse proxy list (adjust selectors based on website)
            table = soup.find('table')
            if table:
                rows = table.find_all('tr')[1:11]  # Get first 10 proxies
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        ip = cols[0].text.strip()
                        port = cols[1].text.strip()
                        proxies.append(f"{ip}:{port}")
        except Exception as e:
            print(f"Error scraping proxies from {url}: {e}")
    
    # Save proxies to file
    with open(PROXY_FILE, 'w') as f:
        f.write('\n'.join(proxies))
    
    return proxies

def load_proxies():
    """Load proxies from file or scrape new ones if file doesn't exist"""
    if os.path.exists(PROXY_FILE):
        with open(PROXY_FILE, 'r') as f:
            proxies = [line.strip() for line in f.readlines() if line.strip()]
    else:
        proxies = scrape_proxies()
    return proxies

def load_accounts():
    """Load TikTok accounts from file"""
    if not os.path.exists(ACCOUNTS_FILE):
        raise FileNotFoundError(f"{ACCOUNTS_FILE} not found")
    
    accounts = []
    with open(ACCOUNTS_FILE, 'r') as f:
        for line in f.readlines():
            if line.strip():
                parts = line.strip().split(':')
                if len(parts) >= 2:
                    account = {
                        'username': parts[0],
                        'password': parts[1],
                        'sessionid': parts[2] if len(parts) > 2 else None
                    }
                    accounts.append(account)
    return accounts

def load_message():
    """Load message from file"""
    if not os.path.exists(MESSAGE_FILE):
        raise FileNotFoundError(f"{MESSAGE_FILE} not found")
    
    with open(MESSAGE_FILE, 'r') as f:
        message = f.read().strip()
    return message

def load_targets():
    """Load target users from file"""
    if not os.path.exists(TARGETS_FILE):
        raise FileNotFoundError(f"{TARGETS_FILE} not found")
    
    with open(TARGETS_FILE, 'r') as f:
        targets = [line.strip() for line in f.readlines() if line.strip()]
    return targets

def init_tiktok_client(account, proxy=None):
    """Initialize TikTok client with optional proxy"""
    try:
        # TikTokApi configuration
        custom_device_id = None
        custom_verify_fp = None
        
        # If using session cookie
        if account['sessionid']:
            return TikTokApi.get_instance(
                custom_device_id=custom_device_id,
                custom_verify_fp=custom_verify_fp,
                use_test_endpoints=False,
                proxy=proxy,
                **{
                    'headers': {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36',
                        'Cookie': f'sessionid={account["sessionid"]}'
                    }
                }
            )
        
        # Otherwise try to login (may require CAPTCHA solving)
        api = TikTokApi.get_instance(
            custom_device_id=custom_device_id,
            custom_verify_fp=custom_verify_fp,
            use_test_endpoints=False,
            proxy=proxy
        )
        
        # This may not work due to TikTok's strict login requirements
        api.login(
            username=account['username'],
            password=account['password']
        )
        
        return api
    except Exception as e:
        print(f"Error initializing TikTok client: {e}")
        return None

def send_tiktok_message(api, target_username, message):
    """Send message to target user"""
    try:
        # TikTok doesn't have a direct public API for DMs
        # This would require using the private API or browser automation
        
        # Alternative: Comment on user's video (if allowed)
        user_videos = api.by_username(target_username, count=1)
        if user_videos:
            video_id = user_videos[0]['id']
            api.comment(
                video_id=video_id,
                text=message,
                count=1,
                cursor=0
            )
            print(f"Comment sent to @{target_username}'s video")
            return True
        
        print(f"No videos found for @{target_username} to comment on")
        return False
        
    except Exception as e:
        print(f"Failed to send message to @{target_username}: {e}")
        return False

def main():
    # Load data
    accounts = load_accounts()
    message = load_message()
    targets = load_targets()
    proxies = load_proxies()
    
    if not accounts:
        print("No accounts found")
        return
    
    if not targets:
        print("No targets found")
        return
    
    if not message:
        print("No message found")
        return
    
    # Process each account
    for i, account in enumerate(accounts):
        print(f"\nProcessing account {i+1}/{len(accounts)}: {account['username']}")
        
        # Select proxy (if available)
        proxy = None
        if proxies:
            proxy = f"http://{random.choice(proxies)}"
            print(f"Using proxy: {proxy}")
        
        # Initialize client
        api = init_tiktok_client(account, proxy)
        if not api:
            print("Failed to initialize TikTok client")
            continue
        
        # Process targets
        successful_sends = 0
        for target in targets:
            attempts = 0
            while attempts < MAX_ATTEMPTS:
                if send_tiktok_message(api, target, message):
                    successful_sends += 1
                    break
                attempts += 1
                time.sleep(MESSAGE_DELAY)  # Wait before retry
            
            # Add delay between messages to avoid rate limits
            if successful_sends > 0 and successful_sends < len(targets):
                time.sleep(MESSAGE_DELAY)
        
        print(f"Account {account['username']} sent {successful_sends}/{len(targets)} messages successfully")
        
        # Sleep between accounts if not last account
        if i < len(accounts) - 1:
            print(f"Waiting {SLEEP_BETWEEN_ACCOUNTS} seconds before next account...")
            time.sleep(SLEEP_BETWEEN_ACCOUNTS)

if __name__ == "__main__":
    main()