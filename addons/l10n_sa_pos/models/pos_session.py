# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_res_partner(self):
        params = super()._loader_params_res_partner()
        if self.company_id.country_id.code == 'SA':
            params['search_params']['fields'].append('company_type')
        return params
