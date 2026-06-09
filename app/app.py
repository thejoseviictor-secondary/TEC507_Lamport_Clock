import os
import json
import time
import socket
import threading
from flask import Flask, render_template, request, Response

app = Flask(__name__)

PORT = int(os.environ.get("PORT"))
PROCESS_ID = os.environ.get("PROCESS_ID")
WEB_PORT = int(os.environ.get("WEB_PORT"))

COMPUTER_ONE_HOST = os.environ.get("COMPUTER_ONE_HOST")
COMPUTER_TWO_HOST = os.environ.get("COMPUTER_TWO_HOST")

MOCK_PEERS = {
    "P1": {"ip": COMPUTER_ONE_HOST, "port": 5001},
    "P2": {"ip": COMPUTER_ONE_HOST, "port": 5002},
    "P3": {"ip": COMPUTER_ONE_HOST, "port": 5003},
    
    "P4": {"ip": COMPUTER_TWO_HOST, "port": 5004},
    "P5": {"ip": COMPUTER_TWO_HOST, "port": 5005},
    "P6": {"ip": COMPUTER_TWO_HOST, "port": 5006},
}

lamport_clock = 0
clock_lock = threading.Lock()
logs = []
listeners = []

def notify_browsers():
    global lamport_clock, logs
    data = json.dumps({"clock": lamport_clock, "logs": logs})
    for listener in listeners:
        listener.put(data)

def tcp_server():
    global lamport_clock
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", PORT))
    server.listen(5)
    
    while True:
        conn, addr = server.accept()
        data = conn.recv(1024).decode('utf-8')
        if data:
            payload = json.loads(data)
            with clock_lock:
                lamport_clock = max(lamport_clock, payload["clock"]) + 1
                logs.append({
                    "time": time.strftime("%H:%M:%S"),
                    "clock": lamport_clock,
                    "action": "RECEBIDO",
                    "detail": f"De {payload['sender']}: '{payload['text']}'"
                })
                notify_browsers()
        conn.close()

@app.route('/')
def index():
    destinations = [k for k in MOCK_PEERS.keys() if k != PROCESS_ID]
    return render_template('index.html', pid=PROCESS_ID, destinations=destinations)

@app.route('/send', methods=['POST'])
def send_message():
    global lamport_clock
    req = request.json
    target_id = req['target']
    msg_text = req['text']
    
    with clock_lock:
        lamport_clock += 1
        current_clock = lamport_clock
        logs.append({
            "time": time.strftime("%H:%M:%S"),
            "clock": current_clock,
            "action": "ENVIADO",
            "detail": f"Para {target_id}: '{msg_text}'"
        })
        notify_browsers()

    def send_task():
        try:
            peer = MOCK_PEERS[target_id]
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2.0)
            s.connect((peer["ip"], peer["port"]))
            s.sendall(json.dumps({"sender": PROCESS_ID, "clock": current_clock, "text": msg_text}).encode('utf-8'))
            s.close()
        except Exception as e:
            with clock_lock:
                logs.append({"time": time.strftime("%H:%M:%S"), "clock": lamport_clock, "action": "ERRO", "detail": f"Falha ao enviar para {target_id}"})
                notify_browsers()

    threading.Thread(target=send_task).start()
    return {"status": "ok"}

import queue
@app.route('/stream')
def stream():
    q = queue.Queue()
    listeners.append(q)
    def event_stream():
        yield f"data: {json.dumps({'clock': lamport_clock, 'logs': logs})}\n\n"
        while True:
            data = q.get()
            yield f"data: {data}\n\n"
    return Response(event_stream(), mimetype="text/event-stream")

if __name__ == '__main__':
    threading.Thread(target=tcp_server, daemon=True).start()
    app.run(host='0.0.0.0', port=WEB_PORT, debug=False)
