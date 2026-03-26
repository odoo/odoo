import logging
import base64
import datetime
import requests

from odoo import api, fields, models
from odoo.exceptions import UserError

from ..mappers import ProductMapper

_logger = logging.getLogger(__name__)

# WC product types that have variants
_VARIABLE_TYPES = {'variable'}


class WooCommerceProductBinding(models.Model):
    """Bridge between WooCommerce products and Odoo product.template records.

    One binding per (backend, WooCommerce product ID) pair.
    The unique constraint on (backend_id, external_id) guarantees idempotency.
    """

    _name = 'woocommerce.product.binding'
    _description = 'WooCommerce Product Binding'
    _inherit = ['channel.binding']
    _order = 'backend_id, external_id'
    _rec_name = 'display_name'

    # ── Relations ─────────────────────────────────────────────────────────────

    backend_id = fields.Many2one(
        comodel_name='woocommerce.backend',
        string='WooCommerce Backend',
        required=True,
        ondelete='cascade',
        index=True,
    )
    odoo_id = fields.Many2one(
        comodel_name='product.template',
        string='Odoo Product',
        required=True,
        ondelete='cascade',
        index=True,
    )

    # ── WooCommerce Metadata ──────────────────────────────────────────────────

    wc_type = fields.Char(
        string='WC Product Type',
        help='simple, variable, grouped, external',
    )
    wc_status = fields.Char(string='WC Status')
    wc_permalink = fields.Char(string='WC Permalink')
    wc_sku = fields.Char(string='WC SKU')
    wc_data_hash = fields.Char(
        string='Data Hash',
        help='MD5 hash of key WC product fields. Used to skip unchanged records.',
    )

    # ── Computed ──────────────────────────────────────────────────────────────

    display_name = fields.Char(compute='_compute_display_name', store=True)

    @api.depends('backend_id', 'external_id', 'odoo_id')
    def _compute_display_name(self):
        for rec in self:
            product_name = rec.odoo_id.name if rec.odoo_id else '?'
            rec.display_name = f'[{rec.backend_id.name}] #{rec.external_id} – {product_name}'

    # ── Constraints ───────────────────────────────────────────────────────────

    _sql_constraints = [
        ('unique_backend_external', 'UNIQUE(backend_id, external_id)',
         'A binding for this WooCommerce product already exists on this backend.'),
    ]

    # ── Import Orchestration ──────────────────────────────────────────────────

    @api.model
    def _run_import(self, backend):
        """Import all products from WooCommerce into Odoo.

        Uses last_products_sync as a cursor for incremental updates.
        Processes in batches to keep memory bounded.

        :param backend: woocommerce.backend record
        """
        client = backend._get_client()
        since = None
        if backend.last_products_sync:
            # Subtract 5 min overlap to catch near-boundary updates
            dt = backend.last_products_sync - datetime.timedelta(minutes=5)
            since = dt.strftime('%Y-%m-%dT%H:%M:%S')

        _logger.info('[WooCommerce] Starting product import for backend %s (since=%s)',
                     backend.name, since)

        imported = skipped = errors = 0
        sync_start = fields.Datetime.now()

        for wc_product in client.get_all_products(modified_after=since):
            try:
                result = self._import_one_product(backend, wc_product, client)
                if result == 'created' or result == 'updated':
                    imported += 1
                elif result == 'skipped':
                    skipped += 1
            except Exception as exc:
                errors += 1
                _logger.error(
                    '[WooCommerce] Failed to import product #%s: %s',
                    wc_product.get('id'), exc, exc_info=True,
                )

        backend.write({'last_products_sync': sync_start})

        _logger.info(
            '[WooCommerce] Product import complete for %s: %d imported, %d skipped, %d errors',
            backend.name, imported, skipped, errors,
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Product Sync Complete',
                'message': f'{imported} imported/updated, {skipped} skipped, {errors} errors.',
                'type': 'success' if errors == 0 else 'warning',
                'sticky': False,
            },
        }

    @api.model
    def _import_one_product(self, backend, wc_product, client):
        """Import or update a single WooCommerce product.

        :returns: 'created', 'updated', or 'skipped'
        """
        wc_id = str(wc_product.get('id'))
        wc_type = wc_product.get('type', 'simple')

        log = self.env['channel.sync.log'].start(
            backend, 'product', 'import', external_id=wc_id,
            raw_data=str(wc_product)[:4096],
        )

        try:
            # ── Deduplication ─────────────────────────────────────────────────
            data_hash = self._compute_hash(wc_product)
            binding = self._get_binding(backend, wc_id)

            if binding and binding.wc_data_hash == data_hash:
                log.skip('No changes detected (hash match).')
                return 'skipped'

            # ── Resolve / create Odoo product template ────────────────────────
            if binding:
                template = binding.odoo_id
                action = 'updated'
            else:
                template = self._find_or_create_template(backend, wc_product)
                action = 'created'

            # ── Apply scalar fields ───────────────────────────────────────────
            categ_id = self._resolve_category(backend, wc_product)
            template_vals = ProductMapper.to_template_vals(wc_product, categ_id=categ_id)

            if backend.product_as_storable:
                template_vals['type'] = 'product'

            template.write(template_vals)

            # ── Handle image ──────────────────────────────────────────────────
            self._sync_product_image(template, wc_product)

            # ── Handle variants (variable products) ───────────────────────────
            if wc_type in _VARIABLE_TYPES:
                self._sync_variations(backend, template, wc_product, client)

            # ── Create or update binding ──────────────────────────────────────
            binding_vals = {
                'wc_type': wc_type,
                'wc_status': wc_product.get('status'),
                'wc_permalink': wc_product.get('permalink'),
                'wc_sku': wc_product.get('sku'),
                'wc_data_hash': data_hash,
                'sync_state': 'synced',
                'last_sync': fields.Datetime.now(),
                'sync_error': False,
            }
            if binding:
                binding.write(binding_vals)
            else:
                binding = self.create({
                    'backend_id': backend.id,
                    'external_id': wc_id,
                    'odoo_id': template.id,
                    **binding_vals,
                })

            log.succeed(odoo_record=template)
            return action

        except Exception as exc:
            log.fail(str(exc))
            raise

    # ── Template Resolution ───────────────────────────────────────────────────

    @api.model
    def _find_or_create_template(self, backend, wc_product):
        """Find existing product.template by SKU or create a new one.

        Matching priority:
        1. SKU match (default_code)
        2. Barcode match
        3. Create new

        :returns: product.template record
        """
        ProductTemplate = self.env['product.template']

        # 1. SKU match
        sku = (wc_product.get('sku') or '').strip()
        if sku:
            tmpl = ProductTemplate.search([('default_code', '=', sku)], limit=1)
            if tmpl:
                _logger.debug('[WooCommerce] Matched product by SKU: %s', sku)
                return tmpl

        # 2. Name match as last resort (risky — log a warning)
        # We deliberately do NOT match by name to avoid false positives.

        # 3. Create new
        categ_id = self._resolve_category(backend, wc_product)
        vals = ProductMapper.to_template_vals(wc_product, categ_id=categ_id)
        if backend.product_as_storable:
            vals['type'] = 'product'
        template = ProductTemplate.create(vals)
        _logger.debug('[WooCommerce] Created new product.template id=%s for WC product #%s',
                      template.id, wc_product.get('id'))
        return template

    # ── Variant Sync ──────────────────────────────────────────────────────────

    @api.model
    def _sync_variations(self, backend, template, wc_product, client):
        """Sync variants for a WooCommerce variable product.

        Creates product.attribute / product.attribute.value records as needed,
        then maps variation JSON to product.product variants.
        """
        wc_id = wc_product.get('id')
        attributes = ProductMapper.extract_attributes(wc_product)

        # ── Ensure attributes and values exist on the template ────────────────
        attr_value_map = {}  # {(attr_name, val_name): product.template.attribute.value}
        for attr_info in attributes:
            if not attr_info.get('variation'):
                continue
            attr_name = attr_info['name']
            odoo_attr = self.env['product.attribute'].search(
                [('name', '=ilike', attr_name)], limit=1,
            )
            if not odoo_attr:
                odoo_attr = self.env['product.attribute'].create({'name': attr_name})

            # Ensure this attribute line exists on template
            attr_line = template.attribute_line_ids.filtered(
                lambda l: l.attribute_id == odoo_attr
            )
            if not attr_line:
                attr_line = self.env['product.template.attribute.line'].create({
                    'product_tmpl_id': template.id,
                    'attribute_id': odoo_attr.id,
                    'value_ids': [],
                })

            for val_name in attr_info['values']:
                attr_val = self.env['product.attribute.value'].search([
                    ('name', '=ilike', val_name),
                    ('attribute_id', '=', odoo_attr.id),
                ], limit=1)
                if not attr_val:
                    attr_val = self.env['product.attribute.value'].create({
                        'name': val_name,
                        'attribute_id': odoo_attr.id,
                    })
                # Add to attribute line if missing
                if attr_val not in attr_line.value_ids:
                    attr_line.write({'value_ids': [(4, attr_val.id)]})
                attr_value_map[(attr_name.lower(), val_name.lower())] = attr_val

        # ── Sync individual variations ────────────────────────────────────────
        VariantBinding = self.env['woocommerce.product.variant.binding']
        for wc_var in client.get_product_variations(wc_id):
            var_id = str(wc_var.get('id'))
            var_attrs = ProductMapper.extract_variation_attributes(wc_var)
            sku = (wc_var.get('sku') or '').strip()

            # Find matching product.product variant
            variant = None

            # 1. By SKU
            if sku:
                variant = self.env['product.product'].search(
                    [('default_code', '=', sku), ('product_tmpl_id', '=', template.id)],
                    limit=1,
                )

            # 2. By attribute combination
            if not variant and var_attrs:
                # Build domain filtering by attribute value combination
                domain = [('product_tmpl_id', '=', template.id)]
                for attr_name, val_name in var_attrs.items():
                    av = attr_value_map.get((attr_name.lower(), val_name.lower()))
                    if av:
                        domain.append((
                            'product_template_attribute_value_ids.product_attribute_value_id',
                            '=', av.id,
                        ))
                variant = self.env['product.product'].search(domain, limit=1)

            # 3. Take first unbound variant (for new products)
            if not variant:
                bound_variant_ids = VariantBinding.search(
                    [('backend_id', '=', backend.id)]
                ).mapped('odoo_id.id')
                unbound = template.product_variant_ids.filtered(
                    lambda v: v.id not in bound_variant_ids
                )
                if unbound:
                    variant = unbound[0]

            if not variant:
                _logger.warning(
                    '[WooCommerce] Cannot find/create variant for WC variation #%s', var_id
                )
                continue

            # Update variant fields
            var_vals = ProductMapper.to_variant_vals(wc_var)
            variant.write(var_vals)

            # Create/update variant binding
            vbinding = VariantBinding._get_binding(backend, var_id)
            if vbinding:
                vbinding.write({'sync_state': 'synced', 'last_sync': fields.Datetime.now()})
            else:
                VariantBinding.create({
                    'backend_id': backend.id,
                    'external_id': var_id,
                    'odoo_id': variant.id,
                    'product_binding_id': self.search([
                        ('backend_id', '=', backend.id),
                        ('external_id', '=', str(wc_id)),
                    ], limit=1).id,
                    'sync_state': 'synced',
                    'last_sync': fields.Datetime.now(),
                })

    # ── Category Resolution ───────────────────────────────────────────────────

    @api.model
    def _resolve_category(self, backend, wc_product):
        """Return an Odoo product.category ID for the first WC category, or default."""
        categories = ProductMapper.extract_categories(wc_product)
        for cat in categories:
            cat_name = cat.get('name', '').strip()
            if not cat_name:
                continue
            odoo_cat = self.env['product.category'].search(
                [('name', '=ilike', cat_name)], limit=1,
            )
            if odoo_cat:
                return odoo_cat.id
            # Create category
            new_cat = self.env['product.category'].create({'name': cat_name})
            return new_cat.id

        if backend.default_product_categ_id:
            return backend.default_product_categ_id.id
        return None

    # ── Image Sync ────────────────────────────────────────────────────────────

    @api.model
    def _sync_product_image(self, template, wc_product):
        """Download and set the main product image from WooCommerce."""
        if template.image_1920:
            return  # Don't overwrite existing images
        image_url = ProductMapper.extract_main_image_url(wc_product)
        if not image_url:
            return
        try:
            resp = requests.get(image_url, timeout=15, verify=True)
            if resp.ok:
                template.image_1920 = base64.b64encode(resp.content)
        except Exception as exc:
            _logger.warning(
                '[WooCommerce] Failed to download image for product #%s: %s',
                wc_product.get('id'), exc,
            )

    # ── Hash Computation ──────────────────────────────────────────────────────

    @staticmethod
    def _compute_hash(wc_product):
        """Compute a hash of key product fields for change detection."""
        import hashlib, json
        key_fields = {
            'name': wc_product.get('name'),
            'sku': wc_product.get('sku'),
            'price': wc_product.get('price'),
            'regular_price': wc_product.get('regular_price'),
            'status': wc_product.get('status'),
            'type': wc_product.get('type'),
            'stock_quantity': wc_product.get('stock_quantity'),
        }
        return hashlib.md5(json.dumps(key_fields, sort_keys=True).encode()).hexdigest()


class WooCommerceProductVariantBinding(models.Model):
    """Bridge between WooCommerce product variations and Odoo product.product variants."""

    _name = 'woocommerce.product.variant.binding'
    _description = 'WooCommerce Product Variant Binding'
    _inherit = ['channel.binding']
    _order = 'backend_id, external_id'

    backend_id = fields.Many2one(
        comodel_name='woocommerce.backend',
        string='WooCommerce Backend',
        required=True,
        ondelete='cascade',
        index=True,
    )
    odoo_id = fields.Many2one(
        comodel_name='product.product',
        string='Odoo Variant',
        required=True,
        ondelete='cascade',
        index=True,
    )
    product_binding_id = fields.Many2one(
        comodel_name='woocommerce.product.binding',
        string='Parent Product Binding',
        ondelete='cascade',
        index=True,
    )

    _sql_constraints = [
        ('unique_backend_external', 'UNIQUE(backend_id, external_id)',
         'A variant binding for this WooCommerce variation already exists.'),
    ]
