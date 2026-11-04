from odoo import api, fields, models
from odoo.exceptions import UserError


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_ro_edi_anaf_imported_inv_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string="Select journal for SPV imported bills",
        domain="[('type', '=', 'purchase')]",
        compute="_compute_l10n_ro_edi_anaf_imported_inv_journal",
        store=True,
        readonly=False,
    )

    @api.depends('country_code')
    def _compute_l10n_ro_edi_anaf_imported_inv_journal(self):
        self.l10n_ro_edi_anaf_imported_inv_journal_id = False
        for company in self:
            if company.country_code == 'RO':
                company.l10n_ro_edi_anaf_imported_inv_journal_id = self.env['account.journal'].search([
                    ('type', '=', 'purchase'),
                    *self.env['account.journal']._check_company_domain(company.id),
                ], limit=1)

    def _cron_l10n_ro_edi_synchronize_invoices(self):
        """
        This CRON method will be run every 24 hours to synchronize the invoices and the bills with the ANAF
        """
        ro_companies = self.env['res.company'].sudo().search([
            ('l10n_ro_edi_refresh_token', '!=', False),
            ('l10n_ro_edi_client_id', '!=', False),
            ('l10n_ro_edi_client_secret', '!=', False),
        ])
        for company in ro_companies:
            try:
                self.env['account.move'].with_company(company)._l10n_ro_edi_fetch_invoices()
            except UserError as e:
                self._l10n_ro_edi_log_message(
                    message=f'{company.id}\n{e}',
                    func='_cron_l10n_ro_edi_synchronize_invoices',
                )
