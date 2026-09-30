# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ProductProduct(models.Model):
    _inherit = "product.product"

    product_catalog_product_is_in_repair = fields.Boolean(
        compute='_compute_product_is_in_repair',
        search='_search_product_is_in_repair',
    )

    def _compute_product_is_in_repair(self):
        # Just to enable the _search method
        self.product_catalog_product_is_in_repair = False

    def _search_product_is_in_repair(self, operator, value):
        if operator != 'in':
            return NotImplemented
        product_ids = self.env['repair.order'].search([
            ('id', 'in', [self.env.context.get('order_id', '')]),
        ]).move_ids.product_id.ids
        return [('id', 'in', product_ids)]

    def _count_returned_sn_products_domain(self, sn_lot, or_domains):
        or_domains.append([
                ('move_id.repair_line_type', 'in', ['remove', 'recycle']),
                ('location_dest_usage', '=', 'internal'),
        ])
        return super()._count_returned_sn_products_domain(sn_lot, or_domains)

    def _update_uom(self, to_uom_id):
        for uom, product, repairs in self.env['repair.order']._read_group(
            [('product_id', 'in', self.ids)],
            ['product_uom', 'product_id'],
            ['id:recordset'],
        ):
            if uom != product.product_tmpl_id.uom_id:
                raise UserError(_(
                'As other units of measure (ex : %(problem_uom)s) '
                'than %(uom)s have already been used for this product, the change of unit of measure can not be done.'
                'If you want to change it, please archive the product and create a new one.',
                problem_uom=uom.display_name, uom=product.product_tmpl_id.uom_id.display_name))
            repairs.product_uom = to_uom_id
        return super()._update_uom(to_uom_id)

class ProductTemplate(models.Model):
    _inherit = "product.template"

    service_tracking = fields.Selection(selection_add=[('repair', 'Repair Order')],
                                        ondelete={'repair': 'set default'})

    @api.model
    def _get_saleable_tracking_types(self):
        return super()._get_saleable_tracking_types() + ['repair']
