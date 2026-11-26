# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile


def manifest_content(manifest={}, /, **values):
    return json.dumps({
        'author': 'Odoo S.A.',
        'license': 'LGPL-3',
        **manifest,
        **values,
    }).encode()


def archive(files):
    buffer = BytesIO()
    with ZipFile(buffer, 'w', compression=ZIP_DEFLATED) as zipf:
        for path, data in files:
            zipf.writestr(path, data)
    return buffer
