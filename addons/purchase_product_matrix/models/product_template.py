from odoo import models, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """
        Returns the products in a prioritized sequence for the purchase order line product selection.
        First, it lists all products that have been invoiced to the specified customer,
        sorted from the most recent to the oldest invoice date.
        Afterward, it includes the remaining products in their default order of display.
        """
        args = args or []
        if not name and self.env.context.get('partner_id') and self.env.context.get('is_purchase'):
            prioritized_product_templates = self.get_prioritized_product('purchase')
            remaining_product_templates = self.search(
                [('id', 'not in', prioritized_product_templates.ids)] + args,
                limit=limit - len(prioritized_product_templates)
            )

            product_templates = prioritized_product_templates + remaining_product_templates
            return [(product_template.id, product_template.display_name) for product_template in product_templates]
        else:
            return super().name_search(name, args, operator, limit)
