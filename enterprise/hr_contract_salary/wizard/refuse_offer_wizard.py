# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError


class GenerateSimulationLink(models.TransientModel):
    _name = 'refuse.offer.wizard'
    _description = 'Refuse an Offer'

    refusal_reason = fields.Many2one('hr.contract.salary.offer.refusal.reason', string="Refusal Reason", required=True)

    def action_refuse(self):
        offer_ids = self.env['hr.contract.salary.offer'].browse(self.env.context.get("active_ids"))
        if not offer_ids:
            raise UserError(_("No offer selected"))
        offer_ids.action_refuse_offer(refusal_reason=self.refusal_reason.id)
        action = self.env['ir.actions.act_window']._for_xml_id('hr_contract_salary.hr_contract_salary_offer_action')
        if len(offer_ids) == 1:
            action['view_mode'] = 'form'
            action['res_id'] = offer_ids.id
            action['views'] = [[False, "form"]]
        else:
            action['domain'] = [('id', 'in', offer_ids.ids)]
        return action
