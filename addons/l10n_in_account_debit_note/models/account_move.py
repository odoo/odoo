# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_last_sequence_domain(self, relaxed=False):
        where_string, param = super()._get_last_sequence_domain(relaxed)
        if self.debit_origin_id and self.country_code == "IN":
            where_string += " AND debit_origin_id IS NOT NULL"
        return where_string, param

    def _get_starting_sequence(self):
        starting_sequence = super()._get_starting_sequence()
        if self.debit_origin_id and self.country_code == "IN":
            starting_sequence = "D" + starting_sequence
        return starting_sequence
