# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductKitLine(models.Model):
    _name = 'product.kit.line'
    _description = "Kit Component Line"
    _order = 'sequence, id'
    _check_company_auto = True

    product_tmpl_id = fields.Many2one(
        comodel_name='product.template',
        string="Kit Product",
        ondelete='cascade',
        required=True,
        index=True,
    )
    company_id = fields.Many2one(related='product_tmpl_id.company_id', store=True, precompute=True)
    sequence = fields.Integer(default=10)
    product_id = fields.Many2one(
        comodel_name='product.product',
        string="Component",
        domain=[('type', '!=', 'kit')],
        required=True,
        check_company=True,
        index=True,
    )
    product_qty = fields.Float(
        string="Quantity",
        required=True,
        default=1.0,
        digits='Product Unit of Measure',
    )
    uom_id = fields.Many2one(
        comodel_name='uom.uom',
        string="Unit of Measure",
        required=True,
    )
    price_ratio = fields.Float(
        string="Price Ratio (%)",
        digits=0,
        default=0.0,
        help="Percentage of the kit's sale price attributed to this component. "
             "The sum of all components' price ratios should equal 100.",
    )

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id

    @api.constrains('product_id')
    def _check_product_id_not_kit(self):
        if any(line.product_id.type == 'kit' for line in self):
            raise ValidationError(_("A kit component cannot itself be a kit."))
