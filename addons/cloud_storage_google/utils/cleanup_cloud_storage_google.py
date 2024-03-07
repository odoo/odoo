import json
import logging
import requests
import xmlrpc.client

from concurrent.futures import ThreadPoolExecutor
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from itertools import islice
from urllib.parse import quote

# This is a script to manually clean up unused google blobs.

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
# +--------+ 6. 204: No Content                            +---------+
#
#
# 1, 2, 3, 4 are done in batch
# 5, 6 are done with threadpool

# Odoo
odoo_url = 'http://localhost:8069'
odoo_db = 'odoo_db'
odoo_username = 'admin'
odoo_password = 'admin'

# Google service account
GOOGLE_CLOUD_STORAGE_ENDPOINT = 'https://storage.googleapis.com'
google_cloud_bucket_name = 'bucket_name'
google_cloud_account_info = r"""account_info"""
google_cloud_account_info = json.loads(google_cloud_account_info)

# Get Google credentials
credentials = service_account.Credentials.from_service_account_info(google_cloud_account_info).with_scopes(
    ['https://www.googleapis.com/auth/devstorage.full_control'])
credentials.refresh(Request())

_logger = logging.getLogger(__name__)


def list_blob_urls(bucket_name, batch_size=1000):
    cloud_storage_blobs_num = 0
    url = f"https://www.googleapis.com/storage/v1/b/{bucket_name}/o"
    params = {
        'maxResults': batch_size,
        'fields': 'items(name), nextPageToken',
    }
    headers = {
        'Authorization': f"Bearer {credentials.token}"
    }

    while True:
        response = requests.get(url, params=params, headers=headers, timeout=5)
        data = response.json()
        for blob in data.get('items', []):
            cloud_storage_blobs_num += 1
            yield f'{GOOGLE_CLOUD_STORAGE_ENDPOINT}/{bucket_name}/{quote(blob["name"])}'

        params['pageToken'] = data.get('nextPageToken')
        if params['pageToken'] is None:
            break

    _logger.info('The cloud storage container has %d blobs.', cloud_storage_blobs_num)


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


def delete_blobs(blob_urls, max_workers=None):
    headers = {
        'Authorization': f"Bearer {credentials.token}"
    }
    deleted_cloud_storage_blobs_num = 0

    def delete_blob_(blob_url):
        nonlocal deleted_cloud_storage_blobs_num
        delete_response = requests.delete(blob_url, headers=headers, timeout=5)
        if delete_response.status_code == 204:
            deleted_cloud_storage_blobs_num += 1
            _logger.info('%s is deleted', blob_url)
        elif delete_response.status_code == 404:
            _logger.debug('%s has been deleted', blob_url)
        else:
            _logger.warning('%s cannot be deleted:\n%s', blob_url, delete_response.text)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        executor.map(delete_blob_, blob_urls)

    _logger.info(' %d blobs are deleted by the script', deleted_cloud_storage_blobs_num)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    all_blob_urls = list_blob_urls(bucket_name=google_cloud_bucket_name, batch_size=1000)
    to_delete_blob_urls = get_blobs_to_be_deleted(all_blob_urls, batch_size=1000)
    delete_blobs(to_delete_blob_urls)
