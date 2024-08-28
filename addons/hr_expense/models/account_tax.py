# -*- coding: utf-8 -*-

from odoo import models


class AccountTax(models.Model):
    _inherit = "account.tax"

    def _hook_compute_is_used(self, taxes_to_compute):
        # OVERRIDE in order to fetch taxes used in expenses

        used_taxes = super()._hook_compute_is_used(taxes_to_compute)
        taxes_to_compute -= used_taxes

        if taxes_to_compute:
            self.env['hr.expense'].flush_model(['tax_ids'])
            self.env.cr.execute("""
                SELECT id
                FROM account_tax
                WHERE EXISTS(
                    SELECT 1
                    FROM expense_tax AS exp
                    WHERE tax_id IN %s
                    AND account_tax.id = exp.tax_id
                )
            """, [tuple(taxes_to_compute)])

            used_taxes.update([tax[0] for tax in self.env.cr.fetchall()])

        return used_taxes

    def _prepare_base_line_for_taxes_computation(self, record, **kwargs):
        # EXTENDS 'account'
        results = super()._prepare_base_line_for_taxes_computation(record, **kwargs)
        results['expense_id'] = self._get_base_line_field_value_from_record(record, 'expense_id', kwargs, self.env['hr.expense'])
        return results

    def _prepare_tax_line_for_taxes_computation(self, record, **kwargs):
        # EXTENDS 'account'
        results = super()._prepare_tax_line_for_taxes_computation(record, **kwargs)
        results['expense_id'] = self._get_base_line_field_value_from_record(record, 'expense_id', kwargs, self.env['hr.expense'])
        return results

    def _prepare_base_line_grouping_key(self, base_line):
        # EXTENDS 'account'
        results = super()._prepare_base_line_grouping_key(base_line)
        results['expense_id'] = base_line['expense_id'].id
        return results

    def _prepare_tax_line_repartition_grouping_key(self, tax_line):
        # EXTENDS 'account'
        results = super()._prepare_tax_line_repartition_grouping_key(tax_line)
        results['expense_id'] = tax_line['expense_id'].id
        return results
