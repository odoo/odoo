# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.mail.tests.common import MailCase
from odoo.tests.common import Form, tagged, HttpCase


@tagged("-at_install", "post_install")
class TestMailActivityChatter(HttpCase):

    def test_chatter_activity_tour(self):
        testuser = self.env['res.users'].create({
            'email': 'testuser@testuser.com',
            'name': 'Test User',
            'login': 'testuser',
            'password': 'testuser',
        })
        self.start_tour(
            f"/web#id={testuser.partner_id.id}&model=res.partner",
            "mail_activity_schedule_from_chatter",
            login="admin",
        )


class ActivityScheduleCase(HttpCase, MailCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_admin = cls.env.ref('base.user_admin')
        cls.model_res_partner = cls.env.ref('base.model_res_partner')
        cls.activity_type_todo = cls.env.ref('mail.mail_activity_data_todo')
        cls.activity_type_call = cls.env.ref('mail.mail_activity_data_call')
        cls.plan_party = cls.env['mail.activity.plan'].create({
            'name': 'Test Plan A Party',
            'res_model_ids': False,
            'template_ids': [Command.create({
                'activity_type_id': cls.activity_type_todo.id,
                'summary': 'Book a place',
                'responsible_type': 'on_demand',
                'sequence': 10,
            }), Command.create({
                'activity_type_id': cls.activity_type_todo.id,
                'summary': 'Invite special guest',
                'responsible_type': 'other',
                'responsible_id': cls.user_admin.id,
                'sequence': 20,
            }),
            ],
        })
        cls.plan_onboarding = cls.env['mail.activity.plan'].create({
            'name': 'Test Onboarding',
            'res_model_ids': False,
            'template_ids': [Command.create({
                'activity_type_id': cls.activity_type_todo.id,
                'summary': 'Plan training',
                'responsible_type': 'other',
                'responsible_id': cls.user_admin.id,
                'sequence': 10,
            }), Command.create({
                'activity_type_id': cls.activity_type_todo.id,
                'summary': 'Training',
                'responsible_type': 'other',
                'responsible_id': cls.user_admin.id,
                'sequence': 20,
            }),
            ]
        })

    def reverse_record_set(self, records):
        """ Get an equivalent recordset but with elements in reversed order. """
        return self.env[records._name].browse([record.id for record in reversed(records)])

    def get_last_activities(self, on_record, limit=None):
        """ Get the last activities on the record in id asc order. """
        return self.reverse_record_set(self.env['mail.activity'].search(
            [('res_model', '=', on_record._name), ('res_id', '=', on_record.id)], order='id desc', limit=limit))

    def get_last_message(self, on_record):
        """ Get the last non-internal message posted on the given record. """
        return self.env['mail.message'].search([('model', '=', on_record._name),
                                                ('is_internal', '=', False),
                                                ('res_id', '=', on_record.id)], order='id desc', limit=1)

    def _instantiate_activity_schedule_wizard(self, records, additional_context_value=None):
        """ Get a new Form with context default values referring to the records. """
        return Form(self.env['mail.activity.schedule'].with_context({
            'default_res_ids': ','.join(str(record.id) for record in records),
            'default_res_model': records._name,
            **(additional_context_value if additional_context_value else {}),
        }))
