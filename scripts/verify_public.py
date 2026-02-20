
# Try to access as public user using curl
import requests
resp = requests.get('http://localhost:8069/')
print(f'Status: {resp.status_code}')
if resp.status_code == 403:
    print('Still 403 Forbidden!')
else:
    print('Access OK')

