# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from odoo import api, models, fields, _
from odoo.exceptions import UserError


class ProductProduct(models.Model):
    _name = 'product.product'
    _inherit = ['product.product', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [('product_tmpl_id', 'in', [p['id'] for p in data['product.template']])]

    @api.model
    def _load_pos_data_fields(self, config):
        taxes = self.env['account.tax'].search(self.env['account.tax']._check_company_domain(config.company_id.id))
        product_fields = taxes._eval_taxes_computation_prepare_product_fields()
        # 'lst_price' and 'standard_price' are slow computed fields.
        # They are simulated in _process_pos_ui_data instead.
        return list((product_fields - {'lst_price', 'standard_price'}).union({
            'id', 'product_tmpl_id', 'product_template_variant_value_ids',
            'product_template_attribute_value_ids', 'barcode', 'product_tag_ids', 'default_code', 'name'
        }))

    @api.model
    def _process_pos_ui_data(self, records, config):
        """Simulate variant computed fields that are too slow for ORM reads.

        Batch-fetches template data, attribute values, and tags via SQL
        to build display_name, lst_price, and all_product_tag_ids.
        """
        super()._process_pos_ui_data(records, config)

        # --- Batch-fetch template data (name, list_price, taxes, tags) ---
        tmpl_ids = {r['product_tmpl_id'] for r in records}
        templates = self.env['product.template'].browse(tmpl_ids)
        tmpl_data = {t.id: {
            'name': t.name,
            'list_price': t.list_price,
            'tag_ids': t.product_tag_ids.ids,
            'taxes_id': t.taxes_id.ids,
        } for t in templates}

        # --- Batch-fetch attribute value names and price extras ---
        attr_val_ids = set()
        for r in records:
            attr_val_ids.update(r.get('product_template_attribute_value_ids', []))
        attr_vals = self.env['product.template.attribute.value'].browse(attr_val_ids)
        attr_data = {v.id: {'name': v.name, 'price_extra': v.price_extra} for v in attr_vals}

        # --- Batch-fetch variant-level tags via SQL ---
        variant_ids = [r['id'] for r in records]
        self.env.cr.execute("""
            SELECT product_product_id, product_tag_id
            FROM product_tag_product_product_rel
            WHERE product_product_id IN %s
        """, [tuple(variant_ids)])
        variant_tags = defaultdict(list)
        for vid, tid in self.env.cr.fetchall():
            variant_tags[vid].append(tid)

        # --- Simulate computed fields for each variant ---
        for record in records:
            tmpl = tmpl_data.get(record['product_tmpl_id'], {})
            ptavs = record.get('product_template_attribute_value_ids', [])

            # lst_price = template list_price + sum of attribute price extras
            price_extra = sum(attr_data.get(vid, {}).get('price_extra', 0.0) for vid in ptavs)
            record['lst_price'] = tmpl.get('list_price', 0.0) + price_extra

            # display_name = "Template Name (Variant1, Variant2)"
            v_names = [attr_data[vid]['name'] for vid in ptavs if vid in attr_data and attr_data[vid].get('name')]
            variant_str = ", ".join(v_names)
            base_name = tmpl.get('name') or record.get('name', '')
            record['display_name'] = f"{base_name} ({variant_str})" if variant_str else base_name

            # all_product_tag_ids = template tags ∪ variant tags
            tags = set(tmpl.get('tag_ids', []))
            tags.update(variant_tags.get(record['id'], []))
            record['all_product_tag_ids'] = list(tags)
            record['product_tag_ids'] = variant_tags.get(record['id'], [])

            # Inherit taxes from template if not set on variant
            if not record.get('taxes_id'):
                record['taxes_id'] = tmpl.get('taxes_id', [])

        # Apply shared product processing (currency, search strings, tax filtering)
        self.env['product.template']._apply_product_processing(records, config)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_active_pos_session(self):
        product_ctx = dict(self.env.context or {}, active_test=False)
        if self.env['pos.session'].sudo().search_count([('state', '!=', 'closed')]):
            if self.with_context(product_ctx).search_count([('id', 'in', self.ids), ('product_tmpl_id.available_in_pos', '=', True)]):
                raise UserError(_(
                    "To delete a product, make sure all point of sale sessions are closed.\n\n"
                    "Deleting a product available in a session would be like attempting to snatch a hamburger from a customer's hand mid-bite; chaos will ensue as ketchup and mayo go flying everywhere!",
                ))

    @api.ondelete(at_uninstall=False)
    def _unlink_except_special_product(self):
        self.product_tmpl_id._check_is_special_product()


    def _can_return_content(self, field_name=None, access_token=None):
        if field_name == "image_128" and self.sudo().available_in_pos:
            return True
        return super()._can_return_content(field_name, access_token)

    def action_archive(self):
        self.product_tmpl_id._ensure_unused_in_pos()
        self.product_tmpl_id._check_is_special_product()
        return super().action_archive()

