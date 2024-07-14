# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrPayrollReport(models.Model):
    _inherit = 'hr.payroll.report'

    l10n_hk_713_gross = fields.Float('713 Gross', readonly=True)
    l10n_hk_mpf_gross = fields.Float('MPF Gross', readonly=True)
    l10n_hk_autopay_gross = fields.Float('AutoPay Gross', readonly=True)
    l10n_hk_second_batch_autopay_gross = fields.Float('Second Batch AutoPay Gross', readonly=True)

    def _select(self, addtional_rules):
        select_str = super()._select(addtional_rules)
        select_str += """
            ,CASE WHEN wd.id = min_id.min_line THEN pl713.total ELSE 0 END AS l10n_hk_713_gross,
            CASE WHEN wd.id = min_id.min_line THEN plm.total ELSE 0 END AS l10n_hk_mpf_gross,
            CASE WHEN wd.id = min_id.min_line THEN pla.total ELSE 0 END AS l10n_hk_autopay_gross,
            CASE WHEN wd.id = min_id.min_line THEN pls.total ELSE 0 END AS l10n_hk_second_batch_autopay_gross
        """
        return select_str

    def _from(self, additional_rules):
        from_str = super()._from(additional_rules)
        from_str += """
            left join hr_payslip_line pl713 on (pl713.slip_id = p.id and pl713.code = '713_GROSS')
            left join hr_payslip_line plm on (plm.slip_id = p.id and plm.code = 'MPF_GROSS')
            left join hr_payslip_line pla on (pla.slip_id = p.id and pla.code = 'MEA')
            left join hr_payslip_line pls on (pls.slip_id = p.id and pls.code = 'SBA')
        """
        return from_str

    def _group_by(self, additional_rules):
        group_by_str = super()._group_by(additional_rules)
        group_by_str += """
            ,pl713.total,
            plm.total,
            pla.total,
            pls.total
        """
        return group_by_str
