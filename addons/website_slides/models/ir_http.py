from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def _get_robots_directives(self):
        config = super()._get_robots_directives()

        disallow_patterns = [
            '/slides/all/tag/*,*',
        ]

        config['*']['disallow'] = config['*']['disallow'] + disallow_patterns

        return config
