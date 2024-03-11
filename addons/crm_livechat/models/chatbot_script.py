# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ChatbotScript(models.Model):
    _inherit = 'chatbot.script'

    lead_count = fields.Integer(
        string='Generated Lead Count', compute='_compute_lead_count')

    def _compute_lead_count(self):
        mapped_leads = {}
        if self.ids:
            leads_data = self.env['crm.lead'].with_context(active_test=False).sudo()._read_group(
                [('source_id', 'in', self.mapped('source_id').ids)], ['source_id'], ['source_id'])
            mapped_leads = {lead['source_id'][0]: lead['source_id_count'] for lead in leads_data}

        for script in self:
            script.lead_count = mapped_leads.get(script.source_id.id, 0)

    def action_view_leads(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('crm.crm_lead_all_leads')
        action['domain'] = [('source_id', '=', self.source_id.id)]
        action['context'] = {'create': False}
        return action
