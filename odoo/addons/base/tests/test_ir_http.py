# -*- coding: utf-8 -*-

from odoo.tests import common
import odoo

GIF = "R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs="


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
