from odoo import models


class ResPartner(models.Model):

    _inherit = 'res.partner'

    def _get_pos_required_partners(self, config):
        partner_ids = super()._get_pos_required_partners(config)
        if self.env.company.country_id.code == 'ES':
            partner_ids = partner_ids.union({config.simplified_partner_id.id})
        return partner_ids
