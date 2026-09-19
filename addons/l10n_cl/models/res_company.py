from odoo import models


class ResCompany(models.Model):
    _inherit = "res.company"
    _inherits_sudo_fields = ("l10n_cl_activity_description",)

    def _localization_use_documents(self):
        """Chilean localization use documents"""
        self.check_singleton()
        return (
            self.account_config_id.chart_template == "cl"
            or super()._localization_use_documents()
        )
