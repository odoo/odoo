# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons import point_of_sale


class PosSession(point_of_sale.PosSession):

    def _loader_params_pos_payment_method(self):
        result = super()._loader_params_pos_payment_method()
        result['search_params']['fields'].append('mp_id_point_smart')
        return result
