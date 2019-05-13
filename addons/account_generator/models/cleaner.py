# -*- coding: utf-8 -*-

from odoo import api, models, fields


class AccountCleaner(models.TransientModel):
    _name = "account.cleaner"
    _description = "Account Cleaner"

    company_ids = fields.Many2many('res.company', default=lambda self: self.env.companies)

    def clean_account_move(self):
        company_ids = tuple(self.company_ids.ids)

        self.env.cr.execute('delete from account_partial_reconcile where company_id in %s;', [company_ids])
        self.env.cr.execute('delete from account_move_line where company_id in %s;', [company_ids])
        self.env.cr.execute('delete from account_move where company_id in %s;', [company_ids])
