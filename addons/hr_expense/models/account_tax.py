# -*- coding: utf-8 -*-

from collections import Counter
from odoo import models


class AccountTax(models.Model):
    _inherit = "account.tax"

    def _hook_compute_is_used(self):
        # OVERRIDE in order to count the usage of taxes in expenses

        taxes_in_transactions_ctr = Counter(dict(self.env['hr.expense']._read_group([], groupby=['tax_ids'], aggregates=['__count'])))

        return super()._hook_compute_is_used() + taxes_in_transactions_ctr
