# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models
from odoo.tools import SQL


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def _load_pos_data_fields(self, config_id):
        pos_data_fields = super()._load_pos_data_fields(config_id)
        pos_data_fields.append('tracking')
        return pos_data_fields

    @api.model
    def _load_pos_data_search_read(self, data, config):
        limit_count = config.get_limited_product_count()
        pos_limited_loading = self.env.context.get('pos_limited_loading', True)
        if limit_count and pos_limited_loading:
            query = self._search(self._load_pos_data_domain(data, config), bypass_access=True)
            sql = SQL(
                """
                    WITH pm AS (
                        SELECT pp.product_tmpl_id,
                            MAX(sml.write_date) date
                        FROM stock_move_line sml
                        JOIN product_product pp ON sml.product_id = pp.id
                        GROUP BY pp.product_tmpl_id
                    )
                    SELECT product_template.id
                        FROM %s
                    LEFT JOIN pm ON product_template.id = pm.product_tmpl_id
                        WHERE %s
                    ORDER BY product_template.is_favorite DESC NULLS LAST,
                        CASE WHEN product_template.type = 'service' THEN 1 ELSE 0 END DESC,
                        pm.date DESC NULLS LAST,
                        product_template.write_date DESC
                    LIMIT %s
                """,
                query.from_clause,
                query.where_clause or SQL("TRUE"),
                limit_count,
            )
            product_tmpl_ids = [r[0] for r in self.env.execute_query(sql)]
            products = self._load_product_with_domain([('id', 'in', product_tmpl_ids)])
        else:
            domain = self._load_pos_data_domain(data, config)
            products = self._load_product_with_domain(domain)

        product_combo = products.filtered(lambda p: p['type'] == 'combo')
        products += product_combo.combo_ids.combo_item_ids.product_id.product_tmpl_id

        special_products = config._get_special_products().filtered(
                    lambda product: not product.sudo().company_id
                                    or product.sudo().company_id == self.env.company
                )
        products += special_products.product_tmpl_id
        if config.tip_product_id:
            tip_company_id = config.tip_product_id.sudo().company_id
            if not tip_company_id or tip_company_id == self.env.company:
                products += config.tip_product_id.product_tmpl_id

        # Ensure optional products are loaded when configured.
        if products.filtered(lambda p: p.pos_optional_product_ids):
            products |= products.mapped("pos_optional_product_ids")

        # Ensure products from loaded orders are loaded
        if data.get('pos.order.line'):
            products += self.env['product.product'].browse([l['product_id'] for l in data['pos.order.line']]).product_tmpl_id
        return self._load_pos_data_read(products, config)

    def get_product_info_pos(self, price, quantity, pos_config_id, product_variant_id=False):
        product_info = super().get_product_info_pos(price, quantity, pos_config_id, product_variant_id)
        config = self.env['pos.config'].browse(pos_config_id)
        product_variant = self.env['product.product'].browse(product_variant_id) if product_variant_id else False
        template_or_variant = product_variant or self

        warehouse_list = [
            {'id': w.id,
            'name': w.name,
            'available_quantity': template_or_variant.with_context({'warehouse_id': w.id}).qty_available,
            'free_qty': (
                    template_or_variant.with_context({'warehouse_id': w.id}).free_qty
                    if product_variant
                    else sum(self.product_variant_ids.with_context({'warehouse_id': w.id}).mapped('free_qty'))
                ),
            'forecasted_quantity': template_or_variant.with_context({'warehouse_id': w.id}).virtual_available,
            'uom': template_or_variant.uom_name}
            for w in self.env['stock.warehouse'].search([('company_id', '=', config.company_id.id)])]

        if config.picking_type_id.warehouse_id:
            # Sort the warehouse_list, prioritizing config.picking_type_id.warehouse_id
            warehouse_list = sorted(
                warehouse_list,
                key=lambda w: w['id'] != config.picking_type_id.warehouse_id.id
            )
        product_info.update({'warehouses': warehouse_list})
        return product_info
