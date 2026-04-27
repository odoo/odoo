from odoo import fields, models
from collections import defaultdict
from odoo.addons.pos_urban_piper.models.pos_urban_piper_request import UrbanPiperClient


class ProductTemplateAttributeValue(models.Model):
    _inherit = 'product.template.attribute.value'

    urbanpiper_pos_config_ids = fields.Many2many(
        'pos.config',
        string='Available on Food Delivery',
        help='Check this if the value is available for food delivery.',
        domain="[('urbanpiper_store_identifier', '!=', False), ('module_pos_urban_piper', '=', True)]",
    )

    def write(self, vals):
        value_has_config_before_write = {v.id: v.urbanpiper_pos_config_ids for v in self}
        res = super().write(vals)
        value_has_config_after_write = {v.id: v.urbanpiper_pos_config_ids for v in self}
        configs_to_enable = defaultdict(list)
        configs_to_disable = defaultdict(list)
        for v in self:
            for config in value_has_config_after_write[v.id] - value_has_config_before_write[v.id]:
                if config in v.product_tmpl_id.urban_piper_status_ids.config_id:
                    configs_to_enable[config].append(v)
            for config in value_has_config_before_write[v.id] - value_has_config_after_write[v.id]:
                if config in v.product_tmpl_id.urban_piper_status_ids.config_id:
                    configs_to_disable[config].append(v)
        for config, values in configs_to_enable.items():
            up = UrbanPiperClient(config)
            up.urbanpiper_attribute_value_toggle(values, True)
        for config, values in configs_to_disable.items():
            up = UrbanPiperClient(config)
            up.urbanpiper_attribute_value_toggle(values, False)
        for v in self:
            product_configs = v.product_tmpl_id.urbanpiper_pos_config_ids
            for config in product_configs:
                if config not in v.product_tmpl_id.attribute_line_ids.product_template_value_ids.urbanpiper_pos_config_ids:
                    v.product_tmpl_id.urbanpiper_pos_config_ids -= config
            for config in v.urbanpiper_pos_config_ids:
                if config not in v.product_tmpl_id.urbanpiper_pos_config_ids:
                    v.product_tmpl_id.with_context(skip_product_config_update=True).urbanpiper_pos_config_ids |= config
        return res
