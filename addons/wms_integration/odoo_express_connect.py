import odoolib
import requests


conn = odoolib.get_connection(
    hostname='localhost',
    database='prod_tes_lavka',
    login='zambas124@gmail.com',
    password='1402',
    protocol='jsonrpc',
    port=8069,
)

def wms_get_products():
    products = []
    url = 'http://lavka-api-proxy.lavka.tst.yandex.net//api/external/products/v1/products'
    headers = {'Authorization': 'Bearer da692f79169ca913c9fa7d9f19a28afe'}
    body = {
        "cursor": "",
        "subscribe": False
    }
    cursor = None
    iteraror = 200
    i = 0
    while True:
        i+=1
        body.update({'cursor': cursor})
        resp = requests.post(url, json=body, headers=headers)
        resp_json = resp.json()
        products_wms = resp_json.get('products')
        products += products_wms
        cursor = resp_json.get('cursor')
        if not products:
            break
        if not cursor:
            break
        if i > iteraror:
            break
    return products


def sync_products(wms_products):
    wms_ids = [i.get('product_id') for i in wms_products]
    wms_products = {i.get('product_id'): i for i in wms_products}
    products = conn.get_model('product.template')
    products_odo = products.search_read(
        [
            ('wms_product_id', 'in', wms_ids)
        ],
        [
            'wms_product_id'
        ]
    )
    products_ids = [i.get('wms_product_id') for i in products_odo]
    for wms_id in wms_ids:
        if wms_id not in products_ids:
            product = wms_products.get(wms_id)
            vals = {
                'name': product.get('title', ''),
                'default_code': product.get('external_id'),
                'wms_product_id': wms_id,
                'type': 'product',
                'description': product.get('description')
            }
            products.create(vals)
            print(f'product: {wms_id} prepere to sync')
    return True


def main():
    wms_products = wms_get_products()
    finish = len(wms_products)
    offset = 0
    limit = 20
    while True:
        if limit >= finish:
            limit = finish
        if offset >= finish:
            break
        to_sync = wms_products[offset:limit]
        sync_products(to_sync)
        offset = limit
        limit += 20

#main()
def get_warehouses_wms():
    products = []
    url = 'https://api.lavka.yandex.net/api/external/stores/v1/list'
    headers = {'Authorization': 'Bearer eyJjb21wYW55X2lkIjogIjJmZGEyMTU3ZTZiYTRlODRiNjVlZmRkOTM2MjZhZGZlMDAwMTAwMDEwMDAxIiwgInNlY3JldCI6ICJlOWY4OWFiNTFiMzAwZDdmZGNiYzBiOWE3NjYyOTNlOCJ9.913e4f1edb3e95153cf0b4005764cca011641b46'}
    body = {
        "cursor": "",
        "subscribe": False
    }
    cursor = None
    iteraror = 200
    while True:
        body.update({'cursor': cursor})
        resp = requests.post(url, json=body, headers=headers)
        resp_json = resp.json()
        products_wms = resp_json.get('stores')
        products += products_wms
        cursor = resp_json.get('cursor')
        if not products:
            break
        if not cursor:
            break
    return products

warehouses = get_warehouses_wms()
a=1


def create_warehousese(warehouses):
    wh = conn.get_model('stock.warehouse')
    for w in warehouses:
        if w.get('status') == 'active':
            code = w.get('slug')
            if code:
                code = code[-5:]
            else:
                break
            try:
                warh = wh.create({
                    'name': w.get('title'),
                    'code': code,
                    'wms_warehouse_id': w.get('store_id')
                })
            except Exception as ex:
                print(f"PASSED: {w.get('store_id')}")

create_warehousese(warehouses)