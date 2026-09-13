from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_cl_activity_description = fields.Char(
        related="partner_id.l10n_cl_activity_description",
        string="Company Activity Description",
        readonly=False,
    )

    def _localization_use_documents(self):
        """Chilean localization use documents"""
        self.check_singleton()
        return self.chart_template == "cl" or super()._localization_use_documents()
