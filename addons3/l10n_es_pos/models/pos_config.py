from odoo import _, api, fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    def _default_sinv_journal_id(self):
        return self.env['account.journal'].search([
            *self.env['account.journal']._check_company_domain(self.env.company),
            ('type', '=', 'sale'),
            ('code', '=', 'SINV'),
        ], limit=1)

    is_spanish = fields.Boolean(string="Company located in Spain", compute="_compute_is_spanish")
    l10n_es_simplified_invoice_limit = fields.Float(
        string="Simplified Invoice limit amount",
        help="Over this amount is not legally possible to create a simplified invoice",
        default=400,
    )
    l10n_es_simplified_invoice_journal_id = fields.Many2one(
        comodel_name='account.journal',
        domain="[('type', '=', 'sale')]",
        check_company=True,
        default=_default_sinv_journal_id,
    )
    simplified_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Simplified invoice partner",
        compute="_compute_simplified_partner_id",
    )

    @api.depends("company_id")
    def _compute_is_spanish(self):
        for pos in self:
            pos.is_spanish = pos.company_id.country_code == "ES"

    def _compute_simplified_partner_id(self):
        for config in self:
            config.simplified_partner_id = self.env.ref("l10n_es.partner_simplified").id

    def get_limited_partners_loading(self):
        # this function normally returns 100 partners, but we have to make sure that
        # the simplified partner is also loaded
        res = super().get_limited_partners_loading()
        if (self.simplified_partner_id.id,) not in res:
            res.append((self.simplified_partner_id.id,))
        return res

    def setup_defaults(self, company):
        # EXTENDS point_of_sale
        super().setup_defaults(company)
        if company.chart_template.startswith('es_'):
            sinv_journal = self.env['account.journal'].search([
                *self.env['account.journal']._check_company_domain(company),
                ('type', '=', 'sale'),
                ('code', '=', 'SINV'),
            ])
            if not sinv_journal:
                income_account = self.env.ref(f'account.{company.id}_account_common_7000', raise_if_not_found=False)
                sinv_journal = self.env['account.journal'].create({
                    'type': 'sale',
                    'name': _('Simplified Invoices'),
                    'code': 'SINV',
                    'default_account_id': income_account.id if income_account else False,
                    'company_id': company.id,
                    'sequence': 30
                })
            for pos_config in self.filtered(lambda config: config.company_id == company):
                if not pos_config.l10n_es_simplified_invoice_journal_id:
                    pos_config.l10n_es_simplified_invoice_journal_id = sinv_journal.id
