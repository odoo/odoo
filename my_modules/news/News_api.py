import requests
import json
import xmlrpc.client

base_url = 'https://newsapi.org/v2/top-headlines?country=in&apiKey=1f5e19ab4afc4eee8adf781473ee4cd7'

r = requests.get(base_url)

val = []
img=[]
desc=[]
urls=[]

rjdata = r.json()
# print(rjdata['totalResults'])
for x in rjdata['articles']:
    val.append(x['title'])
    img.append(x['urlToImage'])
    desc.append(x['description'])
    urls.append(x['url'])

url = 'http://localhost:8088'
db = 'next2'
username = 'admin'
password = 'admin'

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url), allow_none=True)
uid = common.authenticate(db, username, password, {})

if uid:
    print("authenticate successful")
    models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url), allow_none=True)
else:
    print("authenticate failed")

del_id = models.execute_kw(db, uid, password, 'owl.news', 'search', [[]])

print(del_id)
for x in del_id:
    create_id = models.execute_kw(db, uid, password, 'owl.news', 'unlink', [[x]])

for x in range(1,20):
    create_id = models.execute_kw(db, uid, password, 'owl.news', 'create', [{'news': val[x], 'imgsrc': img[x], 'description': desc[x], 'url': urls[x]}])