import logging
import requests
import xmlrpc.client

from concurrent.futures import ThreadPoolExecutor
from itertools import islice
from lxml import etree
from urllib.parse import quote

# This is a script to manually clean up unused azure blobs.

# +--------+ 3. search_read ir.attachments with cloud urls +---------+
# |        | --------------------------------------------> |         |
# |        | <-------------------------------------------- |  Odoo   |
# |        | 4. used urls                                  |         |
# |        |                                               |         |
# | Script |                                               +---------+
# |        |                                               +---------+
# |        |                            1. list all blobs  |  Cloud  |
# |        | --------------------------------------------> | Storage |
# |        | <-------------------------------------------- |         |
# |        | 2. blobs names                                |         |
# |        |                                               |         |
# |        |                        5. delete unused blobs |         |
# |        | --------------------------------------------> |         |
# |        | <-------------------------------------------- |         |
# +--------+ 6. 202: Accepted                              +---------+
#
#
# 1, 2, 3, 4 are done in batch
# 5, 6 are done with threadpool

# odoo
odoo_url = 'http://localhost:8069'
odoo_db = 'odoo_db'
odoo_username = 'admin'
odoo_password = 'admin'

# Azure
X_MS_VERSION = '2023-11-03'
azure_container_name = 'container_name'
azure_account_name = 'account_name'
azure_tenant_id = 'tenant_id'
azure_client_id = 'client_id'
azure_client_secret = 'client_secret'

# Get Azure OAuth token
azure_token_url = f"https://login.microsoftonline.com/{azure_tenant_id}/oauth2/token"
azure_token_data = {
    'grant_type': 'client_credentials',
    'client_id': azure_client_id,
    'client_secret': azure_client_secret,
    'resource': 'https://storage.azure.com/'
}
azure_token_response = requests.post(azure_token_url, data=azure_token_data, timeout=5)
azure_token = azure_token_response.json()['access_token']

_logger = logging.getLogger()


def list_blob_urls(container_name, batch_size=1000):
    cloud_storage_blobs_num = 0
    url = f"https://{azure_account_name}.blob.core.windows.net/{container_name}?restype=container&comp=list"
    headers = {
        'Authorization': f'Bearer {azure_token}',
        'x-ms-version': X_MS_VERSION,
        'Content-Type': 'application/xml'
    }
    params = {
        'maxresults': batch_size,
    }

    while True:
        response = requests.get(url, headers=headers, params=params, timeout=5)
        response_xml = etree.fromstring(response.content)
        for blob in response_xml.findall('.//Blob'):
            cloud_storage_blobs_num += 1
            yield f"https://{azure_account_name}.blob.core.windows.net/{container_name}/{quote(blob.find('Name').text)}"

        params['marker'] = response_xml.find('NextMarker').text
        if params['marker'] is None:
            break

    logging.info('The cloud storage container has %d blobs', cloud_storage_blobs_num)


def split_every(n, iterable, piece_maker=tuple):
    iterator = iter(iterable)
    piece = piece_maker(islice(iterator, n))
    while piece:
        yield piece
        piece = piece_maker(islice(iterator, n))


def get_blobs_to_be_deleted(blob_urls, batch_size=1000):
    common = xmlrpc.client.ServerProxy(f'{odoo_url}/xmlrpc/2/common')
    uid = common.authenticate(odoo_db, odoo_username, odoo_password, {})
    models = xmlrpc.client.ServerProxy(f'{odoo_url}/xmlrpc/2/object')
    for blob_urls_ in split_every(batch_size, blob_urls):
        blob_urls_ = list(blob_urls_)
        attachments = models.execute_kw(odoo_db, uid, odoo_password, 'ir.attachment', 'search_read', [
            [('type', '=', 'cloud_storage'), ('url', 'in', blob_urls_)],
            ['url']
        ])
        used_urls_ = {attachment['url'] for attachment in attachments}
        for blob_url in blob_urls_:
            if blob_url not in used_urls_:
                yield blob_url


def delete_blobs(blob_urls, max_worker=None):
    headers = {
        'Authorization': f'Bearer {azure_token}',
        'x-ms-version': X_MS_VERSION,
        'Content-Type': 'application/xml'
    }
    deleted_cloud_storage_blobs_num = 0

    def delete_blob_(blob_url):
        nonlocal deleted_cloud_storage_blobs_num
        delete_response = requests.delete(blob_url, headers=headers, timeout=5)
        if delete_response.status_code == 202:
            deleted_cloud_storage_blobs_num += 1
            _logger.info('%s is deleted', blob_url)
        elif delete_response.status_code == 404:
            _logger.debug('%s has already been deleted', blob_url)
        else:
            _logger.warning('%s cannot be deleted:\n%s', blob_url, delete_response.text)

    with ThreadPoolExecutor(max_workers=max_worker) as executor:
        executor.map(delete_blob_, blob_urls)

    logging.info('%d blobs are deleted by the script', deleted_cloud_storage_blobs_num)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    all_blob_urls = list_blob_urls(container_name=azure_container_name, batch_size=1000)
    to_delete_blob_urls = get_blobs_to_be_deleted(all_blob_urls, batch_size=1000)
    delete_blobs(to_delete_blob_urls)
