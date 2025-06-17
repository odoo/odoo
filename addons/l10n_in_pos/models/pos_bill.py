from odoo import api, models
from odoo.osv import expression
from odoo.osv.expression import AND

class PosBill(models.Model):
    _inherit = "pos.bill"

    @api.model
    def _load_pos_data_domain(self, data, config):
        domain = super()._load_pos_data_domain(data, config)

        if self.env.company.country_code == 'IN':
            domain = expression.AND([domain, [('value', '>=', 1.0), ('value', '<=', 2000.0)]])

        return domain
