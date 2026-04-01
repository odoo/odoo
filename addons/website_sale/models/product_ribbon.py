# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductRibbon(models.Model):
    _name = 'product.ribbon'
    _description = "Product ribbon"
    _order = 'sequence ASC, id'

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
        help=(
            "Defines the display style:\n"
            "- Ribbon: Shows a ribbon banner on the product image.\n"
            "- Badge: Shows a small badge label on the product image."
        ),
    )
    assign = fields.Selection(
        string="Assign",
        selection=[
            ('manual', "Manually"),
            ('sale', "On Sale"),
            ('new', "When New"),
        ],
        required=True,
        default='manual',
        help=(
            "Defines how this ribbon is assigned to products:\n"
            "- Manually: You assign the ribbon manually to products.\n"
            "- Sale: Applied when the product is visibly on sale.\n"
            "- New: Applied based on the New period you will define.\n"
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

    def _is_applicable_for(self, product, price_data):
        """Return whether the product matches the criteria of the ribbon automatic assignment.

        :param product.product product: the displayed product
        :param dict price_data: price information for the given product
            (sales price for shop page, combination information for product page)

        :return: Whether the ribbon matches the given product and price.
        :rtype: bool
        """
        self.ensure_one()

        # Check if a discount is applied to the product using a pricelist, comparison price, or
        # others.
        if (  # noqa: SIM103
            self.assign == 'sale'
            and price_data
            and (
                # for /shop page
                (
                    'base_price' in price_data
                    and (price_data['base_price'] > price_data['price_reduce'])
                )
                # for /product page
                or (
                    'compare_list_price' in price_data
                    and price_data['compare_list_price'] > price_data['price']
                )
                or price_data.get('has_discounted_price')
            )
        ):
            return True
        # Check if the product is published within the ribbon's new period.
        if (  # noqa: SIM103
            self.assign == 'new'
            and self.new_period >= (fields.Datetime.today() - product.publish_date).days
        ):
            return True
        return False
