from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def _get_robots_directives(self):
        config = super()._get_robots_directives()

        allow_patterns = [
            '/cards/',
        ]

        config['*']['allow'] = config['*']['allow'] + allow_patterns

        return config
