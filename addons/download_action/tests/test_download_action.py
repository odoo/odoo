# -*- coding: utf-8 -*-

import time
import base64
import hashlib

from openerp.tests import common
from openerp.addons.download_action import download_file


class TestModel(common.SingleTransactionCase):

    def setUp(self):
        super(TestModel, self).setUp()
        self.model = self.registry('ir.actions.download')

        md5 = hashlib.md5()
        self.f1 = 'test'
        self.f1_data = {'type': 'memory', 'file': self.f1}
        md5.update(self.f1)
        self.f1_hash = md5.hexdigest()
        self.attachment = {
            'name': 'att_1',
            'datas': base64.b64encode(self.f1),
        }

    def tearDown(self):
        super(TestModel, self).tearDown()
        self.model._clean_cache(force=True)

    def test_add_download(self):
        download_id = self.model._add_download(self.uid, self.f1_data.copy())
        self.assertEquals(download_id, self.f1_hash, 'Wrong hash returned')
        self.assertIn(self.f1_hash, self.model._downloads, 'Failed')

    def test_add_download_duplicate(self):
        # Check if duplicate files are set.
        self.model._add_download(self.uid, self.f1_data.copy())
        self.model._add_download(self.uid, self.f1_data.copy())
        self.assertEquals(len(self.model._downloads), 1,
                          'Duplicate file was set')

    def test_add_download_touch(self):
        download_id = self.model._add_download(self.uid, self.f1_data.copy())
        t1 = self.model._downloads[download_id]['time_added']
        time.sleep(1)
        self.model._add_download(self.uid, self.f1_data.copy())
        t2 = self.model._downloads[download_id]['time_added']
        self.assertLess(t1, t2, 'Timestamp not updated')

    def test_from_memory(self):
        self.model._add_download(self.uid, self.f1_data.copy())
        f1, _, _ = self.model._get_download(self.cr, self.uid, self.f1_hash)
        self.assertEquals(f1, self.f1, 'Files do not match')

    def test_from_db(self):
        att = self.registry('ir.attachment')
        values = {
            'type': 'db',
            'model': 'ir.attachment',
            'field': 'datas',
            'id': att.create(self.cr, self.uid, self.attachment),
        }
        download_id = self.model._add_download(self.uid, values)
        f, _, _ = self.model._get_download(self.cr, self.uid, download_id)
        self.assertEquals(f, self.f1, 'Files do not match')

    def test_uid_check(self):
        self.model._clean_cache(force=True)
        other_uid = self.uid + 1
        self.model._add_download(other_uid, self.f1_data.copy())
        f2, _, _ = self.model._get_download(self.cr, self.uid, self.f1_hash)
        self.assertEquals(f2, None, 'File returned with different UID')

    def test_multiple_users_download(self):
        self.model._clean_cache(force=True)
        other_uid = self.uid + 1
        self.model._add_download(self.uid, self.f1_data.copy())
        self.model._add_download(other_uid, self.f1_data.copy())
        f1, _, _ = self.model._get_download(self.cr, self.uid, self.f1_hash)
        f2, _, _ = self.model._get_download(self.cr, other_uid, self.f1_hash)
        self.assertEquals(self.f1, f2)


class TestDecorator(common.SingleTransactionCase):

    def setUp(self):
        super(TestDecorator, self).setUp()

    @download_file
    def _test_action(self, *args, **kwargs):
        return {
            'type': 'ir.actions.download',
            'file': 'test'
        }

    @download_file
    def _test_action2(self, *args, **kwargs):
        return {
            'type': 'ir.actions.report.xml',
        }

    def test_remove_file_from_dict(self):
        result = self._test_action(self.cr, self.uid)
        self.assertNotIn('file', result, 'File was not removed')

    def test_file_is_cached(self):
        model = self.registry('ir.actions.download')
        result = self._test_action(self.cr, self.uid)
        download_id = result.get('download_id')
        self.assertIn(download_id, model._downloads, 'File not in cache.')

    def test_decorator_return_other_action(self):
        result = self._test_action2(self.cr, self.uid)
        self.assertEquals(result['type'], 'ir.actions.report.xml',
                          'Action type changed')
