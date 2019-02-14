# -*- coding: utf-8 -*-
from odoo import models

class AccountReconciliation(models.AbstractModel):
    _inherit = 'account.reconciliation.widget'

    def _str_domain_for_mv_line(self, search_str):
        return ['|', ('payment_id.check_number', '=', search_str)] + super(AccountReconciliation, self)._str_domain_for_mv_line(search_str)
