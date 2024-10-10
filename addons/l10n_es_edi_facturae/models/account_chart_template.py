from odoo import models


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    def _pre_reload_data(self, template_code, company, template_data):
        super()._pre_reload_data(template_code, company, template_data)
        self.env['account.tax']._update_l10n_es_edi_facturae_tax_type()
