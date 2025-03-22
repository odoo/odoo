from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _pos_data_process(self, loaded_data):
        res = super()._pos_data_process(loaded_data)
        if self.company_id.country_code == 'BE':
            intracom_fpos = self.env.ref(f"l10n_be.{self.env.company.id}_fiscal_position_template_3", False)
            if intracom_fpos:
                loaded_data['intracom_tax_ids'] = intracom_fpos.tax_ids.tax_dest_id.ids
        return res
