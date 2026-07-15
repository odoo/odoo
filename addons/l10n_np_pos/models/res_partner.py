# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.fields import Domain


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _load_pos_data_domain(self, data, config):
        domain = super()._load_pos_data_domain(data, config)
        if config.l10n_np_default_customer and self.env.company.country_id.code == 'NP':
            return Domain.OR([domain, [('id', '=', config.l10n_np_default_customer.id)]])
        return domain
