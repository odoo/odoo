from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def _get_robots_directives(self):
        config = super()._get_robots_directives()

        disallow_patterns = [
            '/event/*/exhibitors?countries=',
            '/event/*/exhibitors?*&countries=',

            '/event/*/exhibitors?sponsorships=',
            '/event/*/exhibitors?*&sponsorships=',
        ]

        config['*']['disallow'] = config['*']['disallow'] + disallow_patterns

        return config
