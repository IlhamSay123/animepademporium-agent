import requests

resp = requests.post(
    "http://localhost:8000/chat",
    json={"message": "do you have any berserk mousepads"},
)
print(resp.status_code)
print(resp.text)