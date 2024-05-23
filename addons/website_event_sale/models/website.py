from odoo import models
from odoo.osv import expression


class Website(models.Model):
    _inherit = 'website'

    def sale_product_domain(self):
        # remove product event from the website content grid and list view (not removed in detail view)
        return expression.AND([
            super().sale_product_domain(),
            [('service_tracking', '!=', 'event')],
        ])
