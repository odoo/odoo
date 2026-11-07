# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockPackage(models.Model):
    _inherit = "stock.package"

    package_carrier_type = fields.Selection(related='package_type_id.package_carrier_type')

    def _pre_put_in_pack_hook(self, package_id=False, package_type_id=False, package_name=False, from_package_wizard=False):
        res = super()._pre_put_in_pack_hook(package_id, package_type_id, package_name, from_package_wizard)
        move_lines = self.move_line_ids
        if res and move_lines.carrier_id:
            if self.env.context.get('picking_id'):
                move_lines = move_lines.filtered(lambda ml: ml.picking_id.id == self.env.context['picking_id'])

            context = res.get('context', {})
            context['default_package_carrier_type'] = move_lines._get_package_carrier_type_for_pack()
            res['context'] = context
        return res

    def _post_put_in_pack_hook(self):
        res = super()._post_put_in_pack_hook()
        weight = self.env.context.get('weight')
        if weight:
            res.shipping_weight = weight
        return res
