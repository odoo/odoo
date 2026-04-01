# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.im_livechat.tests.chatbot_common import ChatbotCase
from odoo.addons.mail.tests.common import MailCommon

class CrmChatbotCase(MailCommon, ChatbotCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._create_portal_user()
        teams_data = [
            {
                "company_id": cls.company_admin.id,
                "crm_team_member_ids": [Command.create({"user_id": cls.user_employee.id})],
                "name": "Test Sale Team 1",
            },
            {
                "company_id": cls.company_admin.id,
                "name": "Test Sale Team 2",
                "use_leads": True,
            },
        ]
        cls.sale_team, cls.sale_team_with_lead = cls.env["crm.team"].create(teams_data)
        cls.step_dispatch_create_lead = cls.env['chatbot.script.answer'].sudo().create({
            'name': 'Create a lead',
            'script_step_id': cls.step_dispatch.id,
        })
        [
            cls.step_create_lead_email,
            cls.step_create_lead_phone,
            cls.step_create_lead,
        ] = cls.env['chatbot.script.step'].sudo().create([{
            'step_type': 'question_email',
            'message': 'Could you provide us your email please.',
            'sequence': 20,
            'triggering_answer_ids': [(4, cls.step_dispatch_create_lead.id)],
            'chatbot_script_id': cls.chatbot_script.id,
        }, {
            'step_type': 'question_phone',
            'message': 'Could you also provide your phone please.',
            'sequence': 21,
            'triggering_answer_ids': [(4, cls.step_dispatch_create_lead.id)],
            'chatbot_script_id': cls.chatbot_script.id,
        }, {
            'step_type': 'create_lead',
            'message': 'Thank you! A lead has been created.',
            'sequence': 22,
            'triggering_answer_ids': [(4, cls.step_dispatch_create_lead.id)],
            'crm_team_id': cls.sale_team.id,
            'chatbot_script_id': cls.chatbot_script.id,
        }])
