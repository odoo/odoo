"""WooCommerce order data → Odoo sale.order field values."""

import logging
from datetime import datetime

_logger = logging.getLogger(__name__)

# Map WooCommerce order statuses to Odoo sale.order states
# WC statuses: pending, processing, on-hold, completed, cancelled, refunded, failed, trash
_WC_STATUS_TO_ODOO = {
    'pending': 'draft',
    'on-hold': 'draft',
    'processing': 'sale',     # confirmed
    'completed': 'sale',      # confirmed (fully fulfilled)
    'cancelled': 'cancel',
    'refunded': 'cancel',
    'failed': 'cancel',
    'trash': 'cancel',
}

# WC statuses that should be auto-confirmed in Odoo
_AUTO_CONFIRM_STATUSES = {'processing', 'completed'}


class OrderMapper:
    """Transforms WooCommerce order JSON to Odoo sale.order/line field dicts."""

    # ── Order Header ──────────────────────────────────────────────────────────

    @classmethod
    def to_order_vals(cls, wc_order, partner_id, partner_shipping_id=None, pricelist_id=None):
        """Map a WooCommerce order to sale.order create vals.

        :param wc_order: dict from GET /orders/<id>
        :param partner_id: resolved Odoo res.partner ID (billing)
        :param partner_shipping_id: resolved delivery partner ID (or same as partner_id)
        :param pricelist_id: Odoo pricelist ID to use (or None for default)
        :returns: dict for sale.order.create() (without order lines)
        """
        wc_status = wc_order.get('status', 'pending')

        vals = {
            'partner_id': partner_id,
            'partner_shipping_id': partner_shipping_id or partner_id,
            'client_order_ref': str(wc_order.get('number') or wc_order.get('id')),
            'origin': f"WooCommerce #{wc_order.get('number') or wc_order.get('id')}",
            'note': cls._build_order_note(wc_order),
        }

        if pricelist_id:
            vals['pricelist_id'] = pricelist_id

        # Order date
        date_str = wc_order.get('date_created_gmt') or wc_order.get('date_created')
        if date_str:
            vals['date_order'] = cls._parse_date(date_str)

        # Customer note
        customer_note = (wc_order.get('customer_note') or '').strip()
        if customer_note:
            vals['note'] = customer_note

        return vals

    # ── Order Lines ───────────────────────────────────────────────────────────

    @classmethod
    def to_order_line_vals(cls, wc_line_item, product_id, tax_id=None):
        """Map a WooCommerce order line item to sale.order.line vals.

        :param wc_line_item: dict from order['line_items'][i]
        :param product_id: resolved Odoo product.product ID
        :param tax_id: list of resolved account.tax IDs (or None)
        :returns: dict for sale.order.line values (without order_id — set by ORM)
        """
        qty = float(wc_line_item.get('quantity') or 1)
        subtotal = float(wc_line_item.get('subtotal') or 0.0)
        subtotal_tax = float(wc_line_item.get('subtotal_tax') or 0.0)

        # Unit price: use subtotal / qty to get pre-tax unit price
        unit_price = (subtotal / qty) if qty else 0.0

        # Discount: WC provides total and subtotal; derive discount %
        total = float(wc_line_item.get('total') or subtotal)
        discount = 0.0
        if subtotal > 0 and total < subtotal:
            discount = round((1 - total / subtotal) * 100, 2)

        vals = {
            'product_id': product_id,
            'product_uom_qty': qty,
            'price_unit': unit_price,
            'discount': discount,
            'name': wc_line_item.get('name') or 'WooCommerce Product',
        }

        if tax_id:
            vals['tax_id'] = [(6, 0, tax_id)]

        return vals

    # ── Shipping Lines ────────────────────────────────────────────────────────

    @classmethod
    def extract_shipping_lines(cls, wc_order):
        """Return list of shipping line dicts from WC order.

        Each dict has: {'method_title': str, 'total': float}
        """
        lines = []
        for sl in wc_order.get('shipping_lines', []):
            try:
                total = float(sl.get('total') or 0.0)
            except (ValueError, TypeError):
                total = 0.0
            lines.append({
                'method_title': sl.get('method_title') or 'Shipping',
                'method_id': sl.get('method_id') or '',
                'total': total,
            })
        return lines

    # ── Discount Lines ────────────────────────────────────────────────────────

    @classmethod
    def extract_coupon_lines(cls, wc_order):
        """Return list of coupon dicts applied to the order."""
        return [
            {
                'code': c.get('code', ''),
                'discount': float(c.get('discount') or 0.0),
            }
            for c in wc_order.get('coupon_lines', [])
        ]

    # ── Status Mapping ────────────────────────────────────────────────────────

    @classmethod
    def get_odoo_state(cls, wc_status):
        """Return the Odoo sale.order state for the given WooCommerce status."""
        return _WC_STATUS_TO_ODOO.get(wc_status, 'draft')

    @classmethod
    def should_confirm(cls, wc_status):
        """Return True if this WC status means the order should be confirmed in Odoo."""
        return wc_status in _AUTO_CONFIRM_STATUSES

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_date(date_str):
        """Parse ISO 8601 date string to Odoo-compatible datetime string."""
        if not date_str:
            return False
        # Strip trailing 'Z' or timezone offset for simplicity
        # WooCommerce *_gmt fields are already UTC
        clean = date_str.replace('Z', '').replace('T', ' ')
        # Handle +00:00 style
        if '+' in clean:
            clean = clean.split('+')[0]
        elif clean.count('-') > 2:
            # Remove timezone offset like -05:00
            parts = clean.rsplit('-', 1)
            if len(parts[1]) <= 5:  # looks like a timezone
                clean = parts[0]
        return clean.strip()

    @staticmethod
    def _build_order_note(wc_order):
        """Build a note string from order metadata."""
        parts = []
        wc_id = wc_order.get('id')
        wc_number = wc_order.get('number')
        if wc_id or wc_number:
            parts.append(f'WooCommerce Order #{wc_number or wc_id}')
        payment_method = wc_order.get('payment_method_title') or wc_order.get('payment_method')
        if payment_method:
            parts.append(f'Payment: {payment_method}')
        customer_note = (wc_order.get('customer_note') or '').strip()
        if customer_note:
            parts.append(f'Customer note: {customer_note}')
        return '\n'.join(parts) or False
