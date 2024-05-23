# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.osv import expression


class Website(models.Model):
    _inherit = 'website'

    def sale_product_domain(self):
        return expression.AND([
            super().sale_product_domain(),
            [('service_tracking', '!=', 'event_booth')],
        ])
