import hashlib

from odoo import http
from odoo.http import request
from odoo.tools import file_open


SCALE_FILES = [
    'l10n_eu_iot_scale_cert/controllers/checksum.py',
    'l10n_eu_iot_scale_cert/static/src/pos_overrides/components/scale_screen/certified_scale_service.js',
    'l10n_eu_iot_scale_cert/static/src/pos_overrides/components/scale_screen/certified_scale_screen.js',
    'l10n_eu_iot_scale_cert/static/src/pos_overrides/components/scale_screen/certified_scale_screen.xml',
    'l10n_eu_iot_scale_cert/static/src/pos_overrides/components/order_receipt/certified_order_receipt.xml',
    'l10n_eu_iot_scale_cert/static/src/pos_overrides/components/orderline/certified_orderline.xml',
    'l10n_eu_iot_scale_cert/static/src/pos_overrides/components/product_screen/certified_product_screen.js',
    'hw_drivers/iot_handlers/drivers/SerialScaleDriver.py',
]


def calculate_scale_checksum():
    files_data = []
    main_hash = hashlib.sha256()
    for path in sorted(SCALE_FILES):
        with file_open(path, 'rb') as file:
            content = file.read()
        content_hash = hashlib.sha256(content).hexdigest()
        files_data.append({
            'name': path,
            'size_in_bytes': len(content),
            'contents': content.decode(),
            'hash': content_hash
        })
        main_hash.update(content_hash.encode())

    return main_hash.hexdigest(), files_data


class ChecksumController(http.Controller):
    @http.route('/scale_checksum', auth='user')
    def handler(self):
        main_hash, files_data = calculate_scale_checksum()

        # TODO master: change this to use a view like pos_blackbox_be
        file_hashes = '\n'.join([f"{file['name']}: {file['hash']} (size in bytes: {file['size_in_bytes']})" for file in files_data])
        file_contents = '\n'.join([
f"""--------------------------------------------------------------------
{file['name']}
--------------------------------------------------------------------
{file['contents']}"""
            for file in files_data
        ])

        response_text = f"""
SIGNATURES:
--------------------------------------------------------------------
GLOBAL HASH: {main_hash}
{file_hashes}
--------------------------------------------------------------------

CONTENT:
{file_contents}"""

        headers = [
            ('Content-Length', len(response_text)),
            ('Content-Type', 'text/plain'),
        ]
        return request.make_response(response_text, headers)
