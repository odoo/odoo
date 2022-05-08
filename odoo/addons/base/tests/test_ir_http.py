# -*- coding: utf-8 -*-

from odoo.tests import common
import odoo

GIF = b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs="


class test_ir_http_mimetype(common.TransactionCase):

    def test_ir_http_mimetype_attachment(self):
        """ Test mimetype for attachment """
        attachment = self.env['ir.attachment'].create({
            'datas': GIF,
            'name': 'file.gif'})

        status, headers, content = self.env['ir.http'].binary_content(
            id=attachment.id,
            mimetype=None,
            default_mimetype='application/octet-stream',
        )
        mimetype = dict(headers).get('Content-Type')
        self.assertEqual(mimetype, 'image/gif')

    def test_ir_http_mimetype_attachment_name(self):
        """ Test mimetype for attachment with bad name"""
        attachment = self.env['ir.attachment'].create({
            'datas': GIF,
            'name': 'file.png'})

        status, headers, content = self.env['ir.http'].binary_content(
            id=attachment.id,
            mimetype=None,
            default_mimetype='application/octet-stream',
        )
        mimetype = dict(headers).get('Content-Type')
        # TODO: fix and change it in master, should be image/gif
        self.assertEqual(mimetype, 'image/png')

    def test_ir_http_mimetype_basic_field(self):
        """ Test mimetype for classic field """
        partner = self.env['res.partner'].create({
            'image_1920': GIF,
            'name': 'Test mimetype basic field',
        })

        status, headers, content = self.env['ir.http'].binary_content(
            model='res.partner',
            id=partner.id,
            field='image_1920',
            default_mimetype='application/octet-stream',
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

        resized = odoo.tools.image_process(prop.value_binary, size=(64, 64))
        # Simul computed field which resize and that is not attachement=True (E.G. on product)
        prop.write({'value_binary': resized})
        status, headers, content = self.env['ir.http'].binary_content(
            model='ir.property',
            id=prop.id,
            field='value_binary',
            default_mimetype='application/octet-stream',
        )
        mimetype = dict(headers).get('Content-Type')
        self.assertEqual(mimetype, 'image/gif')

    def test_ir_http_attachment_access(self):
        """ Test attachment access with and without access token """
        public_user = self.env.ref('base.public_user')
        attachment = self.env['ir.attachment'].create({
            'datas': GIF,
            'name': 'image.gif'
        })

        defaults = {
            'id': attachment.id,
            'default_mimetype': 'image/gif',
        }

        def test_access(**kwargs):
            # DLE P69: `test_ir_http_attachment_access`
            # `binary_content` relies on the `__last_update` to determine if a user has the read access to an attachment.
            # as the attachment has just been created above as sudo, the data is in cache and if we don't remove it the below
            # `test_access` wont have to fetch it and therefore wont raise the accesserror as its already in the cache
            # `__last_update` must be removed from the cache when `test_access` is called, which happens and recompute the todos
            attachment.flush()
            attachment.invalidate_cache()
            status, _, _ = self.env['ir.http'].with_user(public_user).binary_content(
                **dict(defaults, **kwargs)
            )
            return status

        status = test_access()
        self.assertEqual(status, 403, "no access")

        status = test_access(access_token=u'Secret')
        self.assertEqual(status, 403,
            "no access if access token for attachment without access token")

        attachment.access_token = u'Secret'
        status = test_access(access_token=u'Secret')
        self.assertEqual(status, 200, "access for correct access token")

        status = test_access(access_token=u'Wrong')
        self.assertEqual(status, 403, "no access for wrong access token")

        attachment.public = True
        status = test_access()
        self.assertEqual(status, 200, "access for attachment with access")

        status = test_access(access_token=u'Wrong')
        self.assertEqual(status, 403,
            "no access for wrong access token for attachment with access")

        attachment.unlink()
        status = test_access()
        self.assertEqual(status, 404, "no access for deleted attachment")

        status = test_access(access_token=u'Secret')
        self.assertEqual(status, 404,
            "no access with access token for deleted attachment")

    def test_ir_http_default_filename_extension(self):
        """ Test attachment extension when the record has a dot in its name """
        self.env.user.name = "Mr. John"
        self.env.user.image_128 = GIF
        _, _, filename, _, _ = self.env['ir.http']._binary_record_content(
            self.env.user, 'image_128',
        )
        self.assertEqual(filename, "Mr. John.gif")

        # For attachment, the name is considered to have the extension in the name
        # and thus the extension should not be added again.
        attachment = self.env['ir.attachment'].create({
            'datas': GIF,
            'name': 'image.gif'
        })
        _, _, filename, _, _ = self.env['ir.http']._binary_record_content(
            attachment,
        )
        self.assertEqual(filename, 'image.gif')
