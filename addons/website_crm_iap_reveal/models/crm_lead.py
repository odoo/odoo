# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import website_crm, crm_iap_mine, iap_crm


class CrmLead(iap_crm.CrmLead, crm_iap_mine.CrmLead, website_crm.CrmLead):

    reveal_ip = fields.Char(string='IP Address')
    reveal_iap_credits = fields.Integer(string='IAP Credits')
    reveal_rule_id = fields.Many2one('crm.reveal.rule', string='Lead Generation Rule', index='btree_not_null')

    def _merge_get_fields(self):
        return super()._merge_get_fields() + ['reveal_ip', 'reveal_iap_credits', 'reveal_rule_id']
