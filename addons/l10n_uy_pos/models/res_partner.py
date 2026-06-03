from odoo import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _get_pos_partner_view_id(self):
        if self.env.company.country_id.code == 'UY':
            return self.env.ref('base.view_partner_form').id
        return super()._get_pos_partner_view_id()
