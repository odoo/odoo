# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import OrderedDict
from lxml import etree
from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import tagged

from .test_project_sharing import TestProjectSharingCommon


@tagged('post_install', '-at_install')
class TestProjectSharingPortalAccess(TestProjectSharingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        project_share_wizard = cls.env['project.share.wizard'].create({
            'access_mode': 'edit',
            'res_model': 'project.project',
            'res_id': cls.project_portal.id,
            'partner_ids': [
                Command.link(cls.partner_portal.id),
            ],
        })
        project_share_wizard.action_share_record()

        Task = cls.env['project.task']
        cls.read_protected_fields_task = OrderedDict([
            (k, v)
            for k, v in Task._fields.items()
            if k in Task.SELF_READABLE_FIELDS
        ])
        cls.write_protected_fields_task = OrderedDict([
            (k, v)
            for k, v in Task._fields.items()
            if k in Task.SELF_WRITABLE_FIELDS
        ])
        cls.readonly_protected_fields_task = OrderedDict([
            (k, v)
            for k, v in Task._fields.items()
            if k in Task.SELF_READABLE_FIELDS and k not in Task.SELF_WRITABLE_FIELDS
        ])
        cls.other_fields_task = OrderedDict([
            (k, v)
            for k, v in Task._fields.items()
            if k not in Task.SELF_READABLE_FIELDS
        ])

    def test_readonly_fields(self):
        """ The fields are not writeable should not be editable by the portal user. """
        view_infos = self.task_portal.get_view(self.env.ref(self.project_sharing_form_view_xml_id).id)
        fields = [el.get('name') for el in etree.fromstring(view_infos['arch']).xpath('//field[not(ancestor::field)]')]
        project_task_fields = {
            field_name
            for field_name in fields
            if field_name not in self.write_protected_fields_task
        }
        with self.get_project_sharing_form_view(self.task_portal, self.user_portal) as form:
            for field in project_task_fields:
                with self.assertRaises(AssertionError, msg="Field '%s' should be readonly in the project sharing form view "):
                    form.__setattr__(field, 'coucou')

    def test_read_task_with_portal_user(self):
        self.task_portal.with_user(self.user_portal).read(self.read_protected_fields_task)

        with self.assertRaises(AccessError):
            self.task_portal.with_user(self.user_portal).read(self.other_fields_task)

    def test_write_with_portal_user(self):
        for field in self.readonly_protected_fields_task:
            with self.assertRaises(AccessError):
                self.task_portal.with_user(self.user_portal).write({field: 'dummy'})

        for field in self.other_fields_task:
            with self.assertRaises(AccessError):
                self.task_portal.with_user(self.user_portal).write({field: 'dummy'})

    def test_wizard_confirm(self):
        partner_portal_no_user = self.env['res.partner'].create({
            'name': 'NoUser portal',
            'email': 'no@user.portal',
            'company_id': False,
            'user_ids': [],
        })

        project_share_wizard_no_user = self.env['project.share.wizard'].create({
            'access_mode': 'edit',
            'res_model': 'project.project',
            'res_id': self.project_portal.id,
            'partner_ids': [
                Command.link(partner_portal_no_user.id),
            ],
        })
        self.env["res.config.settings"].create({"auth_signup_uninvited": 'b2b'}).execute()

        project_share_wizard_no_user_action = project_share_wizard_no_user.action_share_record()
        self.assertEqual(project_share_wizard_no_user_action['type'], 'ir.actions.act_window', 'Sharing a project with partner without user should display a confimation dialog')
        project_share_wizard_confirmation = self.env['project.share.wizard'].browse(project_share_wizard_no_user_action['res_id'])

        project_share_wizard_confirmation.action_send_mail()
        mail_partner = self.env['mail.message'].search([('partner_ids', '=', partner_portal_no_user.id)], limit=1)
        self.assertTrue(mail_partner, 'A mail should have been sent to the non portal user')
        self.assertIn('href="http://localhost:8069/web/signup', str(mail_partner.body), 'The message link should contain the url to register to the portal')
        self.assertIn('token=', str(mail_partner.body), 'The message link should contain a personalized token to register to the portal')
