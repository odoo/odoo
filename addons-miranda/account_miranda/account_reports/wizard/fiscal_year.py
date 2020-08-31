# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo import _, api, fields, models


class FinancialYearOpeningWizard(models.TransientModel):
    _inherit = 'account.financial.year.op'
    _description = 'Opening Balance of Financial Year'

    account_tax_periodicity = fields.Selection(related='company_id.account_tax_periodicity', string='Periodicity', readonly=False, required=True)
    account_tax_periodicity_reminder_day = fields.Integer(related='company_id.account_tax_periodicity_reminder_day', string='Reminder', readonly=False, required=True)
    account_tax_periodicity_journal_id = fields.Many2one(related='company_id.account_tax_periodicity_journal_id', string='Journal', readonly=False)

    def write(self, vals):
        res = super().write(vals)
        if vals.get('account_tax_periodicity') or vals.get('account_tax_periodicity_reminder_day') or vals.get('account_tax_periodicity_journal_id'):
            self.env['res.config.settings']._update_account_tax_periodicity_reminder_day()

        return res
