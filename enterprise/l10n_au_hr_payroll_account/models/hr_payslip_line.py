# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class HrPayslip(models.Model):
    _inherit = "hr.payslip.line"

    def _adapt_records_to_w3(self, debit_credit='debit'):
        ''' A special case in some contracts needs to be reported in another section of the tax report.
            We need to remove the reporting to W1 and change the reporting from W2 to W3 for those case.
        '''
        if not self:
            return
        plus_w3_tag_id, minus_w3_tag_id = self.env.ref('l10n_au.account_tax_report_payg_w3_tag')._get_matching_tags().sorted(lambda tag: tag.tax_negate).ids
        plus_w2_tag_id, minus_w2_tag_id = self.env.ref('l10n_au.account_tax_report_payg_w2_tag')._get_matching_tags().sorted(lambda tag: tag.tax_negate).ids
        w1_tag_ids = self.env.ref('l10n_au.account_tax_report_payg_w1_tag')._get_matching_tags().sorted(lambda tag: tag.tax_negate).ids
        for record in self:
            tag_ids = []
            tags_list = record.salary_rule_id.debit_tag_ids if debit_credit == 'debit' else record.salary_rule_id.credit_tag_ids
            for tag in tags_list:
                if tag.id in (plus_w2_tag_id, minus_w2_tag_id):
                    tag_ids += [minus_w3_tag_id] if tag.tax_negate else [plus_w3_tag_id]
                elif tag.id in w1_tag_ids:
                    continue
                else:
                    tag_ids += [tag.id]
            if debit_credit == 'debit':
                record.debit_tag_ids = tag_ids
            else:
                record.credit_tag_ids = tag_ids

    @api.depends('salary_rule_id.debit_tag_ids', 'contract_id.l10n_au_report_to_w3')
    def _compute_debit_tags(self):
        lines_to_report_in_w3 = self.filtered(lambda record: record.contract_id.l10n_au_report_to_w3)
        lines_to_report_in_w3._adapt_records_to_w3('debit')
        super(HrPayslip, self - lines_to_report_in_w3)._compute_debit_tags()

    @api.depends('salary_rule_id.credit_tag_ids', 'contract_id.l10n_au_report_to_w3')
    def _compute_credit_tags(self):
        lines_to_report_in_w3 = self.filtered(lambda record: record.contract_id.l10n_au_report_to_w3)
        lines_to_report_in_w3._adapt_records_to_w3('credit')
        super(HrPayslip, self - lines_to_report_in_w3)._compute_credit_tags()
