# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    # NOTE: this function acts as a m2m field with loyalty.program model. We do this to handle an exceptional use case:
    # When no PoS is specified at a loyalty program form, this program is applied to every PoS (instead of none)
    def _get_program_ids(self, check_usage=True):
        today = fields.Date.context_today(self)
        programs = self.env['loyalty.program'].search([
            ('pos_ok', '=', True),
            '|', ('pos_config_ids', '=', self.id), ('pos_config_ids', '=', False),
            '|', ('date_from', '=', False), ('date_from', '<=', today),
            '|', ('date_to', '=', False), ('date_to', '>=', today),
            '|', ('pricelist_ids', '=', False), ('pricelist_ids', 'in', self._get_available_pricelists().ids),
            ('currency_id', '=', self.currency_id.id)
        ])

        if check_usage:
            programs = programs.filtered(
                lambda p: not p.limit_usage or p.sudo().total_order_count < p.max_usage
            )
        return programs

    @api.model
    def _load_pos_data_read(self, records, config):
        read_records = super()._load_pos_data_read(records, config)
        if not read_records:
            return read_records

        # Identify special loyalty products (e.g., gift cards, e-wallets) to be displayed in the POS
        loyality_products = config.get_record_by_ref([
            'loyalty.gift_card_product_50',
            'loyalty.ewallet_product_50',
        ])
        special_display_products = self.env['product.product'].search([('id', 'in', loyality_products)])
        # Include trigger products from loyalty programs of type 'gift_card' or 'ewallet'
        special_display_products += self.env['loyalty.program'].search([
            ('program_type', 'in', ['ewallet']),
            ('pos_config_ids', 'in', [False, config.id]),
        ]).trigger_product_ids
        read_records[0]['_pos_special_display_products_ids'] = special_display_products.product_tmpl_id.ids

        return read_records
