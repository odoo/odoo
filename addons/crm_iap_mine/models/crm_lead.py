# -*- coding: utf-8 -*-
from odoo.addons import crm
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class CrmLead(models.Model, crm.CrmLead):

    lead_mining_request_id = fields.Many2one('crm.iap.lead.mining.request', string='Lead Mining Request', index='btree_not_null')

    def _merge_get_fields(self):
        return super()._merge_get_fields() + ['lead_mining_request_id']

    def action_generate_leads(self):
        return {
            "name": _("Need help reaching your target?"),
            "type": "ir.actions.act_window",
            "res_model": "crm.iap.lead.mining.request",
            "target": "new",
            "views": [[False, "form"]],
            "context": {"is_modal": True},
        }
