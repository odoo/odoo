import markupsafe

from odoo import api, fields, models


class L10nEsEdiTbaiConfig(models.Model):
    _name = "l10n_es_edi_tbai.config"
    _description = "A company's l10n es edi tbai configuration"
    _inherit = ["mixin.company.config"]

    l10n_es_tbai_certificate_id = fields.Many2one(
        comodel_name="certificate.certificate",
        string="Certificate (TicketBAI)",
        compute="_compute_l10n_es_tbai_certificate_id",
        store=True,
        readonly=False,
    )
    l10n_es_tbai_tax_agency = fields.Selection(
        selection=[
            ("araba", "Hacienda Foral de Araba"),  # es-vi (region code)
            ("bizkaia", "Hacienda Foral de Bizkaia"),  # es-bi
            ("gipuzkoa", "Hacienda Foral de Gipuzkoa"),  # es-ss
        ],
        string="Tax Agency for TBAI",
    )
    l10n_es_tbai_license_html = fields.Html(
        string="TicketBAI license",
        compute="_compute_l10n_es_tbai_license_html",
    )
    l10n_es_tbai_chain_sequence_id = fields.Many2one(
        comodel_name="ir.sequence",
        string="TicketBai account.move chain sequence",
        copy=False,
        readonly=True,
    )
    l10n_es_tbai_test_env = fields.Boolean(
        string="TBAI Test Mode",
        default=True,
        help="Use the test environment for TicketBAI",
    )
    l10n_es_tbai_is_enabled = fields.Boolean(compute="_compute_l10n_es_tbai_is_enabled")

    @api.depends("company_id.country_id", "l10n_es_tbai_tax_agency")
    def _compute_l10n_es_tbai_is_enabled(self):
        for config in self:
            config.l10n_es_tbai_is_enabled = (
                config.company_id.country_code == "ES"
                and config.l10n_es_tbai_tax_agency
            )

    @api.depends("company_id.country_id", "company_id.l10n_es_tbai_certificate_ids")
    def _compute_l10n_es_tbai_certificate_id(self):
        for config in self:
            if config.company_id.country_code == "ES":
                config.l10n_es_tbai_certificate_id = self.env[  # noqa: E8507 - one lookup per configuration, on its company's certificates
                    "certificate.certificate"
                ].search(
                    [
                        ("company_id", "=", config.company_id.id),
                        ("is_valid", "=", True),
                        ("scope", "=", "tbai"),
                    ],
                    order="date_end desc",
                    limit=1,
                )
            else:
                config.l10n_es_tbai_certificate_id = False

    @api.depends(
        "company_id.country_id", "l10n_es_tbai_test_env", "l10n_es_tbai_tax_agency"
    )
    def _compute_l10n_es_tbai_license_html(self):
        for config in self:
            license_dict = config.company_id._get_l10n_es_tbai_license_dict()
            if license_dict:
                license_dict.update(
                    {
                        "tr_nif": self.env._("Licence NIF"),
                        "tr_number": self.env._("Licence number"),
                        "tr_name": self.env._("Software name"),
                        "tr_version": self.env._("Software version"),
                    }
                )
                config.l10n_es_tbai_license_html = markupsafe.Markup("""
<strong>{license_name}</strong><br/>
<p>
<strong>{tr_nif}: </strong>{license_nif}<br/>
<strong>{tr_number}: </strong>{license_number}<br/>
<strong>{tr_name}: </strong>{software_name}<br/>
<strong>{tr_version}: </strong>{software_version}<br/>
</p>""").format(**license_dict)
            else:
                config.l10n_es_tbai_license_html = markupsafe.Markup("""
<strong>{tr_no_license}</strong>""").format(
                    tr_no_license=self.env._("TicketBAI is not configured")
                )
