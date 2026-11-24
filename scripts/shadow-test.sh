#!/bin/bash
set -e

kubectl -n aceest exec -i deployment/aceest-shadow -- python - <<'PY'
import urllib.request

production_url = "http://aceest-service:5000/health"
shadow_url = "http://aceest-shadow-service:5000/health"

def send_request(url):
    with urllib.request.urlopen(url, timeout=5) as response:
        return response.status, response.read().decode()

production_status, production_body = send_request(production_url)
shadow_status, shadow_body = send_request(shadow_url)

print("PRODUCTION RESPONSE")
print("HTTP:", production_status)
print("Body:", production_body)

print("\nSHADOW RESPONSE")
print("HTTP:", shadow_status)
print("Body:", shadow_body)

print("\nUSER-FACING RESPONSE: PRODUCTION ONLY")
print(production_body)
PY
