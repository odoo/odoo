"""WooCommerce product data → Odoo product field values.

Pure transformation logic. No ORM access, no database calls.
The mapper receives a WooCommerce product dict and returns a dict
of Odoo field values suitable for model.create() / model.write().

WooCommerce product types handled:
- simple: one product.template, no variants
- variable: one product.template, multiple product.product variants
- variation: individual variation under a variable product
"""

import logging

_logger = logging.getLogger(__name__)

# Map WooCommerce tax_status to a human-readable label
_TAX_STATUS_MAP = {
    'taxable': 'taxable',
    'shipping': 'shipping',
    'none': 'none',
}

# Map WooCommerce stock_status to a boolean
_IN_STOCK_MAP = {
    'instock': True,
    'outofstock': False,
    'onbackorder': True,
}


class ProductMapper:
    """Transforms WooCommerce product/variation JSON to Odoo field dicts."""

    # ── Product Template ──────────────────────────────────────────────────────

    @classmethod
    def to_template_vals(cls, wc_product, categ_id=None):
        """Map a WooCommerce product to product.template create/write vals.

        :param wc_product: dict from WooCommerce GET /products/<id>
        :param categ_id: resolved Odoo product.category ID (or None)
        :returns: dict suitable for product.template.create() / .write()
        """
        vals = {
            'name': wc_product.get('name') or 'Unnamed Product',
            'description_sale': cls._clean_html(wc_product.get('short_description', '')),
            'description': cls._clean_html(wc_product.get('description', '')),
            'list_price': float(wc_product.get('price') or wc_product.get('regular_price') or 0.0),
            'active': wc_product.get('status') == 'publish',
        }

        # Internal reference (SKU) — only set if WC has one
        sku = wc_product.get('sku', '').strip()
        if sku:
            vals['default_code'] = sku

        # Category
        if categ_id:
            vals['categ_id'] = categ_id

        # Weight (WooCommerce uses grams or kg depending on store settings —
        # stored as-is; the backend model holds the unit assumption)
        weight = wc_product.get('weight', '')
        if weight:
            try:
                vals['weight'] = float(weight)
            except (ValueError, TypeError):
                pass

        # Product type
        wc_type = wc_product.get('type', 'simple')
        if wc_type in ('simple', 'external', 'grouped'):
            vals['type'] = 'consu'  # consumable by default; change to 'product' for storable
        elif wc_type == 'variable':
            vals['type'] = 'consu'

        # Sale price (if on sale)
        sale_price = wc_product.get('sale_price', '')
        if sale_price:
            try:
                vals['list_price'] = float(sale_price)
            except (ValueError, TypeError):
                pass

        return vals

    # ── Product Variant ───────────────────────────────────────────────────────

    @classmethod
    def to_variant_vals(cls, wc_variation):
        """Map a WooCommerce variation to field values for product.product.

        Note: This only covers scalar fields. Attribute value linking is
        handled in the sync layer (requires DB lookups).

        :param wc_variation: dict from GET /products/<id>/variations/<vid>
        :returns: dict for product.product.write()
        """
        vals = {
            'active': wc_variation.get('status', 'publish') == 'publish',
            'list_price': float(
                wc_variation.get('price')
                or wc_variation.get('regular_price')
                or 0.0
            ),
        }

        sku = (wc_variation.get('sku') or '').strip()
        if sku:
            vals['default_code'] = sku

        weight = wc_variation.get('weight', '')
        if weight:
            try:
                vals['weight'] = float(weight)
            except (ValueError, TypeError):
                pass

        return vals

    # ── Stock ─────────────────────────────────────────────────────────────────

    @classmethod
    def extract_stock_quantity(cls, wc_product):
        """Return the stock quantity from a WC product dict, or None if unmanaged."""
        if not wc_product.get('manage_stock'):
            return None
        qty = wc_product.get('stock_quantity')
        if qty is None:
            return None
        try:
            return float(qty)
        except (ValueError, TypeError):
            return None

    # ── Attributes ────────────────────────────────────────────────────────────

    @classmethod
    def extract_attributes(cls, wc_product):
        """Return a list of attribute dicts from a variable product.

        Each dict has: {'name': str, 'values': [str, ...], 'variation': bool}
        """
        attributes = []
        for attr in wc_product.get('attributes', []):
            attributes.append({
                'name': attr.get('name', '').strip(),
                'values': [v.strip() for v in attr.get('options', [])],
                'variation': attr.get('variation', False),
            })
        return attributes

    @classmethod
    def extract_variation_attributes(cls, wc_variation):
        """Return variation attribute name→value mapping.

        Returns: {'Color': 'Red', 'Size': 'M'}
        """
        result = {}
        for attr in wc_variation.get('attributes', []):
            name = (attr.get('name') or '').strip()
            value = (attr.get('option') or '').strip()
            if name and value:
                result[name] = value
        return result

    # ── Categories ────────────────────────────────────────────────────────────

    @classmethod
    def extract_categories(cls, wc_product):
        """Return list of {'id': int, 'name': str, 'slug': str} dicts."""
        return [
            {
                'id': cat.get('id'),
                'name': cat.get('name', ''),
                'slug': cat.get('slug', ''),
            }
            for cat in wc_product.get('categories', [])
        ]

    # ── Images ────────────────────────────────────────────────────────────────

    @classmethod
    def extract_main_image_url(cls, wc_product):
        """Return the src URL of the first image, or None."""
        images = wc_product.get('images', [])
        if images:
            return images[0].get('src')
        return None

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _clean_html(html_str):
        """Minimal HTML passthrough — Odoo Html fields accept HTML."""
        return (html_str or '').strip() or False
