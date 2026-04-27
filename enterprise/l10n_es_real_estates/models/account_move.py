# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_es_real_estate_id = fields.Many2one(string="Real Estate", comodel_name='l10n_es_reports.real.estate', help="Real estate related to this invoice, in case we are leasing it.")
    l10n_es_reports_mod347_invoice_type = fields.Selection(selection_add=[('real_estates', "Real estates operation")])

    @api.onchange('l10n_es_reports_mod347_invoice_type')
    def _onchange_mod347_invoice_type(self):
        """ Onchange method making sure the l10n_es_real_estate_id field
        is reset to None in case the mod347 invoice type is changed from 'real
        estates' to something else """
        if self.l10n_es_reports_mod347_invoice_type != 'real_estates':
            self.l10n_es_real_estate_id = None


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # Stored to allow being used in the financial reports as a groupby value (we need it since it's called via SQL)
    l10n_es_real_estate_id = fields.Many2one(string="Real Estate", related='move_id.l10n_es_real_estate_id', store=True, help="Real estate related to the invoice that created this move line, in case we are leasing it.", readonly=False)
