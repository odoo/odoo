from odoo import api, fields, models


class Website(models.Model):
    _inherit = 'website'

    simplified_invoice_journal_id = fields.Many2one(
        string="Simplified Invoice Journal",
        comodel_name='account.journal',
        compute='_compute_simplified_invoice_journal_id',
        store=True,
        readonly=False,
        domain="[('type', '=', 'sale'), ('company_id', '=', company_id)]",
        check_company=True,
        help="Journal used for simplified invoices generated from eCommerce.",
    )

    @api.depends('company_id')
    def _compute_simplified_invoice_journal_id(self):
        for website in self:
            journal = website.simplified_invoice_journal_id
            if journal and journal.company_id == website.company_id:
                continue
            Journal = self.env['account.journal'].sudo()
            chart_template = self.env['account.chart.template'].with_company(website.company_id)
            website.simplified_invoice_journal_id = (
                chart_template.ref('simplified_journal', raise_if_not_found=False)
                or Journal.search([
                    *Journal._check_company_domain(website.company_id),
                    ('type', '=', 'sale'),
                    ('code', '=', 'SINV'),
                ], limit=1)
            )
