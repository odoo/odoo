# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unittest.mock import patch

from odoo import api
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import HttpCase
from odoo.tools import mute_logger


@tagged('post_install', '-at_install')
class TestCallUpload(HttpCase):

    def _upload(self, method, **data):
        self.authenticate('admin', 'admin')
        return self.url_open(
            '/web/dataset/call_upload',
            {'csrf_token': self.csrf_token(), 'model': 'res.partner', 'method': method, **data},
            files=[
                ('ufile', ('a.txt', b'first', 'text/plain')),
                ('ufile', ('b.txt', b'second', 'text/plain')),
            ],
        )

    def test_method_gets_the_attachments(self):
        calls = []

        @api.model
        def upload_test(model, attachment_ids=None):
            calls.append((model.env.context.get('foo'), attachment_ids))
            return {'type': 'ir.actions.act_window_close'}

        with patch.object(self.registry['res.partner'], 'upload_test', upload_test, create=True):
            response = self._upload('upload_test', context='{"foo": "bar"}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['result']['type'], 'ir.actions.act_window_close')
        self.assertEqual(len(calls), 1)
        foo, attachment_ids = calls[0]
        self.assertEqual(foo, 'bar')
        attachments = self.env['ir.attachment'].browse(attachment_ids)
        self.assertEqual(attachments.mapped('name'), ['a.txt', 'b.txt'])
        self.assertEqual(attachments.mapped('file_size'), [5, 6])
        self.assertFalse(any(attachments.mapped('res_model')))

    def test_method_called_on_the_records(self):
        partner = self.env['res.partner'].create({'name': 'Upload target'})
        calls = []

        def upload_test(records, attachment_ids=None):
            calls.append((records, attachment_ids))

        with patch.object(self.registry['res.partner'], 'upload_test', upload_test, create=True):
            response = self._upload('upload_test', res_ids=f'[{partner.id}]')
        self.assertEqual(response.json(), {'result': False})
        self.assertEqual(calls[0][0].ids, [partner.id])

    def test_method_called_on_no_record(self):
        calls = []

        def upload_test(records, attachment_ids=None):
            calls.append(records)

        with patch.object(self.registry['res.partner'], 'upload_test', upload_test, create=True):
            self._upload('upload_test')
        self.assertEqual(calls[0]._name, 'res.partner')
        self.assertFalse(calls[0])

    def test_user_error_is_returned_and_attachments_dropped(self):
        @api.model
        def upload_test(model, attachment_ids=None):
            raise UserError("Nope")

        before = self.env['ir.attachment'].search_count([('name', 'in', ['a.txt', 'b.txt'])])
        with patch.object(self.registry['res.partner'], 'upload_test', upload_test, create=True):
            response = self._upload('upload_test')
        self.assertEqual(response.json(), {'error': {'message': 'Nope'}})
        self.assertEqual(self.env['ir.attachment'].search_count([('name', 'in', ['a.txt', 'b.txt'])]), before)

    def test_private_method_is_refused(self):
        with mute_logger('odoo.http'):
            response = self._upload('_search')
        self.assertEqual(response.status_code, 403)
