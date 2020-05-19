# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class Stock(models.Model):
    _inherit = 'stock.warehouse'

    l10n_in_purchase_journal_id = fields.Many2one('account.journal', string="Purchase Journal")

    @api.onchange('partner_id')
    def onchange_purchase_partner_id(self):
        self.l10n_in_purchase_journal_id = False

        if self.partner_id:
            purchase_journal = self.env['account.journal'].search([('company_id', '=', self.env.company.id), 
                ('type','=','purchase'), ('l10n_in_gstin_partner_id','=',self.partner_id.id)], limit=1)
            
            if purchase_journal:
                self.l10n_in_purchase_journal_id = purchase_journal.id