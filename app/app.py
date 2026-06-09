import os
import sys
import json
import time
import socket
import threading
from flask import Flask, render_template
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

PROCESS_ID = os.environ.get("PROCESS_ID", "P1")
HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 5000))
WEB_PORT = int(os.environ.get("WEB_PORT", 8080))

MOCK_PEERS = {
    "P1": {"ip": "192.168.1.50", "port": 5001},
    "P2": {"ip": "192.168.1.50", "port": 5002},
    "P3": {"ip": "192.168.1.50", "port": 5003},
    
    "P4": {"ip": "192.168.1.60", "port": 5004},
    "P5": {"ip": "192.168.1.60", "port": 5005},
    "P6": {"ip": "192.168.1.60", "port": 5006},
}

lamport_clock = 0
clock_lock = threading.Lock()
logs = []

def log_and_notify(action, detail):
    global lamport_clock
    log_entry = {
        "clock": lamport_clock,
        "action": action,
        "detail": detail,
        "time": time.strftime("%H:%M:%S")
    }
    logs.append(log_entry)
    socketio.emit('update', {'clock': lamport_clock, 'logs': logs})

def tcp_server():
    global lamport_clock
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(5)
    print(f"[{PROCESS_ID}] Servidor TCP escutando na porta {PORT}...")
    
    while True:
        conn, addr = server.accept()
        data = conn.recv(1024).decode('utf-8')
        if data:
            payload = json.loads(data)
            sender = payload["sender"]
            msg_text = payload["text"]
            received_clock = payload["clock"]
            
            with clock_lock:
                lamport_clock = max(lamport_clock, received_clock) + 1
                log_and_notify("RECEBIDO", f"De {sender}: '{msg_text}' (Relógio recebido: {received_clock})")
        conn.close()

@socketio.on('send_message')
def handle_send_message(data):
    global lamport_clock
    target_id = data['target']
    msg_text = data['text']
    
    if target_id not in MOCK_PEERS or target_id == PROCESS_ID:
        return
    
    with clock_lock:
        lamport_clock += 1
        current_clock = lamport_clock
        log_and_notify("ENVIADO", f"Para {target_id}: '{msg_text}'")

    def send_task():
        try:
            peer = MOCK_PEERS[target_id]
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3.0)
            s.connect((peer["ip"], peer["port"]))
            
            payload = {
                "sender": PROCESS_ID,
                "clock": current_clock,
                "text": msg_text
            }
            s.sendall(json.dumps(payload).encode('utf-8'))
            s.close()
        except Exception as e:
            with clock_lock:
                log_and_notify("ERRO", f"Falha ao enviar para {target_id} ({str(e)})")

    threading.Thread(target=send_task).start()

@app.route('/')
def index():
    destinations = [k for k in MOCK_PEERS.keys() if k != PROCESS_ID]
    return render_template('index.html', pid=PROCESS_ID, clock=lamport_clock, logs=logs, destinations=destinations)

if __name__ == '__main__':
    threading.Thread(target=tcp_server, daemon=True).start()
    socketio.run(app, host='0.0.0.0', port=WEB_PORT, debug=False, allow_unsafe_werkzeug=True)
