from odoo import fields, models

TAX_SYSTEM = [
    ("RF01", "[RF01] Ordinario"),
    ("RF02", "[RF02] Contribuenti minimi (art.1, c.96-117, L. 244/07)"),
    (
        "RF04",
        "[RF04] Agricoltura e attività connesse e pesca (artt.34 e 34-bis, DPR 633/72)",
    ),
    ("RF05", "[RF05] Vendita sali e tabacchi (art.74, c.1, DPR. 633/72)"),
    ("RF06", "[RF06] Commercio fiammiferi (art.74, c.1, DPR  633/72)"),
    ("RF07", "[RF07] Editoria (art.74, c.1, DPR  633/72)"),
    ("RF08", "[RF08] Gestione servizi telefonia pubblica (art.74, c.1, DPR 633/72)"),
    (
        "RF09",
        "[RF09] Rivendita documenti di trasporto pubblico e di sosta (art.74, c.1, DPR  633/72)",
    ),
    (
        "RF10",
        "[RF10] Intrattenimenti, giochi e altre attività di cui alla tariffa allegata al DPR 640/72 (art.74, c.6, DPR 633/72)",
    ),
    ("RF11", "[RF11] Agenzie viaggi e turismo (art.74-ter, DPR 633/72)"),
    ("RF12", "[RF12] Agriturismo (art.5, c.2, L. 413/91)"),
    ("RF13", "[RF13] Vendite a domicilio (art.25-bis, c.6, DPR  600/73)"),
    (
        "RF14",
        "[RF14] Rivendita beni usati, oggetti d’arte, d’antiquariato o da collezione (art.36, DL 41/95)",
    ),
    (
        "RF15",
        "[RF15] Agenzie di vendite all’asta di oggetti d’arte, antiquariato o da collezione (art.40-bis, DL 41/95)",
    ),
    ("RF16", "[RF16] IVA per cassa P.A. (art.6, c.5, DPR 633/72)"),
    ("RF17", "[RF17] IVA per cassa (art. 32-bis, DL 83/2012)"),
    ("RF18", "[RF18] Altro"),
    ("RF19", "[RF19] Regime forfettario (art.1, c.54-89, L. 190/2014)"),
]


class ResCompany(models.Model):
    _inherit = "res.company"
    _inherits_sudo_fields = ("l10n_it_codice_fiscale",)

    l10n_it_edi_config_id = fields.Many2one(
        comodel_name="l10n_it_edi.config",
        compute="_compute_l10n_it_edi_config_id",
        search="_search_l10n_it_edi_config_id",
    )

    l10n_it_eco_index_liquidation_state = fields.Selection(
        related="l10n_it_edi_config_id.l10n_it_eco_index_liquidation_state",
        readonly=False,
    )
    l10n_it_eco_index_number = fields.Char(
        related="l10n_it_edi_config_id.l10n_it_eco_index_number",
        readonly=False,
    )
    l10n_it_eco_index_share_capital = fields.Float(
        related="l10n_it_edi_config_id.l10n_it_eco_index_share_capital",
        readonly=False,
    )
    l10n_it_eco_index_sole_shareholder = fields.Selection(
        related="l10n_it_edi_config_id.l10n_it_eco_index_sole_shareholder",
        readonly=False,
    )
    l10n_it_has_eco_index = fields.Boolean(
        related="l10n_it_edi_config_id.l10n_it_has_eco_index",
        readonly=False,
    )
    l10n_it_has_tax_representative = fields.Boolean(
        related="l10n_it_edi_config_id.l10n_it_has_tax_representative",
        readonly=False,
    )
    l10n_it_tax_system = fields.Selection(
        related="l10n_it_edi_config_id.l10n_it_tax_system",
        readonly=False,
    )

    l10n_it_eco_index_office = fields.Many2one(
        related="l10n_it_edi_config_id.l10n_it_eco_index_office",
        readonly=False,
    )
    l10n_it_tax_representative_partner_id = fields.Many2one(
        related="l10n_it_edi_config_id.l10n_it_tax_representative_partner_id",
        readonly=False,
    )

    def _search_l10n_it_edi_config_id(self, operator, value):
        return self._search_config_link("l10n_it_edi.config", operator, value)

    def _compute_l10n_it_edi_config_id(self):
        configs = self.env["l10n_it_edi.config"]._for_each(self)
        by_company = dict(zip(configs.mapped("company_id").ids, configs, strict=True))
        for company in self:
            company.l10n_it_edi_config_id = by_company.get(company.id, False)

    def _l10n_it_edi_export_check(self):
        checks = {
            "company_vat_codice_fiscale_missing": {
                "fields": [("vat", "l10n_it_codice_fiscale")],
                "message": self.env._(
                    "Company/ies should have a VAT number or Codice Fiscale."
                ),
            },
            "company_address_missing": {
                "fields": [("street", "street2"), ("zip",), ("city",), ("country_id",)],
                "message": self.env._(
                    "Company/ies should have a complete address, verify their Street, City, Zipcode and Country."
                ),
            },
            "company_l10n_it_tax_system_missing": {
                "fields": [("l10n_it_tax_system",)],
                "message": self.env._("Company/ies should have a Tax System"),
            },
        }
        errors = {}
        for key, check in checks.items():
            for fields_tuple in check.pop("fields"):
                if invalid_records := self.filtered(
                    lambda record, fields_tuple=fields_tuple: (
                        not any(
                            record._config_owner_of(field)[field]
                            for field in fields_tuple
                        )
                    )
                ):
                    errors[f"l10n_it_edi_{key}"] = {
                        "message": check["message"],
                        "action_text": self.env._("View Company/ies"),
                        "action": invalid_records._get_records_action(
                            name=self.env._("Check Company Data")
                        ),
                    }
        if self.filtered(
            lambda x: not x.l10n_it_edi_config_id.l10n_it_edi_proxy_user_id
        ):
            errors["l10n_it_edi_settings_l10n_it_edi_proxy_user_id"] = {
                "message": self.env._(
                    "You need to set the Codice Fiscale on your company."
                ),
                "action_text": self.env._("View Company/ies"),
                "action": self._get_records_action(
                    name=self.env._("Check Company Data")
                ),
            }
        return errors

    def _l10n_it_get_edi_company(self):
        self.check_singleton()
        if (
            self.root_id.id != self.id
            and self.l10n_it_codice_fiscale == self.root_id.l10n_it_codice_fiscale
            and self.vat == self.root_id.vat
        ):
            return self.root_id
        else:
            return self
