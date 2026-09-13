from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_es_sii_certificate_id = fields.Many2one(
        string="Certificate (SII)",
        store=True,
        readonly=False,
        comodel_name="certificate.certificate",
        compute="_compute_l10n_es_sii_certificate_id",
    )
    l10n_es_sii_certificate_ids = fields.One2many(
        comodel_name="certificate.certificate",
        inverse_name="company_id",
        domain=[("scope", "=", "sii")],
    )
    l10n_es_sii_tax_agency = fields.Selection(
        string="Tax Agency for SII",
        selection=[
            ("aeat", "Agencia Tributaria española"),
            ("gipuzkoa", "Hacienda Foral de Gipuzkoa"),
            ("bizkaia", "Hacienda Foral de Bizkaia"),
        ],
        default=False,
    )
    l10n_es_sii_test_env = fields.Boolean(
        string="SII Test Mode",
        help="Use the test environment for SII",
        default=True,
    )

    @api.depends("country_id", "l10n_es_sii_certificate_ids")
    def _compute_l10n_es_sii_certificate_id(self):
        for company in self:
            if company.country_code == "ES":
                company.l10n_es_sii_certificate_id = self.env[  # noqa: E8507 - one lookup per company, on its own certificates
                    "certificate.certificate"
                ].search(
                    [
                        ("company_id", "=", company.id),
                        ("is_valid", "=", True),
                        ("scope", "=", "sii"),
                    ],
                    order="date_end desc",
                    limit=1,
                )
            else:
                company.l10n_es_sii_certificate_id = False
