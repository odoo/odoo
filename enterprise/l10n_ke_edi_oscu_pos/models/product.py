from odoo import _, models, fields, api


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def l10n_ke_action_open_products_view(self, product_ids):
        return {
            'name': _("Products"),
            'type': 'ir.actions.act_window',
            'res_model': 'product.product',
            'domain': [('id', 'in', product_ids)],
            'views': [
                (self.env.ref('l10n_ke_edi_oscu_pos.l10n_ke_pos_kra_product_list').id, 'list'),
            ],
            'context': {'create': False, 'delete': False},
            'target': 'new',
        }

    def _load_pos_data_fields(self, config_id):
        """ This function add new fields on the product model in pos app. """
        return [
            *super()._load_pos_data_fields(config_id),
            'l10n_ke_item_code',
            'l10n_ke_packaging_unit_id',
            'l10n_ke_packaging_quantity',
            'l10n_ke_origin_country_id',
            'l10n_ke_product_type_code',
            'unspsc_code_id',
        ]


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    l10n_ke_validation_message = fields.Char(compute='_compute_l10n_ke_validation_message')

    @api.depends('available_in_pos')
    def _compute_l10n_ke_validation_message(self):
        for product in self:
            product.l10n_ke_validation_message = ""
            if product.available_in_pos:
                if self.env.company.country_code != 'KE':
                    continue

                messages = {}

                for variant in product.product_variant_ids:
                    variant_messages = {
                        **variant._l10n_ke_get_validation_messages(),
                        **variant.uom_id._l10n_ke_get_validation_messages(),
                    }
                    for key, value in variant_messages.items():
                        if key not in messages:
                            messages[key] = value

                for message in messages.values():
                    product.l10n_ke_validation_message += f"{message['message']}\n"


class ProductCode(models.Model):
    _inherit = 'product.unspsc.code'

    def _load_pos_data(self, data):
        domain = []
        fields = self._load_pos_data_fields(data['pos.config']['data'][0]['id'])
        data = self.search_read(domain, fields, load=False)
        return {
            'data': data,
            'fields': fields,
        }

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['code']
