import requests
from datetime import datetime
from db import SessionLocal, engine
from models import GroupService

TIMEOUT = 5

def check_all_webhooks():
    session = SessionLocal()
    # print(f"Connecting to Database URL: {engine.url}")
    try:
        links = session.query(GroupService).filter(GroupService.webhook_url != None, GroupService.enabled == True).all()
        for gs in links:
            url = gs.webhook_url
            if gs.enabled:
                try:
                    # Discord treats simple POSTs; a HEAD/GET will still give a useful status
                    resp = requests.get(url, timeout=TIMEOUT)

                    gs.health_code = resp.status_code
                    if 200 <= resp.status_code < 300:

                        gs.health_status = "ok"
                    elif resp.status_code == 404 or resp.status_code == 401:
                        gs.health_status = "missing"   # likely deleted or invalid
                    else:
                        gs.health_status = "error"

                    # print(url, gs.health_status)
                except Exception:
                    gs.health_status = "error"
                    gs.health_code = None
                gs.health_checked_at = datetime.utcnow()
        session.commit()
    finally:
        session.close()

if __name__ == "__main__":
    check_all_webhooks()
