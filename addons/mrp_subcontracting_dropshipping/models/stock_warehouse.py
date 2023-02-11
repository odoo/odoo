# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    subcontracting_dropshipping_to_resupply = fields.Boolean(
        'Dropship Subcontractors', default=True,
        help="Dropship subcontractors with components")

    subcontracting_dropshipping_pull_id = fields.Many2one(
        'stock.rule', 'Subcontracting-Dropshipping MTS Rule'
    )

    def _get_global_route_rules_values(self):
        rules = super()._get_global_route_rules_values()
        subcontract_location_id = self._get_subcontracting_location()
        production_location_id = self._get_production_location()
        rules.update({
            'subcontracting_dropshipping_pull_id': {
                'depends': ['subcontracting_dropshipping_to_resupply'],
                'create_values': {
                    'procure_method': 'make_to_order',
                    'company_id': self.company_id.id,
                    'action': 'pull',
                    'auto': 'manual',
                    'route_id': self._find_global_route('mrp_subcontracting_dropshipping.route_subcontracting_dropshipping',
                                                        _('Dropship Subcontractor on Order')).id,
                    'name': self._format_rulename(subcontract_location_id, production_location_id, False),
                    'location_id': production_location_id.id,
                    'location_src_id': subcontract_location_id.id,
                    'picking_type_id': self.subcontracting_type_id.id
                },
                'update_values': {
                    'active': self.subcontracting_dropshipping_to_resupply
                }
            },
        })
        return rules
