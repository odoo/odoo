from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    simplified_invoice_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Simplified Journal',
        domain=[('type', '=', 'general')],
        check_company=True,
    )

    def _get_simplified_journal(self):
        if self.simplified_invoice_journal_id:
            return self.simplified_invoice_journal_id
        if not self.simplified_invoice_journal_id:
            simplified_journal = self.env['account.journal']
            for company in reversed(self.sudo().parent_ids):
                if journal := company.simplified_invoice_journal_id:
                    simplified_journal = journal
                    break
            if not simplified_journal:
                simplified_journal = self.env['account.journal'].sudo().search([
                    *self.env['account.journal']._check_company_domain(self),
                    ('code', '=', 'SINV'),  # TRTRN for Backward compatibility
                    ('type', '=', 'general'),
                ])
            if not simplified_journal:
                # Try reloading the chart template data to create the tax return journal with translations.
                ChartTemplate = self.env['account.chart.template'].with_company(self)
                ChartTemplate._load_data({
                    'account.journal': ChartTemplate._get_simplified_journal(self.chart_template),
                    'res.company': ChartTemplate._get_simplified_res_company(self.chart_template),
                })
                simplified_journal = ChartTemplate.ref('simplified_journal')
            self.simplified_invoice_journal_id = simplified_journal
        return self.simplified_invoice_journal_id
