# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.osv import expression


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _make_mo_get_domain(self, procurement, bom):
        domain = super()._make_mo_get_domain(procurement, bom)
        return tuple(
            expression.AND([
                list(domain),
                expression.OR([
                    [('check_ids', '=', False)],
                    [('check_ids', 'not any', [('quality_state', '!=', 'none')])]
                ]),
                expression.OR([
                    [('workorder_ids', '=', False)],
                    [('workorder_ids', 'not any',
                        [
                            ('check_ids', '!=', False),
                            ('check_ids', 'any', [('quality_state', '!=', 'none')])
                        ]
                    )]
                ])
            ])
        )
