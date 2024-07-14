# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    account_represented_company_ids = fields.One2many('res.company', 'account_representative_id')

    def open_partner_ledger(self):
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_account_moves_all_tree")
        action['context'] = {
            'search_default_partner_id': self.id,
            'default_partner_id': self.id,
            'search_default_posted': 1,
            'search_default_trade_payable': 1,
            'search_default_trade_receivable': 1,
        }
        return action
