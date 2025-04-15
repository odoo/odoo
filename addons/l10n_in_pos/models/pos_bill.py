from odoo import api, models
from odoo.fields import Domain


class PosBill(models.Model):
    _inherit = "pos.bill"

    @api.model
    def _load_pos_data_domain(self, data):
        domain = super()._load_pos_data_domain(data)

        if self.env.company.country_code == 'IN':
            domain = Domain.AND([domain, [('value', '>=', 1.0), ('value', '<=', 2000.0)]])

        return domain
