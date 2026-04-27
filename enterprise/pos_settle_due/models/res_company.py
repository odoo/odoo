# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def _load_pos_data_fields(self, config_id):
        params = super()._load_pos_data_fields(config_id)
        if self.env.user.has_group('account.group_account_readonly'):
            params += ['account_use_credit_limit']
        return params
