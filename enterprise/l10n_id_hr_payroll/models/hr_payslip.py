# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from datetime import date

KODE_PTKP_MAPPING = {
    'tk0': 'a',
    'tk1': 'a',
    'k0': 'a',
    'tk2': 'b',
    'tk3': 'b',
    'k1': 'b',
    'k2': 'b',
    'k3': 'c',
}


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    l10n_id_include_jkk_jkm = fields.Boolean(default=True)  # jkk jkm jht jp
    l10n_id_include_bpjs_kesehatan = fields.Boolean(default=True)  # bpjs kesehatan + its deduction
    l10n_id_include_pkp_ptkp = fields.Boolean(
        compute="_compute_l10n_id_include_pkp_ptkp", store=True, readonly=False)  # include the PTKP/PKP computation

    def _l10n_id_get_historical_categorical_total(self, codes):
        """ Get the total amount of specific category among the contract's taxes history that has been validated
        within a certain year"""
        date_start = date(self.date_to.year, 1, 1)
        payslips = self.env['hr.payslip'].search([
            ('date_to', '>', date_start),
            ('date_to', '<', self.date_to),
            ('state', 'in', ['done', 'paid'])
        ])
        vals = payslips._get_line_values(codes, compute_sum=True)
        return sum(vals[code]['sum']['total'] for code in codes)

    def _l10n_id_get_pph21_amount(self, amount):
        """ Find the right percentage to apply depending on the GROSS amount of the payslip"""
        category_type = KODE_PTKP_MAPPING[self.employee_id.l10n_id_kode_ptkp]

        ranges = self._rule_parameter('l10n_id_pph21_percentage_' + category_type)
        for line in ranges:
            if amount < line[1]:
                return line[2]

    def _l10n_id_get_worked_days_rate(self):
        """Total number of worked days (incl leaves except out of contract)/total number of days
        value is returned between 0 to 1"""
        total_days = sum(self.worked_days_line_ids.mapped('number_of_days'))
        wds = self.worked_days_line_ids.filtered(lambda wd: wd.code != 'OUT')
        number_of_days = sum(wds.mapped('number_of_days'))
        return number_of_days / total_days

    def _l10n_id_get_end_total_pph_amount(self):
        """ Getting the accumulated PPH21 amount over the course of a year (from start of year/contract)"""
        return self._l10n_id_get_historical_categorical_total(['PPH21'])

    def _l10n_id_get_gross_accumulated(self):
        # gross_lines = self._l10n_id_get_historical_categorical_total_lines(['GROSS'])
        date_start = date(self.date_to.year, 1, 1)
        payslips = self.env['hr.payslip'].search([
            ('date_to', '>', date_start),
            ('date_to', '<', self.date_to),
            ('state', 'in', ['done', 'paid'])
        ])
        vals = payslips._get_line_values(['GROSS'])['GROSS']
        gross_lines = [vals[i]['total'] for i in payslips.ids]

        sum_gross = 0
        threshold = self._rule_parameter('l10n_id_biaya_jabatan_salary_threshold')
        percent = self._rule_parameter('l10n_id_biaya_jabatan_percent')
        for line in gross_lines:
            amount = min(line, threshold)
            sum_gross += (percent / 100) * amount

        return sum_gross

    def _l10n_id_get_total_gross(self):
        """ Get the total GROSS accumulated before the current payslip"""
        return self._l10n_id_get_historical_categorical_total(['GROSS'])

    @api.depends('date_from', 'date_to', 'contract_id.date_start', 'contract_id.date_end')
    def _compute_l10n_id_include_pkp_ptkp(self):
        """ by default, if it's end of year/end of contract, set to True"""
        for slip in self:
            slip.l10n_id_include_pkp_ptkp = (
                slip.date_to and (
                    (slip.date_to.month == 12) or
                    (
                        slip.contract_id.date_end and
                        slip.contract_id.date_end.month == slip.date_to.month and
                        slip.contract_id.date_end.year == slip.date_to.year
                    )
                )
            )
