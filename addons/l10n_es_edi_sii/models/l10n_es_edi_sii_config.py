from odoo import api, fields, models


class L10nEsEdiSiiConfig(models.Model):
    _name = "l10n_es_edi_sii.config"
    _description = "A company's l10n es edi sii configuration"
    _inherit = ["mixin.company.config"]

    l10n_es_sii_certificate_id = fields.Many2one(
        comodel_name="certificate.certificate",
        string="Certificate (SII)",
        compute="_compute_l10n_es_sii_certificate_id",
        store=True,
        readonly=False,
    )
    l10n_es_sii_tax_agency = fields.Selection(
        selection=[
            ("aeat", "Agencia Tributaria española"),
            ("gipuzkoa", "Hacienda Foral de Gipuzkoa"),
            ("bizkaia", "Hacienda Foral de Bizkaia"),
        ],
        string="Tax Agency for SII",
        default=False,
    )
    l10n_es_sii_test_env = fields.Boolean(
        string="SII Test Mode",
        default=True,
        help="Use the test environment for SII",
    )

    @api.depends("company_id.country_id", "company_id.l10n_es_sii_certificate_ids")
    def _compute_l10n_es_sii_certificate_id(self):
        for config in self:
            if config.company_id.country_code == "ES":
                config.l10n_es_sii_certificate_id = self.env[  # noqa: E8507 - one lookup per configuration, on its company's certificates
                    "certificate.certificate"
                ].search(
                    [
                        ("company_id", "=", config.company_id.id),
                        ("is_valid", "=", True),
                        ("scope", "=", "sii"),
                    ],
                    order="date_end desc",
                    limit=1,
                )
            else:
                config.l10n_es_sii_certificate_id = False
