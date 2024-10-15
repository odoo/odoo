from odoo import models, api
from odoo.addons import account, point_of_sale


class AccountFiscalPositionTax(account.AccountFiscalPositionTax, point_of_sale.PosLoadMixin):

    @api.model
    def _load_pos_data_domain(self, data):
        return [('position_id', 'in', [fpos['id'] for fpos in data['account.fiscal.position']['data']])]
