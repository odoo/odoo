# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64

from odoo.exceptions import AccessError
from odoo.tests import TransactionCase


class testAttachmentAccess(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.env['res.users'].create({
            'name': "foo",
            'login': "foo",
            'email': "foo@bar.com",
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('base.group_partner_manager').id,
            ])]
        })
        cls.letter_defaults = {
            'model': cls.user.partner_id._name,
            'res_id': cls.user.partner_id.id,
            'partner_id': cls.user.partner_id.id,
        }

    def test_user_letter_attachment_without_res_fields(self):
        """Test an employee can create a letter linked to an attachment without res_model/res_id"""
        env_user = self.env(user=self.user)
        # As user, create an attachment without res_model/res_id
        attachment = env_user['ir.attachment'].create({'name': 'foo', 'datas': base64.b64encode(b'foo')})
        # As user, create a snailmail.letter linked to that attachment
        letter = env_user['snailmail.letter'].create({'attachment_id': attachment.id, **self.letter_defaults})
        # As user, ensure the content of the attachment can be read through the letter
        self.assertEqual(base64.b64decode(letter.attachment_datas), b'foo')
        # As user, create another attachment without res_model/res_id
        attachment_2 = env_user['ir.attachment'].create({'name': 'foo', 'datas': base64.b64encode(b'bar')})
        # As user, change the attachment of the letter to this second attachment
        letter.write({'attachment_id': attachment_2.id})
        # As user, ensure the content of this second attachment can be read through the letter
        self.assertEqual(base64.b64decode(letter.attachment_datas), b'bar')

    def test_user_letter_attachment_without_res_fields_created_by_admin(self):
        """Test an employee can read the content of the letter's attachment created by another user, the admin,
        and the attachment does not have a res_model/res_id
        """
        # As admin, create an attachment without res_model/res_id
        attachment = self.env['ir.attachment'].create({'name': 'foo', 'datas': base64.b64encode(b'foo')})
        # As admin, create a snailmail.letter linked to that attachment
        letter = self.env['snailmail.letter'].create({'attachment_id': attachment.id, **self.letter_defaults})

        # As user, ensure the attachment itself cannot be read
        self.env.invalidate_all()
        with self.assertRaises(AccessError):
            attachment.with_user(self.user).datas
        # But, as user, the content of the attachment can be read through the letter
        self.assertEqual(base64.b64decode(letter.with_user(self.user).attachment_datas), b'foo')

        # As admin, create a second attachment without res_model/res_id
        attachment = self.env['ir.attachment'].create({'name': 'bar', 'datas': base64.b64encode(b'bar')})
        # As admin, link this second attachment to the previously created letter (write instead of create)
        letter.write({'attachment_id': attachment.id})

        # As user ensure the attachment itself cannot be read
        self.env.invalidate_all()
        with self.assertRaises(AccessError):
            self.assertEqual(base64.b64decode(attachment.with_user(self.user).datas), b'bar')
        # But, as user, the content of the attachment can be read through the letter
        self.assertEqual(base64.b64decode(letter.with_user(self.user).attachment_datas), b'bar')

    def test_user_read_unallowed_attachment(self):
        """Test a user cannot access an attachment he is not supposed to through a snailmail.letter"""
        # As admin, create an attachment for which you require the settings group to access
        autovacuum_job = self.env.ref('base.autovacuum_job')
        attachment_forbidden = self.env['ir.attachment'].create({
            'name': 'foo', 'datas': base64.b64encode(b'foo'),
            'res_model': autovacuum_job._name, 'res_id': autovacuum_job.id,
        })
        # As user, make sure this is indeed not possible to access that attachment data directly
        self.env.invalidate_all()
        with self.assertRaises(AccessError):
            attachment_forbidden.with_user(self.user).datas
        # As user, create a letter pointing to that attachment
        # and make sure it raises an access error
        with self.assertRaises(AccessError):
            letter = self.env['snailmail.letter'].with_user(self.user).create({
                'attachment_id': attachment_forbidden.id,
                **self.letter_defaults,
            })
            letter.attachment_datas

        # As user, update the attachment of an existing letter to the unallowed attachment
        # and make sure it raises an access error
        attachment_tmp = self.env['ir.attachment'].with_user(self.user).create({
            'name': 'bar', 'datas': base64.b64encode(b'bar'),
        })
        letter = self.env['snailmail.letter'].with_user(self.user).create({
            'attachment_id': attachment_tmp.id,
            **self.letter_defaults,
        })
        with self.assertRaises(AccessError):
            letter.write({'attachment_id': attachment_forbidden.id})
            letter.attachment_datas
