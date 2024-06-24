# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from collections import OrderedDict
from lxml import etree
from re import search

from odoo import Command
from odoo.tools import mute_logger
from odoo.exceptions import AccessError
from odoo.tests import tagged, HttpCase

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
        project_share_wizard.action_send_mail()

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


class TestProjectSharingChatterAccess(TestProjectSharingCommon, HttpCase):
    @mute_logger('odoo.addons.http_routing.models.ir_http', 'odoo.http')
    def test_post_chatter_as_portal_user(self):
        self.env['project.share.wizard'].create({
            'res_model': 'project.project',
            'res_id': self.project_no_collabo.id,
            'access_mode': 'edit',
            'partner_ids': [Command.set([self.user_portal.partner_id.id])],
        }).action_send_mail()
        message = self.env['mail.message'].search([
            ('partner_ids', 'in', self.user_portal.partner_id.id),
        ])

        share_link = str(message.body.split('href="')[1].split('">')[0])
        match = search(r"access_token=([^&]+)&amp;pid=([^&]+)&amp;hash=([^&]*)", share_link)
        access_token, pid, _hash = match.groups()

        res = self.url_open(
            url="/mail/chatter_post",
            data=json.dumps({
                "params": {
                    "res_model": 'project.task',
                    "res_id": self.task_no_collabo.id,
                    "message": '(-b ±√[b²-4ac]) / 2a',
                    "attachment_ids": None,
                    "attachment_tokens": None,
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
