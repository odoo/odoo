from odoo import fields, models
from collections import defaultdict
from .pos_urban_piper_request import UrbanPiperClient


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    urbanpiper_pos_config_ids = fields.Many2many(
        'pos.config',
        string='Available on Food Delivery',
        help='Check this if the product is available for food delivery.',
        domain="[('urbanpiper_store_identifier', '!=', False), ('module_pos_urban_piper', '=', True)]",
    )
    urbanpiper_meal_type = fields.Selection([
        ('1', 'Vegetarian'),
        ('2', 'Non-Vegetarian'),
        ('3', 'Eggetarian'),
        ('4', 'N/A')], string='Meal Type', required=True, default='4', help='Product type i.e. Veg, Non-Veg, etc.')
    is_recommended_on_urbanpiper = fields.Boolean(string='Is Recommended', help='Recommended products on food platforms.')
    urban_piper_status_ids = fields.One2many(
        'product.urban.piper.status',
        'product_tmpl_id',
        string='Stores',
        help='Handle products with urban piper and pos config - Product is linked or not with appropriate store.'
    )
    is_alcoholic_on_urbanpiper = fields.Boolean(string='Is Alcoholic', help='Indicates if the product contains alcohol.')

    def write(self, vals):
        field_list = ['name', 'description', 'list_price', 'weight', 'urbanpiper_meal_type', 'pos_categ_ids', 'image_1920', 'public_description',
                    'product_template_attribute_value_ids', 'taxes_id', 'is_recommended_on_urbanpiper', 'product_tag_ids', 'is_alcoholic_on_urbanpiper', 'attribute_line_ids']
        if any(field in vals for field in field_list):
            urban_piper_statuses = self.urban_piper_status_ids.filtered(lambda s: s.is_product_linked)
            urban_piper_statuses.write({'is_product_linked': False})
        # Enable/Disable product on Urban Piper based on pos_config_ids changes.
        products_has_config_before_write = {p.id: p.urbanpiper_pos_config_ids for p in self}
        res = super().write(vals)
        products_has_config_after_write = {p.id: p.urbanpiper_pos_config_ids for p in self}
        configs_to_enable = defaultdict(list)
        configs_to_disable = defaultdict(list)
        for p in self:
            for config in products_has_config_after_write[p.id] - products_has_config_before_write[p.id]:
                if config in p.urban_piper_status_ids.config_id:
                    configs_to_enable[config].append(p)
            for config in products_has_config_before_write[p.id] - products_has_config_after_write[p.id]:
                if config in p.urban_piper_status_ids.config_id:
                    configs_to_disable[config].append(p)
        for config, products in configs_to_enable.items():
            up = UrbanPiperClient(config)
            up.register_item_toggle(products, True)
        for config, products in configs_to_disable.items():
            up = UrbanPiperClient(config)
            up.register_item_toggle(products, False)
        return res
