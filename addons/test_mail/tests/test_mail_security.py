# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import nullcontext

from odoo.addons.mail.tests.common import mail_new_test_user, MailCommon
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged


@tagged('security')
class TestSubtypeAccess(MailCommon):

    def test_subtype_access(self):
        """
        The function aims to formally verify the access restrictions on mail.message.subtype for
        normal and admin users. It ensures that normal users are unable to modify it,
        while admin users possess the necessary privileges to modify it successfully.
        """

        test_subtype = self.env['mail.message.subtype'].create({
            'name': 'Test',
            'description': 'only description',
        })

        user = mail_new_test_user(self.env, 'Internal user', groups='base.group_user')

        with self.assertRaises(AccessError):
            test_subtype.with_user(user).write({'description': 'changing description'})

        test_subtype.with_user(self.user_admin).write({'description': 'testing'})
        self.assertEqual(test_subtype.description, 'testing')

    def test_subtype_protection(self):
        """ Test master data protection """
        for xml_id, is_protected, can_change_internal_flag in [
            ('mail.mt_comment', True, False),
            ('mail.mt_note', True, False),
            ('mail.mt_activities', True, True),
            ('test_mail.st_mail_test_simple_external', False, True),
        ]:
            with self.subTest(xml_id=xml_id):
                subtype = self.env.ref(xml_id)
                raiseIfProtected = self.assertRaises(UserError) if is_protected else nullcontext()

                # protected against model change
                with raiseIfProtected:
                    subtype.write({'res_model': 'res.partner'})

                # on some subtypes internal flag is protected
                raiseIfCannotUpdate = self.assertRaises(UserError) if not can_change_internal_flag else nullcontext()
                with raiseIfCannotUpdate:
                    subtype.write({'internal': not subtype.internal})

                raiseIfProtected = self.assertRaises(UserError) if is_protected else nullcontext()
                # protected against removal
                with raiseIfProtected:
                    subtype.unlink()
