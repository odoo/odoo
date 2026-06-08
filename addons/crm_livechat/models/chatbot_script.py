# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ChatbotScript(models.Model):
    _inherit = 'chatbot.script'

    lead_count = fields.Integer(
        string='Generated Lead Count', compute='_compute_lead_count')

    def _compute_lead_count(self):
        leads_data = self.env['crm.lead'].with_context(active_test=False).sudo()._read_group(
            [('utm_reference', 'in', [f'{script._name},{script.id}' for script in self])],
            ['utm_reference'], ['__count']
        )
        mapped_leads = dict(leads_data)
        for script in self:
            script.lead_count = mapped_leads.get(f'{script._name},{script.id}', 0)

    def action_view_leads(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('crm.crm_lead_all_leads')
        action['domain'] = [('utm_reference', '=', f'{self._name},{self.id}')]
        action['context'] = {'create': False}
        return action
