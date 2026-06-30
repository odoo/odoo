from odoo import models, api


class PosConfig(models.Model):
    _inherit = 'pos.config'

    @api.model
    def _load_pos_data_read(self, records, config):
        read_records = super()._load_pos_data_read(records, config)
        if read_records and self.env.company.country_code == 'BE':
            intracom_fpos = self.env["account.chart.template"].with_company(self.company_id.root_id).sudo().ref("fiscal_position_template_3", False)
            if intracom_fpos:
                read_records[0]['_intracom_tax_ids'] = intracom_fpos.tax_ids.ids
        return read_records
