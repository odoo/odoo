import urllib.request
import json

auth_data = json.dumps({
    'jsonrpc': '2.0',
    'params': {'db': 'odoo', 'login': 'admin', 'password': 'admin'}
}).encode('utf-8')

req = urllib.request.Request(
    'http://localhost:8070/web/session/authenticate',
    data=auth_data,
    headers={'Content-Type': 'application/json'}
)
resp = urllib.request.urlopen(req)
cookie = resp.headers.get('Set-Cookie')

opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
opener.addheaders = [('Cookie', cookie)]

endpoints = [
    ('/university/marksheet/892/pdf', 'Marksheet PDF'),
    ('/university/marksheet/892/xlsx', 'Marksheet XLSX'),
    ('/university/marksheet/892/download', 'Marksheet PDF Alias'),
    ('/university/marksheet/892/excel', 'Marksheet XLSX Alias'),
    ('/university/document/university.exam/892/download', 'Document Controller Exam PDF'),
    ('/university/document/university.exam/892/download/xlsx', 'Document Controller Exam XLSX'),
    ('/university/document/892/download', 'Document Controller Fallback PDF'),
    ('/university/document/892/download/xlsx', 'Document Controller Fallback XLSX'),
]

for url, label in endpoints:
    full_url = f'http://localhost:8070{url}'
    try:
        r = opener.open(full_url)
        content = r.read()
        print(f"[SUCCESS] {label}: {url} -> status {r.status}, length {len(content):,} bytes, type {r.headers.get('Content-Type')}")
    except Exception as e:
        print(f"[ERROR] {label}: {url} -> {e}")
