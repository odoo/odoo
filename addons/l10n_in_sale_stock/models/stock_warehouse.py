# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class Stock(models.Model):
    _inherit = 'stock.warehouse'

    l10n_in_sale_journal_id = fields.Many2one('account.journal', string="Sale Journal")

    @api.onchange('partner_id')
    def onchange_sale_partner_id(self):
        self.l10n_in_sale_journal_id = False
        
        if self.partner_id:
            sale_journal = self.env['account.journal'].search([('company_id', '=', self.env.company.id), 
                ('type','=','sale'), ('l10n_in_gstin_partner_id','=',self.partner_id.id)], limit=1)

            if sale_journal:
                self.l10n_in_sale_journal_id = sale_journal.id