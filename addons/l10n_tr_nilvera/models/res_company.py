from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"
    _CREDENTIAL_FIELDS = {
        "l10n_tr_nilvera_api_key": "l10n_tr_nilvera_api_key",
    }

    l10n_tr_nilvera_api_key = fields.Char(
        string="Nilvera API key",
        compute="_compute_credential_doors",
        inverse="_inverse_credential_doors",
        groups="base.group_system",
    )
    l10n_tr_nilvera_use_test_env = fields.Boolean(
        string="Use testing environment",
        default=True,
        required=True,
    )
    l10n_tr_nilvera_purchase_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Nilvera Purchase Journal",
        compute="_compute_l10n_tr_nilvera_purchase_journal_id",
        inverse="_inverse_l10n_tr_nilvera_purchase_journal_id",
        store=True,
        domain=[("type", "=", "purchase")],
    )

    def _compute_l10n_tr_nilvera_purchase_journal_id(self):
        purchase_journals = self.env["account.journal"].search(
            [("type", "=", "purchase")]
        )
        for company in self:
            if not company.l10n_tr_nilvera_purchase_journal_id:
                company.l10n_tr_nilvera_purchase_journal_id = (
                    purchase_journals.filtered_domain(
                        self.env["account.journal"]._check_company_domain(company)
                    )[:1]
                )
                company.l10n_tr_nilvera_purchase_journal_id.is_nilvera_journal = True

    def _inverse_l10n_tr_nilvera_purchase_journal_id(self):
        # dict(company: journals)
        journals_to_reset_grouped = (
            self.env["account.journal"]
            .search(
                [
                    ("company_id", "in", self.ids),
                    ("is_nilvera_journal", "=", True),
                ]
            )
            .grouped("company_id")
        )
        for company in self:
            # This avoids having 2 or more journals from the same company with
            # `is_nilvera_journal` set to True (which could occur after changes).
            if journals_to_reset := journals_to_reset_grouped.get(company):
                journals_to_reset.is_nilvera_journal = False
            company.l10n_tr_nilvera_purchase_journal_id.is_nilvera_journal = True
