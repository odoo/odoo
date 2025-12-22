from odoo import models


class ResCompany(models.Model):

    _inherit = "res.company"

    def _localization_use_documents(self):
        self.ensure_one()
        return self.chart_template == 'ec' or super()._localization_use_documents()
