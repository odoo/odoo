import urllib.request, json

req = urllib.request.Request('http://localhost:8070/web/session/authenticate', data=json.dumps({
    'jsonrpc': '2.0',
    'params': {'db': 'odoo', 'login': 'student', 'password': '1234'}
}).encode(), headers={'Content-Type': 'application/json'})

resp = urllib.request.urlopen(req)
cookie = resp.headers.get('Set-Cookie')

req2 = urllib.request.Request('http://localhost:8070/web/webclient/load_menus/1', data=json.dumps({
    'jsonrpc': '2.0', 'params': {}
}).encode(), headers={'Content-Type': 'application/json', 'Cookie': cookie})
res2 = json.loads(urllib.request.urlopen(req2).read().decode())['result']

print('Student Visible Root Menus:')
for child_id in res2['root']['children']:
    m = res2[str(child_id)]
    print(f"- {m['name']} (id={m['id']}, appID={m.get('appID')}, actionID={m.get('actionID')})")
    for sub_id in m.get('children', []):
        sub = res2[str(sub_id)]
        print(f"   * {sub['name']} (id={sub['id']}, actionID={sub.get('actionID')})")
        for subsub_id in sub.get('children', []):
            subsub = res2[str(subsub_id)]
            print(f"      > {subsub['name']} (id={subsub['id']}, actionID={subsub.get('actionID')})")
