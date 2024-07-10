from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def load_data(self, models_to_load, only_data=False):
        response = super().load_data(models_to_load, only_data)
        if self.company_id.country_code == 'BE':
            intracom_fpos = self.env["account.chart.template"].with_company(
                self.company_id).ref("fiscal_position_template_3", False)
            response['custom']['intracom_tax_ids'] = intracom_fpos.tax_ids.tax_dest_id.ids
        return response
