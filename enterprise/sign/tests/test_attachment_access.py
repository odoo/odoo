# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import io

from odoo.exceptions import AccessError
from odoo.tests import Form, TransactionCase, users
from odoo.tools.pdf import PdfFileWriter
from odoo.tools import mute_logger


class testAttachmentAccess(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.env['res.users'].create({
            'name': "foo",
            'login': "foo",
            'email': "foo@bar.com",
            'groups_id': [(6, 0, [cls.env.ref('sign.group_sign_user').id])]
        })
        with io.BytesIO() as stream:
            PdfFileWriter().write(stream)
            stream.seek(0)
            cls.pdf = base64.b64encode(stream.read())

    def test_user_template_attachment_without_res_fields(self):
        """Test an employee can create a template linked to an attachment without res_model/res_id"""
        env_user = self.env(user=self.user)
        # As user, create an attachment without res_model/res_id
        attachment = env_user['ir.attachment'].create({'name': 'foo', 'datas': self.pdf})
        # As user, create a sign.template linked to that attachment
        template = env_user['sign.template'].create({'attachment_id': attachment.id})
        # As user, ensure the content of the attachment can be read through the template
        self.assertEqual(template.datas, self.pdf)
        # As user, create another attachment without res_model/res_id
        attachment_2 = env_user['ir.attachment'].create({'name': 'foo', 'datas': self.pdf})
        # As user, change the attachment of the template to this second attachment
        template.write({'attachment_id': attachment_2.id})
        # As user, ensure the content of this second attachment can be read through the template
        self.assertEqual(template.datas, self.pdf)

    def test_user_template_attachment_without_res_fields_created_by_admin(self):
        """Test an employee can read the content of the template's attachment created by another user, the admin,
        and the attachment does not have a res_model/res_id
        """
        # As admin, create an attachment without res_model/res_id
        attachment = self.env['ir.attachment'].create({'name': 'foo', 'datas': self.pdf})
        # As admin, create a sign.template linked to that attachment
        template = self.env['sign.template'].create({'attachment_id': attachment.id})

        # As user, ensure the attachment itself cannot be read
        self.env.invalidate_all()
        with self.assertRaises(AccessError):
            attachment.with_user(self.user).datas
        # But, as user, the content of the attachment can be read through the template
        self.assertEqual(template.with_user(self.user).datas, self.pdf)

        # As admin, create a second attachment without res_model/res_id
        attachment = self.env['ir.attachment'].create({'name': 'bar', 'datas': self.pdf})
        # As admin, link this second attachment to the previously created template (write instead of create)
        template.write({'attachment_id': attachment.id})

        # As user ensure the attachment itself cannot be read
        self.env.invalidate_all()
        with self.assertRaises(AccessError):
            self.assertEqual(attachment.with_user(self.user).datas, self.pdf)
        # But, as user, the content of the attachment can be read through the template
        self.assertEqual(template.with_user(self.user).datas, self.pdf)

    def test_user_read_unallowed_attachment(self):
        """Test a user cannot access an attachment he is not supposed to through a sign template"""
        # As admin, create an attachment for which you require the settings group to access
        autovacuum_job = self.env.ref('base.autovacuum_job')
        attachment_forbidden = self.env['ir.attachment'].create({
            'name': 'foo', 'datas': self.pdf,
            'res_model': autovacuum_job._name, 'res_id': autovacuum_job.id,
        })
        # As user, make sure this is indeed not possible to access that attachment data directly
        self.env.invalidate_all()
        with self.assertRaises(AccessError):
            attachment_forbidden.with_user(self.user).datas
        # As user, create a template pointing to that attachment
        # and make sure it raises an access error
        with self.assertRaises(AccessError):
            template = self.env['sign.template'].with_user(self.user).create({
                'attachment_id': attachment_forbidden.id,
            })
            template.datas

        # As user, update the attachment of an existing template to the unallowed attachment
        # and make sure it raises an access error
        attachment_tmp = self.env['ir.attachment'].with_user(self.user).create({
            'name': 'bar', 'datas': self.pdf,
        })
        template = self.env['sign.template'].with_user(self.user).create({
            'attachment_id': attachment_tmp.id,
        })
        with self.assertRaises(AccessError):
            template.write({'attachment_id': attachment_forbidden.id})
            template.datas

    def test_user_template_duplicate_created_by_admin(self):
        """Test an employee can read the content of a duplicated template created by another user, the admin"""

        # As admin, create an attachment without res_model/res_id
        attachment = self.env['ir.attachment'].create({'name': 'foo', 'datas': self.pdf})
        # As admin, create a sign.template linked to that attachment
        template = self.env['sign.template'].create({'attachment_id': attachment.id})

        # As user, ensure the attachment itself cannot be read
        self.env.invalidate_all()
        with self.assertRaises(AccessError):
            attachment.with_user(self.user).datas
        # But, as user, the content of the attachment can be read through the template
        self.assertEqual(template.with_user(self.user).datas, self.pdf)

        # Duplicate template
        template_dup = self.env['sign.duplicate.template.pdf'].create({
            'original_template_id': template.id,
            'new_pdf': self.pdf,
            'new_template': 'dup template',
        })

        # Current user is not part of authorized users -> duplicate should fail
        with self.assertRaises(AccessError):
            template_dup.with_user(self.user).duplicate_template_with_pdf()

        # Add user to authorized users
        template.write({'authorized_ids': [(4, self.user.id)]})
        template_dup.with_user(self.user).duplicate_template_with_pdf()

        # Modify access rules as admin
        new_template = self.env['sign.template'].search([('name', '=', 'dup template')])
        new_template.write({
            'group_ids': [(6, 0, [self.env.ref('sign.group_sign_user').id])],
        })

        # As user, ensure duplicated template is visible
        new_template = self.env['sign.template'].with_user(self.user).search([('name', '=', 'dup template')])
        self.assertEqual(len(new_template.ids), 1)

        # As user, ensure that both the attachment and the template can be read
        self.env.invalidate_all()
        new_template.attachment_id.with_user(self.user).datas
        self.assertEqual(new_template.with_user(self.user).datas, self.pdf)

    @users('foo')
    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.addons.base.models.ir_rule', 'odoo.models')
    def test_access_sign_user_fields(self):
        """Test an employee can read and write his own signature / initials but not others"""
        # This test doesn't make sense if the record read/updated are sudo,
        # it needs to be tested with the employee access rights
        admin = self.env.ref('base.user_admin')
        self.assertTrue(
            admin.env.user == self.user and not admin.env.su,
            'This test makes sense only if it is tested with employee access rights'
        )
        my_user = self.env['res.users'].browse(self.env.user.id)
        self.assertTrue(
            my_user.env.user == self.user and not my_user.env.su,
            'This test makes sense only if it is tested with employee access rights'
        )

        sign_user_fields = ['sign_signature', 'sign_initials']

        # Set a signature / initials for the admin, to test if the employee can read or change it later on
        for field in sign_user_fields:
            admin.sudo()[field] = base64.b64encode(b'admin')

        signature = base64.b64encode(b'foo')
        for field in sign_user_fields:
            # A user must be able to change his own signature / initials
            my_user[field] = signature
            # and read
            self.assertEqual(my_user[field], signature, f'An employee must be able to read his own {field!r}')
            # but not others
            with self.assertRaises(AccessError, msg=f'An employee must not be able to write {field!r} of another user'):
                admin[field] = signature
            with self.assertRaises(AccessError, msg=f'An employee must not be able to read {field!r} of another user'):
                admin[field]

            # Let's take the assumption the employee obtains the attachment id linked to the admin attachments somehow.
            # Hence herebelow the sudo just to get the id of the attachment
            attachment_id = self.env['ir.attachment'].sudo().search([
                ('res_model', '=', 'res.users'),
                ('res_id', '=', admin.id),
                ('res_field', '=', field),
            ]).id

            with self.assertRaises(
                AccessError,
                msg=f'An employee must not be able to read the attachment related to the {field!r} of another user'
            ):
                self.env['ir.attachment'].browse(attachment_id).datas

    @users('foo')
    def test_sign_user_fields_preferences_form(self):
        """
        Test an employee can change its signature and initials through the preferences form

        It deserves a test because of the tricky case that the signature and initials fields are protected
        behind a `groups='base.group_system' but part of the `SELF_WRITEABLE_FIELDS`,
        as a user should be able to change its own signature and initials,
        so they should be included in the user preferences form and be editable.
        """
        my_user = self.env['res.users'].browse(self.env.user.id)
        signature = base64.b64encode(b'signature')
        initials = base64.b64encode(b'initials')
        with Form(my_user, view='base.view_users_form_simple_modif') as UserForm:
            UserForm.sign_signature = signature
            UserForm.sign_initials = initials
        self.assertEqual(my_user.sign_signature, signature)
        self.assertEqual(my_user.sign_initials, initials)

    def test_user_sign_item(self):
        env_user = self.env(user=self.user)
        attachment = env_user['ir.attachment'].create({'name': 'foo', 'datas': self.pdf})
        attachment_2 = env_user['ir.attachment'].create({'name': 'foo', 'datas': self.pdf})
        template = env_user['sign.template'].create({'attachment_id': attachment.id})
        template_2 = self.env['sign.template'].create({'attachment_id': attachment_2.id})

        sign_item = env_user['sign.item'].create({
            'template_id': template.id,
            'type_id': self.env.ref('sign.sign_item_type_name').id,
            'posX': 0.190,
            'posY': 0.185,
            'width': 0.680,
            'height': 0.015,
        })

        with self.assertRaises(AccessError):
            template_2.with_env(env_user).read(['name'])

        with self.assertRaises(AccessError):
            sign_item.template_id = template_2

        with self.assertRaises(AccessError):
            env_user['sign.item'].create({
                'template_id': template_2.id,
                'type_id': self.env.ref('sign.sign_item_type_name').id,
                'posX': 0.190,
                'posY': 0.185,
                'width': 0.680,
                'height': 0.015,
            })
