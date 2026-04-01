# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from collections import OrderedDict
from lxml import etree
from re import search

from odoo import Command
from odoo.tools import mute_logger, config
from odoo.exceptions import AccessError
from odoo.tests import HttpCase, tagged

from .test_project_sharing import TestProjectSharingCommon


@tagged('post_install', '-at_install')
class TestProjectSharingPortalAccess(TestProjectSharingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['project.share.wizard'].create({
            'res_model': 'project.project',
            'res_id': cls.project_portal.id,
            'collaborator_ids': [
                Command.create({'partner_id': cls.partner_portal.id, 'access_mode': 'edit'}),
            ],
        })

        Task = cls.env['project.task']
        readable_fields, writeable_fields = Task._portal_accessible_fields()
        cls.read_protected_fields_task = OrderedDict([
            (k, v)
            for k, v in Task._fields.items()
            if k in readable_fields
        ])
        cls.write_protected_fields_task = OrderedDict([
            (k, v)
            for k, v in Task._fields.items()
            if k in writeable_fields
        ])
        cls.readonly_protected_fields_task = OrderedDict([
            (k, v)
            for k, v in Task._fields.items()
            if k in readable_fields and k not in writeable_fields
        ])
        cls.other_fields_task = OrderedDict([
            (k, v)
            for k, v in Task._fields.items()
            if k not in readable_fields
        ])

    def test_mention_suggestions(self):
        data = self.task_portal.with_user(self.user_portal).get_mention_suggestions(search="")
        suggestion_ids = {partner.get("id") for partner in data.get("res.partner")}
        self.assertEqual(
            suggestion_ids,
            {self.user_projectuser.partner_id.id, self.user_portal.partner_id.id},
            "Portal user as a project collaborator should have access to mention suggestions",
        )
        self.assertEqual(
            data["res.partner"][0]["mention_token"],
            self.user_projectuser.partner_id._get_mention_token(),
        )
        self.assertEqual(
            data["res.partner"][1]["mention_token"],
            self.user_portal.partner_id._get_mention_token(),
        )
        # remove portal user from the project collaborators
        self.project_portal.collaborator_ids.filtered(
            lambda rec: rec.partner_id == self.user_portal.partner_id
        ).unlink()
        self.assertEqual(
            {},
            self.task_portal.with_user(self.user_portal).get_mention_suggestions(search=""),
            "Non collaborator portal user should not have access to mention suggestions",
        )

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
        task = self.task_portal.with_user(self.user_portal)
        task.check_access('read')
        task.read(self.read_protected_fields_task)

        for field in self.other_fields_task:
            task.invalidate_recordset()
            with self.assertRaises(AccessError, msg=f"Field {field} should be inaccessible"):
                task.read([field])

    def test_write_task_with_portal_user(self):
        task = self.task_portal.with_user(self.user_portal)
        task.check_access('write')

        def dummy_value(field_name):
            field = task._fields[field_name]
            if field.is_text:
                value = 'dummy'
                if field.type == 'html':
                    value = f'<p>{value}</p>'
                return value
            if field.relational and field.comodel_name != 'ir.attachment':
                value = task.env[field.comodel_name].search([], limit=1).id
                if field.type != 'many2one':
                    value = [value]
                return value
            if field.name == 'id':
                return 42
            return task.default_get([field_name]).get(field_name, False)

        for field_name in self.write_protected_fields_task:
            field = task._fields[field_name]
            if field.comodel_name == 'project.task':
                other_task = self.env['project.task'].create({'name': 'Parent task', 'project_id': task.project_id.id})
                value = other_task.id if field.type == 'many2one' else other_task.ids
                task.write({field_name: value})
                self.assertEqual(task[field_name], other_task)
            else:
                value = dummy_value(field_name)
                task.write({field_name: value})
                actual_value = task[field_name]
                expected_value = field.convert_to_record(value, task)
                self.assertEqual(actual_value, expected_value, f"Field {field} should be editable.")

        for field in self.readonly_protected_fields_task:
            with self.assertRaises(AccessError, msg=f"Field {field} should be readonly"):
                task.write({field: dummy_value(field)})

        for field in self.other_fields_task:
            with self.assertRaises(AccessError, msg=f"Field {field} should be inaccessible"):
                task.write({field: dummy_value(field)})

    def test_wizard_confirm(self):
        partner_portal_no_user = self.env['res.partner'].create({
            'name': 'NoUser portal',
            'email': 'no@user.portal',
            'company_id': False,
            'user_ids': [],
        })

        project_share_wizard_no_user = self.env['project.share.wizard'].create({
            'res_model': 'project.project',
            'res_id': self.project_portal.id,
            'collaborator_ids': [
                Command.create({'partner_id': partner_portal_no_user.id, 'access_mode': 'edit'}),
            ],
        })
        self.env["res.config.settings"].create({"auth_signup_uninvited": 'b2b'}).execute()

        project_share_wizard_no_user_action = project_share_wizard_no_user.action_share_record()
        self.assertEqual(project_share_wizard_no_user_action['type'], 'ir.actions.act_window', 'Sharing a project with partner without user should display a confimation dialog')
        project_share_wizard_confirmation = self.env['project.share.wizard'].browse(project_share_wizard_no_user_action['res_id'])

        project_share_wizard_confirmation.action_send_mail()
        mail_partner = self.env['mail.message'].search([('partner_ids', '=', partner_portal_no_user.id)], limit=1)
        self.assertTrue(mail_partner, 'A mail should have been sent to the non portal user')
        self.assertIn(f'href="http://localhost:{config["http_port"]}/web/signup', str(mail_partner.body), 'The message link should contain the url to register to the portal')
        self.assertIn('token=', str(mail_partner.body), 'The message link should contain a personalized token to register to the portal')


class TestProjectSharingChatterAccess(TestProjectSharingCommon, HttpCase):
    @mute_logger('odoo.addons.http_routing.models.ir_http', 'odoo.http')
    def test_post_chatter_as_portal_user(self):
        self.project_no_collabo.privacy_visibility = 'portal'
        message = self.get_project_share_link()
        share_link = str(message.body.split('href="')[1].split('">')[0])
        match = search(r"access_token=([^&]+)&amp;pid=([^&]+)&amp;hash=([^&]*)", share_link)
        access_token, pid, _hash = match.groups()

        res = self.url_open(
            url="/mail/message/post",
            data=json.dumps({
                "params": {
                    "thread_model": self.task_no_collabo._name,
                    "thread_id": self.task_no_collabo.id,
                    "post_data": {'body': '(-b ±√[b²-4ac]) / 2a'},
                    "token": access_token,
                    "pid": pid,
                    "hash": _hash,
                },
            }),
            headers={'Content-Type': 'application/json'},
        )
        self.assertEqual(res.status_code, 200)

        self.assertTrue(
            self.env['mail.message'].sudo().search([
                ('author_id', '=', self.user_portal.partner_id.id),
            ])
        )
