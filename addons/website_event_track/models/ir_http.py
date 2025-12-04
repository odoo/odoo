from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def _get_robots_directives(self):
        config = super()._get_robots_directives()

        disallow_patterns = [
            '/event/*/track?tags=',
            '/event/*/track?*&tags=',
        ]

        config['*']['disallow'] = config['*']['disallow'] + disallow_patterns

        return config
