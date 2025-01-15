from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _load_pos_data(self, data):
        data = super()._load_pos_data(data)
        if self.env.company.country_code == 'BE':
            intracom_fpos = self.env["account.chart.template"].with_company(self.company_id).ref("fiscal_position_template_3", False)
            if intracom_fpos:
                data['data'][0]['_intracom_tax_ids'] = intracom_fpos.tax_ids.tax_dest_id.ids
        return data
