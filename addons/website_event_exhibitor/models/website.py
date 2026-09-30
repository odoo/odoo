from odoo import models


class Website(models.Model):
    _inherit = "website"

    def _search_get_details(self, search_type, order, options):
        result = super()._search_get_details(search_type, order, options)
        if search_type in ['sponsor', 'all'] and options.get('event'):
            result.append(self.env['event.sponsor']._search_get_detail(self, order, options))
        return result
