# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api
from odoo.osv import expression


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _load_pos_data_domain(self, data):
        # Make sure to always load the walk-in customer
        domain = super()._load_pos_data_domain(data)
        if self.env.company.country_id.code == "VN":
            walk_in_customer_id = self.env.ref('l10n_vn_edi_viettel_pos.partner_walk_in_customer', raise_if_not_found=False).id
            return expression.OR([domain, [('id', '=', walk_in_customer_id)]])
        return domain
