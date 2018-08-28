# -*- coding: utf-8 -*-

from odoo.tests import common
import odoo
import uuid

GIF = b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs="
ACCESS_TOKEN = str(uuid.uuid4())


class test_ir_http_mimetype(common.TransactionCase):

    def test_ir_http_mimetype_attachment(self):
        """ Test mimetype for attachment """
        attachment = self.env['ir.attachment'].create({
            'datas': GIF,
            'name': 'Test mimetype gif',
            'datas_fname': 'file.gif'})

        status, headers, content = self.env['ir.http'].binary_content(
            id=attachment.id,
            mimetype=None,
            default_mimetype='application/octet-stream',
            env=self.env
        )
        mimetype = dict(headers).get('Content-Type')
        self.assertEqual(mimetype, 'image/gif')

    def test_ir_http_mimetype_attachment_name(self):
        """ Test mimetype for attachment with bad name"""
        attachment = self.env['ir.attachment'].create({
            'datas': GIF,
            'name': 'Test mimetype gif with png name',
            'datas_fname': 'file.png'})

        status, headers, content = self.env['ir.http'].binary_content(
            id=attachment.id,
            mimetype=None,
            default_mimetype='application/octet-stream',
            env=self.env
        )
        mimetype = dict(headers).get('Content-Type')
        # TODO: fix and change it in master, should be image/gif
        self.assertEqual(mimetype, 'image/png')

    def test_ir_http_mimetype_basic_field(self):
        """ Test mimetype for classic field """
        partner = self.env['res.partner'].create({
            'image': GIF,
            'name': 'Test mimetype basic field',
        })

        status, headers, content = self.env['ir.http'].binary_content(
            model='res.partner',
            id=partner.id,
            field='image',
            default_mimetype='application/octet-stream',
            env=self.env
        )
        mimetype = dict(headers).get('Content-Type')
        self.assertEqual(mimetype, 'image/gif')

    def test_ir_http_mimetype_computed_field(self):
        """ Test mimetype for computed field wich resize picture"""
        prop = self.env['ir.property'].create({
            'fields_id': self.env['ir.model.fields'].search([], limit=1).id,
            'name': "Property binary",
            'value_binary': GIF,
            'type': 'binary',
        })

        resized = odoo.tools.image_get_resized_images(prop.value_binary, return_big=True, avoid_resize_medium=True)['image_small']
        # Simul computed field which resize and that is not attachement=True (E.G. on product)
        prop.write({'value_binary': resized})
        status, headers, content = self.env['ir.http'].binary_content(
            model='ir.property',
            id=prop.id,
            field='value_binary',
            default_mimetype='application/octet-stream',
            env=self.env
        )
        mimetype = dict(headers).get('Content-Type')
        self.assertEqual(mimetype, 'image/gif')

    def test_ir_http_attachment_valid_access_token(self):
        """ Test valid access token for an image """
        attachment = self.env['ir.attachment'].create({
            'datas': GIF,
            'access_token': ACCESS_TOKEN,
            'name': 'Test valid access token with image',
            'datas_fname': 'image.gif'})

        status, headers, content = self.env['ir.http'].binary_content(
            id=attachment.id,
            default_mimetype='image/gif',
            access_token=ACCESS_TOKEN,
            env=self.env
        )
        self.assertEqual(status, 200)

    def test_ir_http_attachment_wrong_access_token(self):
        """ Test wrong access token for an image """
        attachment = self.env['ir.attachment'].create({
            'datas': GIF,
            'access_token': ACCESS_TOKEN,
            'name': 'Test wrong access token with image',
            'datas_fname': 'image.gif'})

        status, headers, content = self.env['ir.http'].binary_content(
            id=attachment.id,
            default_mimetype='image/gif',
            access_token='False',
            env=self.env
        )
        self.assertEqual(status, 403)

    def test_ir_http_attachment_wrong_access_token_none_saved(self):
        """ Test undefined access token for an image without access token"""
        attachment = self.env['ir.attachment'].create({
            'datas': GIF,
            'name': 'Test undefined access token with image',
            'datas_fname': 'image.gif'})

        status, headers, content = self.env['ir.http'].binary_content(
            id=attachment.id,
            default_mimetype='image/gif',
            access_token='False',
            env=self.env
        )
        self.assertEqual(status, 403)

    def test_ir_http_attachment_wrong_access_token_none_saved_public(self):
        """ Test undefined access token for an image without access token, but public"""
        attachment = self.env['ir.attachment'].create({
            'datas': GIF,
            'public': True,
            'name': 'Test undefined access token with public image',
            'datas_fname': 'image.gif'})

        status, headers, content = self.env['ir.http'].binary_content(
            id=attachment.id,
            default_mimetype='image/gif',
            access_token='False',
            env=self.env
        )
        self.assertEqual(status, 200)

    def test_ir_http_attachment_wrong_access_token_none_saved_model_sudo_read(self):
        """ Test undefined access token for an image without access token, 
            but associated to a model the user is allowed to read"""
        attachment = self.env['ir.attachment'].create({
            'datas': GIF,
            'res_model': 'ir.module.module',
            'res_id': 1,
            'name': 'Test undefined access token with image of a model user can read',
            'datas_fname': 'image.gif'})

        status, headers, content = self.env['ir.http'].sudo().binary_content(
            id=attachment.id,
            default_mimetype='image/gif',
            access_token='False',
            env=self.env
        )
        self.assertEqual(status, 200)

    def test_ir_http_attachment_wrong_access_token_none_saved_model_read(self):
        """ Test undefined access token for an image without access token, 
            but associated to a model we are not allowed to read"""
        public_user = self.env.ref('base.public_user')
        attachment = self.env['ir.attachment'].create({
            'datas': GIF,
            'res_model': 'ir.module.module',
            'res_id': 1,
            'name': 'Test undefined access token with image of a model user cannot read',
            'datas_fname': 'image.gif'})

        http_sudo = self.env['ir.http'].sudo(user=public_user.id)
        status, headers, content = http_sudo.binary_content(
            id=attachment.id,
            default_mimetype='image/gif',
            access_token='False',
            env=http_sudo.env
        )
        self.assertEqual(status, 403)
