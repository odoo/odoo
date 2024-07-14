# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.im_livechat.tests.chatbot_common import ChatbotCase
from odoo.addons.mail.tests.common import mail_new_test_user


class HelpdeskChatbotCase(ChatbotCase):

    @classmethod
    def setUpClass(cls):
        """ Override to the default chatbot script that adds ticket creation steps. """

        super().setUpClass()

        cls.company_id = cls.env['res.company'].create({
            'name': 'Test Company',
            'country_id': cls.env.ref('base.be').id,
        })

        cls.user_public = mail_new_test_user(
            cls.env, login='user_public', groups='base.group_public', name='Public User')
        cls.user_portal = mail_new_test_user(
            cls.env, login='user_portal', groups='base.group_portal', name='Portal User',
            company_id=cls.company_id.id, email='portal@example.com')
        # update company_id on partner since the user's company is not propagated
        cls.user_portal.partner_id.write({'company_id': cls.company_id.id})

        cls.helpdesk_team = cls.env['helpdesk.team'].create({
            'name': 'Helpdesk Team',
            'company_id': cls.company_id.id,
        })

        cls.step_selection_ticket = cls.env['chatbot.script.answer'].sudo().create({
            'name': 'Create a Ticket',
            'script_step_id': cls.step_dispatch.id,
        })

        [
            cls.step_helpdesk_issue,
            cls.step_helpdesk_email,
            cls.step_helpdesk_phone,
            cls.step_helpdesk_create_ticket,
        ] = cls.env['chatbot.script.step'].sudo().create([{
            'step_type': 'free_input_multi',
            'sequence': 30,
            'message': 'Could you please explain your issue?',
            'triggering_answer_ids': [(4, cls.step_selection_ticket.id)],
            'chatbot_script_id': cls.chatbot_script.id,
        }, {
            'step_type': 'question_email',
            'sequence': 31,
            'message': 'Alright, got it, what is your email so we can contact you?',
            'triggering_answer_ids': [(4, cls.step_selection_ticket.id)],
            'chatbot_script_id': cls.chatbot_script.id,
        }, {
            'step_type': 'question_phone',
            'sequence': 32,
            'message': 'And finally, could you provide your phone number please?',
            'triggering_answer_ids': [(4, cls.step_selection_ticket.id)],
            'chatbot_script_id': cls.chatbot_script.id,
        }, {
            'step_type': 'create_ticket',
            'sequence': 33,
            'message': 'Thank you, a ticket has been created! We will reach out soon.',
            'triggering_answer_ids': [(4, cls.step_selection_ticket.id)],
            'chatbot_script_id': cls.chatbot_script.id,
        }])
