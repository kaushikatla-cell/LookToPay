from flask import Flask, render_template_string, Response, jsonify
import threading
import cv2
from pyzbar.pyzbar import decode
from web3 import Web3
import requests
import time

app = Flask(__name__)

RPC = "https://eth.llamarpc.com"
w3 = Web3(Web3.HTTPProvider(RPC))

private_key = "55d253c81b9da6022152a0c1683c4d5b65a8db87f0b2abf41e961692c1a42022"
account = w3.eth.account.from_key(private_key)

status = "Scanning for QR codes..."
payment_confirmed = False
last_data = ""

HTML = """
<!DOCTYPE html>
<html>
<head>
<title>VisionPay Dashboard</title>

<style>
body{
font-family:Arial;
background:#111;
color:white;
text-align:center;
}

.box{
background:#222;
padding:20px;
margin:20px auto;
border-radius:10px;
width:720px;
}

h1{
color:#00ff88;
}

img{
border-radius:10px;
border:2px solid #00ff88;
}

#confirm{
display:none;
background:#00ff88;
color:black;
font-weight:bold;
padding:15px;
border-radius:8px;
margin:20px auto;
width:400px;
animation:flash 1s infinite;
}

@keyframes flash{
0%{opacity:1;}
50%{opacity:0.3;}
100%{opacity:1;}
}
</style>

<script>
setInterval(() => {

fetch('/status')
.then(r => r.json())
.then(data => {

document.getElementById("status").innerText = data.status

if(data.confirmed){
document.getElementById("confirm").style.display="block"
setTimeout(()=>{
document.getElementById("confirm").style.display="none"
},3000)
}

})

},1000)
</script>

</head>

<body>

<h1>VisionPay AI Vision Dashboard</h1>

<div class="box">
<h2>Live Camera Feed</h2>
<img src="/video" width="640">
</div>

<div id="confirm">✅ PAYMENT CONFIRMED</div>

<div class="box">
<h2>Wallet</h2>
<p>{{wallet}}</p>
</div>

<div class="box">
<h2>Payment Status</h2>
<p id="status">Loading...</p>
</div>

</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML, wallet=account.address)


@app.route("/status")
def get_status():
    global payment_confirmed

    data = {
        "status": status,
        "confirmed": payment_confirmed
    }

    payment_confirmed = False
    return jsonify(data)


def get_eth_price():
    try:
        r = requests.get(
        "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"
        ).json()
        return r["ethereum"]["usd"]
    except:
        return None


def send_eth(receiver,amount):
    global status,payment_confirmed

    status="Preparing transaction..."

    nonce=w3.eth.get_transaction_count(account.address)

    tx={
        "nonce":nonce,
        "to":receiver,
        "value":w3.to_wei(amount,"ether"),
        "gas":21000,
        "gasPrice":w3.to_wei("20","gwei"),
        "chainId":1
    }

    signed=w3.eth.account.sign_transaction(tx,private_key)
    tx_hash=w3.eth.send_raw_transaction(signed.raw_transaction)

    status="Transaction submitted"

    try:
        w3.eth.wait_for_transaction_receipt(tx_hash,timeout=120)
        status="Transaction confirmed"
        payment_confirmed=True
    except:
        status="Transaction pending"


def generate_frames():

    cap = cv2.VideoCapture(0)

    while True:

        success, frame = cap.read()

        if not success:
            continue

        codes = decode(frame)

        for qr in codes:

            x,y,w,h = qr.rect

            cv2.rectangle(frame,(x,y),(x+w,y+h),(0,255,0),4)

            cv2.rectangle(frame,(x,y-30),(x+90,y),(0,255,0),-1)

            cv2.putText(frame,"QR",(x+10,y-8),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,(0,0,0),2)

        ret, buffer = cv2.imencode('.jpg', frame)

        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')


@app.route('/video')
def video():
    return Response(generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame')


def scanner():

    global status,last_data

    cap=cv2.VideoCapture(0)

    while True:

        ret,frame=cap.read()

        codes=decode(frame)

        for qr in codes:

            data=qr.data.decode("utf-8")

            if data!=last_data:

                if data.startswith("ethereum:"):

                    parts=data.replace("ethereum:","").split("?")

                    address=parts[0]
                    amount=float(parts[1].split("=")[1])

                    price=get_eth_price()

                    if price:
                        usd=amount*price
                        status=f"Detected {amount} ETH (${usd:.2f})"
                    else:
                        status=f"Detected {amount} ETH"

                    if amount>0.02:
                        status="Payment blocked: amount too large"
                    else:
                        status="Sending payment..."
                        send_eth(address,amount)

                last_data=data

        time.sleep(0.2)


threading.Thread(target=scanner,daemon=True).start()

app.run(host="0.0.0.0",port=5000)
