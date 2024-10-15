from odoo import models, api
from odoo.osv.expression import OR
from odoo.addons import point_of_sale


class AccountFiscalPosition(point_of_sale.AccountFiscalPosition):

    @api.model
    def _load_pos_data_domain(self, data):
        params = super()._load_pos_data_domain(data)
        params = OR([params, [('id', '=', data['pos.config']['data'][0]['takeaway_fp_id'])]])
        return params
