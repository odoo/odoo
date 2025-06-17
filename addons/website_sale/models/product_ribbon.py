# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models

from odoo.exceptions import ValidationError


class ProductRibbon(models.Model):
    _name = 'product.ribbon'
    _description = "Product ribbon"
    _order = 'sequence ASC'

    name = fields.Char(string="Ribbon Name", required=True, translate=True, size=20)
    sequence = fields.Integer(default=10)
    bg_color = fields.Char(string="Background Color", required=True, default='#000000')
    text_color = fields.Char(string="Text Color", required=True, default='#FFFFFF')
    position = fields.Selection(
        string='Position',
        selection=[('left', "Left"), ('right', "Right")],
        required=True,
        default='left',
    )
    style = fields.Selection(
        string="Style",
        selection=[('ribbon', "Ribbon"), ('tag', "Badge")],
        required=True,
        default='ribbon',
    )
    assign = fields.Selection(
        string="Assign",
        selection=[
            ('manual', "Manually"),
            ('sale', "on sale"),
            ('new', "when new"),
        ],
        required=True,
        default='manual',
        help=(
            "Defines how this ribbon is assigned to products:\n"
            "- Manually: You assign the ribbon manually to products.\n"
            "- Sale: Applied when the product is visibly on sale.\n"
            "- New: Applied based on the New period you will define.\n"
            "- Out Of Stock: Applied when the product is out of stock."
        ),
    )
    new_period = fields.Integer(default=30)

    @api.constrains('assign')
    def _check_assign(self):
        """
        Ensure only one ribbon exists per automatic assign type.
        This prevents duplicates, since automatic assignment logic always uses the first ribbon
        with a given assign value.
        """
        for ribbon in self:
            if ribbon.assign != 'manual':
                existing_ribbons = self.search([
                    ('id', '!=', ribbon.id),
                    ('assign', '=', ribbon.assign)
                ], limit=1)
                if existing_ribbons:
                    raise ValidationError(
                        _(
                            "Only one ribbon with the assign %s is allowed.",
                            dict(self._fields['assign'].selection).get(ribbon.assign)
                        )
                    )

    def _get_css_classes(self):
        """
        Return the CSS classes for this ribbon based on style and position.
        rtype: str
        """
        css_classes = ""
        match self.style:
            case 'ribbon':
                css_classes += "o_wsale_ribbon"
            case 'tag':
                css_classes += "o_wsale_badge"

        match self.position:
            case 'left':
                css_classes += " o_left"
            case 'right':
                css_classes += " o_right"
        return css_classes

    def _get_applicable_ribbon(self, product, product_prices):
        """
        Returns the ribbon for which the product matches the criteria of automatic assignment.
        :param product.product product: The product to get the automatic ribbon for.
        :param function get_product_prices: A lazy loaded funciton to get product's pricing info
        :return: Ribbon for which given product matches the automatic assign criteria.
        :rtype: `product.ribbon` recordset.
        """
        for ribbon in self:
            # Check if a discount is applied to the product using a pricelist, comparison price, or
            # others.
            if (
                ribbon.assign == 'sale'
                and product_prices
                and (
                    # for /shop page
                    (
                        'base_price' in product_prices
                        and (product_prices['base_price'] > product_prices['price_reduce'])
                    )
                    # for /product page
                    or (
                        'compare_list_price' in product_prices
                        and product_prices['compare_list_price'] > product_prices['price']
                    )
                    or product_prices.get('has_discounted_price')
                )
            ):
                return ribbon

            # Check if the product is published within the ribbon's new period.
            if (
                ribbon.assign == 'new'
                and ribbon.new_period >= (fields.Datetime.today() - product.publish_date).days
            ):
                return ribbon

        return self.env['product.ribbon']
