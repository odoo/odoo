from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"
    _inherits_sudo_fields = (
        "l10n_br_ie_code",
        "l10n_br_im_code",
    )

    # ==== Business fields ====
    l10n_br_nire_code = fields.Char(
        string="NIRE",
        help="State Commercial Identification Number. Should contain 11 digits.",
    )

    def _localization_use_documents(self):
        self.check_singleton()
        return (
            self.account_config_id.chart_template == "br"
            or super()._localization_use_documents()
        )

    def _is_latam(self):
        return (
            super()._is_latam()
            or self.account_config_id.account_fiscal_country_id.code == "BR"
        )
