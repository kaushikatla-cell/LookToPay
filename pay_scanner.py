import cv2
from pyzbar.pyzbar import decode
from web3 import Web3
import requests
import time
import os

RPC = "https://eth.llamarpc.com"
w3 = Web3(Web3.HTTPProvider(RPC))

private_key = "55d253c81b9da6022152a0c1683c4d5b65a8db87f0b2abf41e961692c1a42022"

account = w3.eth.account.from_key(private_key)

cap = cv2.VideoCapture(0)
cap.set(3,640)
cap.set(4,480)

status = "Scanning..."
last_data = ""

def dashboard(msg):
    os.system("clear")
    print("===================================")
    print("        VISIONPAY DASHBOARD        ")
    print("===================================")
    print("")
    print("Wallet:", account.address)
    print("")
    print("STATUS:", msg)
    print("")
    print("Press CTRL+C to stop")
    print("===================================")

def get_eth_price():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"
        r = requests.get(url).json()
        return r["ethereum"]["usd"]
    except:
        return None

def send_eth(receiver, amount):

    dashboard("Preparing transaction...")

    nonce = w3.eth.get_transaction_count(account.address)

    tx = {
        "nonce": nonce,
        "to": receiver,
        "value": w3.to_wei(amount, "ether"),
        "gas": 21000,
        "gasPrice": w3.to_wei("20", "gwei"),
        "chainId": 1
    }

    signed_tx = w3.eth.account.sign_transaction(tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

    dashboard("Transaction submitted")

    print("")
    print("TX HASH:", tx_hash.hex())
    print("https://etherscan.io/tx/" + tx_hash.hex())

    try:
        w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        dashboard("Transaction confirmed")
    except:
        dashboard("Transaction pending")

dashboard("Scanning for QR codes...")

while True:

    ret, frame = cap.read()
    codes = decode(frame)

    for qr in codes:

        data = qr.data.decode("utf-8")

        if data != last_data:

            if data.startswith("ethereum:"):

                parts = data.replace("ethereum:", "").split("?")

                address = parts[0]
                amount = float(parts[1].split("=")[1])

                eth_price = get_eth_price()

                if eth_price:
                    usd_value = amount * eth_price
                    dashboard(f"Detected {amount} ETH (${usd_value:.2f})")
                else:
                    dashboard(f"Detected {amount} ETH")

                if amount > 0.02:
                    dashboard("Payment blocked: amount too large")
                else:
                    dashboard("Sending payment...")
                    send_eth(address, amount)

            last_data = data

    time.sleep(0.2)
