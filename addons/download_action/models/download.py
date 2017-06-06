# -*- coding: utf-8 -*-

import base64
import hashlib
import logging
import time

import openerp
from openerp import models

_logger = logging.getLogger(__name__)

# Duration (in seconds) for which the file will be kept in cache and not
# cleaned by the Cron job.
FILE_TIMEOUT = 600


class ir_actions_download(models.AbstractModel):

    _register = True
    _name = 'ir.actions.download'

    _downloads = {}

    def _add_download(self, uid, data):

        md5 = hashlib.md5()
        if 'file' in data:
            md5.update(data['file'])
            download_id = md5.hexdigest()
            if download_id not in self._downloads:
                _logger.debug('Setting file with ID: %s' % download_id)
                self._downloads[download_id] = {
                    'type': 'memory',
                    'data': {
                        'file': data.pop('file'),
                    }
                }
        elif 'model' in data and 'field' in data and 'id' in data:
            md5.update('{model:}:{field:}:{id:}'.format(**data))
            download_id = md5.hexdigest()
            self._downloads[download_id] = {
                'type': 'db',
                'data': {
                    'model': data['model'],
                    'field': data['field'],
                    'id': data['id'],
                },
            }
        else:
            raise ValueError('Fields not set')

        # Set or update the timestamp.
        self._downloads[download_id].update({
            'filename': data.get('filename'),
            'mimetype': data.get('mimetype'),
            'time_added': int(time.time()),
        })
        # Store the uid of the user, who generated the file.
        # It is used later to check if the same user is downloading the file.
        self._downloads[download_id].setdefault('uids', set()).add(uid)
        return download_id

    def _get_download(self, cr, uid, download_id, context=None):
        download = self._downloads.get(download_id)
        uids = download.get('uids', [])

        if not download or uid not in uids:
            return None, None, None

        file_content = None
        filename = download.get('filename')
        mimetype = download.get('mimetype')

        if download['type'] == 'memory':
            file_content = self.from_memory(cr, uid, download_id)
        elif download['type'] == 'db':
            file_content = self.from_db(cr, uid, download_id)
        if len(uids) == 1:
            del self._downloads[download_id]
        return file_content, filename, mimetype

    def from_memory(self, cr, uid, download_id):
        _logger.debug('Requesting file: %s' % download_id)
        return self._downloads[download_id]['data']['file']

    def from_db(self, cr, uid, download_id):
        data = self._downloads[download_id]['data']
        model, field, id = data['model'], data['field'], data['id']
        pool = openerp.registry(cr.dbname)
        model = pool[model]
        rec_id = model.search(cr, uid, [('id', '=', id)], context={})

        if rec_id:
            values = model.read(cr, uid, rec_id[0], [field], context={})
            if values:
                return base64.b64decode(values[0][field])

    def _clean_cache(self, force=False, *args, **kwargs):
        """Clean unclaimed files from cache."""
        _logger.debug('Cleaning download cache...')
        now = int(time.time())
        for file_id in list(self._downloads.keys()):
            time_added = self._downloads[file_id]['time_added']
            if force or now - time_added > FILE_TIMEOUT:
                _logger.debug('Dropping file with ID: %s' % file_id)
                self._downloads.pop(file_id, None)
