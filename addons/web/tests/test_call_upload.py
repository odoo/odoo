# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unittest.mock import patch

from odoo import api
from odoo.exceptions import AccessError, RedirectWarning, UserError
from odoo.tests import tagged
from odoo.tests.common import HttpCase, new_test_user
from odoo.tools import mute_logger


@tagged('post_install', '-at_install')
class TestCallUpload(HttpCase):

    def _upload(self, method, login='admin', files=None, model='res.partner', **data):
        self.authenticate(login, login)
        return self.url_open(
            f'/web/dataset/call_upload/{model}/{method}',
            {'csrf_token': self.csrf_token(), **data},
            files=files or [
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

    def test_default_values_of_the_context_do_not_reach_the_attachments(self):
        calls = []

        @api.model
        def upload_test(model, attachment_ids=None):
            calls.append((model.env.context.get('default_res_id'), attachment_ids))

        context = '{"default_res_model": "res.partner", "default_res_id": 42, "default_type": "opportunity"}'
        with patch.object(self.registry['res.partner'], 'upload_test', upload_test, create=True):
            self._upload('upload_test', context=context)
        default_res_id, attachment_ids = calls[0]
        self.assertEqual(default_res_id, 42)
        attachments = self.env['ir.attachment'].browse(attachment_ids)
        self.assertEqual(len(attachments), 2)
        self.assertFalse(any(attachments.mapped('res_model')))
        self.assertFalse(any(attachments.mapped('res_id')))
        self.assertEqual(set(attachments.mapped('type')), {'binary'})

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
            msg = "Nope"
            raise UserError(msg)

        before = self.env['ir.attachment'].search_count([('name', 'in', ['a.txt', 'b.txt'])])
        with patch.object(self.registry['res.partner'], 'upload_test', upload_test, create=True), \
             mute_logger('odoo.http'):
            response = self._upload('upload_test')
        error = response.json()['error']
        self.assertEqual(error['data']['name'], 'odoo.exceptions.UserError')
        self.assertEqual(error['data']['message'], 'Nope')
        self.assertEqual(self.env['ir.attachment'].search_count([('name', 'in', ['a.txt', 'b.txt'])]), before)

    def test_private_method_is_refused(self):
        with mute_logger('odoo.http'):
            response = self._upload('_search')
        self.assertEqual(response.json()['error']['data']['name'], 'odoo.exceptions.AccessError')

    def test_unknown_model_is_refused(self):
        with mute_logger('odoo.http'):
            response = self._upload('upload_test', model='not.a.model')
        self.assertEqual(response.status_code, 404)

    def test_empty_file_is_refused(self):
        calls = []

        @api.model
        def upload_test(model, attachment_ids=None):
            calls.append(attachment_ids)

        with patch.object(self.registry['res.partner'], 'upload_test', upload_test, create=True), \
             mute_logger('odoo.http'):
            response = self._upload('upload_test', files=[('ufile', ('empty.txt', b'', 'text/plain'))])
        self.assertIn('empty.txt', response.json()['error']['data']['message'])
        self.assertFalse(calls)

    def test_method_runs_with_the_rights_of_the_user(self):
        new_test_user(self.env, login='upload_user', password='upload_user', groups='base.group_user')
        calls = []

        @api.model
        def upload_test(model, attachment_ids=None):
            calls.append(model.env.user.login)

        with patch.object(self.registry['res.partner'], 'upload_test', upload_test, create=True):
            response = self._upload('upload_test', login='upload_user')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(calls, ['upload_user'])

    def test_every_error_of_the_method_is_returned(self):
        def raise_error(error):
            @api.model
            def upload_test(model, attachment_ids=None):
                raise error
            return upload_test

        action = {'type': 'ir.actions.act_window_close'}
        for error, name in [
            (RedirectWarning("Configure", action, "Go"), 'odoo.exceptions.RedirectWarning'),
            (AccessError("No access"), 'odoo.exceptions.AccessError'),
            (ValueError("Unreadable file"), 'builtins.ValueError'),
        ]:
            with self.subTest(name=name), \
                 patch.object(self.registry['res.partner'], 'upload_test', raise_error(error), create=True), \
                 mute_logger('odoo.http'):
                response = self._upload('upload_test')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()['error']['data']['name'], name)

    def test_request_larger_than_the_upload_limit_is_refused(self):
        self.env['ir.config_parameter'].set_int('web.max_file_upload_size', 10)
        with mute_logger('odoo.http'):
            response = self._upload('upload_test', files=[('ufile', ('big.txt', b'x' * 100, 'text/plain'))])
        self.assertEqual(response.status_code, 413)

    def test_browse_uploads(self):
        user = new_test_user(self.env, login='uploader', groups='base.group_user')
        Attachment = self.env['ir.attachment'].with_user(user)
        upload = Attachment.create({'name': 'a.pdf', 'raw': b'%PDF-1.4 upload', 'mimetype': 'application/pdf'})
        self.assertEqual(Attachment._browse_uploads(upload.ids), upload)
        self.assertEqual(Attachment._browse_uploads(upload.ids, mimetypes=['application/pdf']), upload)
        with self.assertRaisesRegex(UserError, 'invalid type'):
            Attachment._browse_uploads(upload.ids, mimetypes=['image/'])

        others = self.env['ir.attachment'].create({'name': 'b.txt', 'raw': b'other', 'public': True})
        with self.assertRaises(UserError):
            Attachment._browse_uploads(others.ids)

        upload.write({'res_model': 'res.partner', 'res_id': user.partner_id.id})
        with self.assertRaises(UserError):
            Attachment._browse_uploads(upload.ids)
