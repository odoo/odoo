from odoo import models


class ResCompany(models.Model):
    _inherit = "res.company"

    def _localization_use_documents(self):
        # OVERRIDE
        self.check_singleton()
        return (
            self.account_config_id.chart_template == "pe"
            or super()._localization_use_documents()
        )

    def _is_latam(self):
        return super()._is_latam() or self.country_code == "PE"
