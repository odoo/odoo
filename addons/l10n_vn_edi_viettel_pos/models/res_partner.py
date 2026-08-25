# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api
from odoo.exceptions import UserError
from odoo.fields import Domain


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.ondelete(at_uninstall=False)
    def _vn_unlink_except_master_data(self):
        walk_in_customer = self.env.ref(
            'l10n_vn_edi_viettel_pos.partner_walk_in_customer', raise_if_not_found=False
        )
        if walk_in_customer and walk_in_customer in self:
            raise UserError(
                self.env._(
                    "Deleting the partner %s is not allowed because it is required by the Vietnam point of sale.",
                    walk_in_customer.display_name,
                )
            )

    @api.model
    def _load_pos_data_domain(self, data, config):
        # Make sure to always load the walk-in customer
        domain = super()._load_pos_data_domain(data, config)
        if self.env.company.country_id.code == "VN":
            walk_in_customer_id = self.env.ref('l10n_vn_edi_viettel_pos.partner_walk_in_customer', raise_if_not_found=False).id
            return Domain.OR([domain, [('id', '=', walk_in_customer_id)]])
        return domain
