import asyncio
import json
import time
import os
from web3 import Web3
from eth_account import Account
from colorama import Fore, init
import requests
import aiohttp

init(autoreset=True)

# Konfigurasi
RPC_URL = "https://mainnet.base.org"
CHAIN_ID = 8453
CONTRACT_ADDRESS = "0xC5bf05cD32a14BFfb705Fb37a9d218895187376c"
AMOUNT_ETH = 0.0000001
GAS_LIMIT = 210000
GAS_PRICE_GWEI = 0.0016
DELAY_BETWEEN_TX = 10
TX_PER_CYCLE = 150
SLEEP_AFTER_CYCLE = 300
API_URL = "https://hanafuda-backend-app-520478841386.us-central1.run.app/graphql"
FIREBASE_API_KEY = "AIzaSyDipzN0VRfTPnMGhQ5PSzO27Cxm3DohJGY"

# Telegram
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

web3 = Web3(Web3.HTTPProvider(RPC_URL))
contract = web3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=json.loads('[{"inputs":[],"name":"depositETH","outputs":[],"stateMutability":"payable","type":"function"}]'))

def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID:
        print(Fore.YELLOW + "Telegram bot/chat ID belum di-set.")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    except Exception as e:
        print(Fore.RED + f"Telegram error: {e}")

private_keys = os.getenv("PRIVATE_KEYS", "").split(",")
refresh_tokens = os.getenv("TOKENS", "").split(",")

async def deposit_loop():
    for i in range(TX_PER_CYCLE):
        for pk in private_keys:
            acct = Account.from_key(pk)
            nonce = web3.eth.get_transaction_count(acct.address)
            try:
                tx = contract.functions.depositETH().build_transaction({
                    'from': acct.address,
                    'value': web3.to_wei(AMOUNT_ETH, 'ether'),
                    'gas': GAS_LIMIT,
                    'gasPrice': web3.to_wei(GAS_PRICE_GWEI, 'gwei'),
                    'nonce': nonce,
                    'chainId': CHAIN_ID
                })
                signed_tx = web3.eth.account.sign_transaction(tx, pk)
                tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
                link = f"https://basescan.org/tx/{tx_hash.hex()}"
                msg = f"✅ [TX {i+1}/{TX_PER_CYCLE}] *SUKSES:* [{tx_hash.hex()}]({link})"
                print(Fore.GREEN + msg)
                send_telegram(msg)
            except Exception as e:
                msg = f"❌ [TX {i+1}] *ERROR:* {str(e)}"
                print(Fore.RED + msg)
                send_telegram(msg)
            await asyncio.sleep(DELAY_BETWEEN_TX)
    print(Fore.CYAN + f"\nSelesai {TX_PER_CYCLE} TX. Tidur {SLEEP_AFTER_CYCLE//60} menit...\n")
    time.sleep(SLEEP_AFTER_CYCLE)

async def refresh_access_token(session, refresh_token):
    async with session.post(
        f'https://securetoken.googleapis.com/v1/token?key={FIREBASE_API_KEY}',
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data=f'grant_type=refresh_token&refresh_token={refresh_token}'
    ) as response:
        if response.status != 200:
            raise Exception("Failed to refresh token")
        return (await response.json())["access_token"]

async def grow_action(session, token, index):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    try:
        q = {"query": "mutation executeGrowAction { executeGrowAction(withAll: true) { totalValue } }"}
        async with session.post(API_URL, json=q, headers=headers) as res:
            data = await res.json()
            val = data["data"]["executeGrowAction"]["totalValue"]
            msg = f"✅ Akun {index}: *Grow Berhasil* +{val} POINT"
            print(Fore.GREEN + msg)
            send_telegram(msg)
    except Exception as e:
        msg = f"❌ Akun {index}: *Grow Gagal:* {str(e)}"
        print(Fore.RED + msg)
        send_telegram(msg)

async def grow_loop():
    async with aiohttp.ClientSession() as session:
        for i, rt in enumerate(refresh_tokens, 1):
            try:
                token = await refresh_access_token(session, rt)
                await grow_action(session, token, i)
            except Exception as e:
                print(Fore.RED + f"Token {i} error: {e}")
    print(Fore.YELLOW + "Selesai semua akun grow. Tidur 1 jam...\n")
    time.sleep(3600)

async def mode_3_loop():
    while True:
        await deposit_loop()
        await grow_loop()

def pilih_mode():
    return os.getenv("MODE", "1")  # default ke mode 1 jika tidak di-set

if __name__ == "__main__":
    mode = pilih_mode()
    if mode == "1":
        asyncio.run(deposit_loop())
    elif mode == "2":
        asyncio.run(grow_loop())
    elif mode == "3":
        asyncio.run(mode_3_loop())
    else:
        print(Fore.RED + "MODE tidak valid. Gunakan 1 / 2 / 3.")

