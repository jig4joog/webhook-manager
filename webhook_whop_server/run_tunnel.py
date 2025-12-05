# run_tunnel.py
from pyngrok import ngrok
import time

# --- CONFIGURATION ---
PORT = 8000
# Paste your token inside the quotes below
AUTH_TOKEN = "36P6oAgVWxd6GyKGj9Hu6iZtu2U_4jYiuCDZY2jR1We3CFL8v" 
# ---------------------

def start_ngrok():
    # 1. Set the token
    ngrok.set_auth_token(AUTH_TOKEN)

    # 2. Open the tunnel to port 8000
    try:
        public_url = ngrok.connect(PORT).public_url
        print("\n" + "="*50)
        print(f"STATUS: Tunnel is ON")
        print(f"COPY THIS URL FOR WHOP: {public_url}/webhook")
        print("="*50 + "\n")
        
        # Keep the script running
        while True:
            time.sleep(1)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    start_ngrok()

# https://inspective-unnauseating-cyril.ngrok-free.dev/webhook