from odoo import fields, models
from odoo.addons.l10n_tr_nilvera.lib.nilvera_client import NilveraClient


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_tr_nilvera_api_key = fields.Char(string="Nilvera API key", groups='base.group_system')
    l10n_tr_nilvera_environment = fields.Selection(
        string="Nilvera Environment",
        selection=[
            ('sandbox', "Sandbox"),
            ('production', "Production"),
        ],
        required=True,
        default='sandbox',
    )
    l10n_tr_nilvera_purchase_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string="Nilvera Purchase Journal",
        domain=[('type', '=', 'purchase')],
        store=True,
        compute='_compute_l10n_tr_nilvera_purchase_journal_id',
        inverse='_inverse_l10n_tr_nilvera_purchase_journal_id',
    )

    def _compute_l10n_tr_nilvera_purchase_journal_id(self):
        for company in self:
            if not company.l10n_tr_nilvera_purchase_journal_id:
                company.l10n_tr_nilvera_purchase_journal_id = self.env['account.journal'].search([
                    *self.env['account.journal']._check_company_domain(company),
                    ('type', '=', 'purchase'),
                ], limit=1)
                company.l10n_tr_nilvera_purchase_journal_id.is_nilvera_journal = True
            else:
                company.l10n_tr_nilvera_purchase_journal_id = company.l10n_tr_nilvera_purchase_journal_id

    def _inverse_l10n_tr_nilvera_purchase_journal_id(self):
        for company in self:
            # This avoids having 2 or more journals from the same company with
            # `is_nilvera_journal` set to True (which could occur after changes).
            journals_to_reset = self.env['account.journal'].search([
                ('company_id', '=', company.id),
                ('is_nilvera_journal', '=', True),
            ])
            journals_to_reset.is_nilvera_journal = False
            company.l10n_tr_nilvera_purchase_journal_id.is_nilvera_journal = True

    def _get_nilvera_client(self):
        self.ensure_one()
        client = NilveraClient(
            environment=self.l10n_tr_nilvera_environment,
            api_key=self.l10n_tr_nilvera_api_key,
        )
        return client
