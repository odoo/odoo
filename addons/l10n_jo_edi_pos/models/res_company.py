from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_jo_edi_pos_enabled = fields.Boolean()
    l10n_jo_edi_pos_testing_mode = fields.Boolean()

    @api.model
    def _load_pos_data_fields(self, config_id):
        params = super()._load_pos_data_fields(config_id)
        if self.env.company.account_fiscal_country_id.code == 'JO':
            params += ["l10n_jo_edi_pos_enabled"]
        return params
