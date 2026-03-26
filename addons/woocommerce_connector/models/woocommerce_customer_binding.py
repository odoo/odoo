import logging

from odoo import api, fields, models

from ..mappers import CustomerMapper

_logger = logging.getLogger(__name__)


class WooCommerceCustomerBinding(models.Model):
    """Bridge between WooCommerce customers and Odoo res.partner records.

    WooCommerce guest orders (customer_id == 0) are handled separately:
    they produce a res.partner matched by email, but no binding is created
    since there is no persistent WooCommerce customer ID to track.
    """

    _name = 'woocommerce.customer.binding'
    _description = 'WooCommerce Customer Binding'
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
        comodel_name='res.partner',
        string='Odoo Contact',
        required=True,
        ondelete='cascade',
        index=True,
    )

    # ── WooCommerce Metadata ──────────────────────────────────────────────────

    wc_email = fields.Char(string='WC Email')
    wc_username = fields.Char(string='WC Username')

    # ── Computed ──────────────────────────────────────────────────────────────

    display_name = fields.Char(compute='_compute_display_name', store=True)

    @api.depends('backend_id', 'external_id', 'odoo_id')
    def _compute_display_name(self):
        for rec in self:
            name = rec.odoo_id.name if rec.odoo_id else '?'
            rec.display_name = f'[{rec.backend_id.name}] #{rec.external_id} – {name}'

    # ── Constraints ───────────────────────────────────────────────────────────

    _sql_constraints = [
        ('unique_backend_external', 'UNIQUE(backend_id, external_id)',
         'A binding for this WooCommerce customer already exists on this backend.'),
    ]

    # ── Import ────────────────────────────────────────────────────────────────

    @api.model
    def _run_import(self, backend):
        """Import all WooCommerce customers into Odoo res.partner records."""
        client = backend._get_client()
        since = None
        if backend.last_customers_sync:
            import datetime
            dt = backend.last_customers_sync - datetime.timedelta(minutes=5)
            since = dt.strftime('%Y-%m-%dT%H:%M:%S')

        _logger.info('[WooCommerce] Starting customer import for backend %s (since=%s)',
                     backend.name, since)

        imported = skipped = errors = 0
        sync_start = fields.Datetime.now()

        for wc_customer in client.get_customers(modified_after=since):
            try:
                result = self._import_one_customer(backend, wc_customer)
                if result in ('created', 'updated'):
                    imported += 1
                else:
                    skipped += 1
            except Exception as exc:
                errors += 1
                _logger.error(
                    '[WooCommerce] Failed to import customer #%s: %s',
                    wc_customer.get('id'), exc, exc_info=True,
                )

        backend.write({'last_customers_sync': sync_start})
        _logger.info(
            '[WooCommerce] Customer import complete: %d imported, %d skipped, %d errors',
            imported, skipped, errors,
        )

    @api.model
    def _import_one_customer(self, backend, wc_customer):
        """Import or update a single WooCommerce customer."""
        wc_id = str(wc_customer.get('id'))
        email = CustomerMapper.extract_email(wc_customer)

        log = self.env['channel.sync.log'].start(
            backend, 'customer', 'import', external_id=wc_id,
        )

        try:
            binding = self._get_binding(backend, wc_id)

            if binding:
                partner = binding.odoo_id
                action = 'updated'
            else:
                # Find existing partner by email
                partner = self._find_partner_by_email(email) if email else None
                action = 'created' if not partner else 'updated'
                if not partner:
                    partner = self._create_partner(backend, wc_customer)

            # Update partner fields
            country_id, state_id = self._resolve_geo(
                wc_customer.get('billing', {}).get('country'),
                wc_customer.get('billing', {}).get('state'),
            )
            vals = CustomerMapper.to_partner_vals(wc_customer, country_id=country_id, state_id=state_id)
            partner.write(vals)

            # Create or update binding
            if not binding:
                self.create({
                    'backend_id': backend.id,
                    'external_id': wc_id,
                    'odoo_id': partner.id,
                    'wc_email': email,
                    'wc_username': wc_customer.get('username'),
                    'sync_state': 'synced',
                    'last_sync': fields.Datetime.now(),
                })
            else:
                binding.mark_synced()

            log.succeed(odoo_record=partner)
            return action

        except Exception as exc:
            log.fail(str(exc))
            raise

    # ── Find or Create Partner for Order ─────────────────────────────────────

    @api.model
    def find_or_create_for_order(self, backend, wc_order):
        """Find or create a res.partner for a WooCommerce order.

        Handles both registered customers (customer_id > 0) and guest orders.

        :returns: (billing_partner, shipping_partner) tuple
        """
        wc_customer_id = wc_order.get('customer_id', 0)
        billing = wc_order.get('billing', {})
        shipping = wc_order.get('shipping', {})
        email = CustomerMapper.extract_email(billing)

        # ── Registered customer ───────────────────────────────────────────────
        if wc_customer_id:
            binding = self._get_binding(backend, str(wc_customer_id))
            if binding:
                billing_partner = binding.odoo_id
            else:
                # Try to find by email first
                billing_partner = self._find_partner_by_email(email) if email else None
                if not billing_partner:
                    # Fetch customer from WC API
                    try:
                        client = backend._get_client()
                        wc_customer = client.get_customer(wc_customer_id)
                        billing_partner = self._create_partner(backend, wc_customer)
                        self.create({
                            'backend_id': backend.id,
                            'external_id': str(wc_customer_id),
                            'odoo_id': billing_partner.id,
                            'wc_email': email,
                            'sync_state': 'synced',
                            'last_sync': fields.Datetime.now(),
                        })
                    except Exception as exc:
                        _logger.warning(
                            '[WooCommerce] Could not fetch customer #%s, using billing data: %s',
                            wc_customer_id, exc,
                        )
                        billing_partner = self._create_partner_from_billing(backend, billing)

        # ── Guest order ───────────────────────────────────────────────────────
        else:
            billing_partner = self._find_partner_by_email(email) if email else None
            if not billing_partner:
                billing_partner = self._create_partner_from_billing(backend, billing)

        # ── Shipping address ──────────────────────────────────────────────────
        ship_country, ship_state = self._resolve_geo(
            shipping.get('country'), shipping.get('state')
        )
        shipping_partner = self._find_or_create_shipping_partner(
            billing_partner, shipping, ship_country, ship_state
        )

        return billing_partner, shipping_partner

    # ── Helpers ───────────────────────────────────────────────────────────────

    @api.model
    def _find_partner_by_email(self, email):
        """Return a res.partner with matching email, or None."""
        if not email:
            return None
        return self.env['res.partner'].search(
            [('email', '=ilike', email), ('active', '=', True)],
            limit=1,
        ) or None

    @api.model
    def _create_partner(self, backend, wc_customer):
        """Create a new res.partner from a WooCommerce customer dict."""
        country_id, state_id = self._resolve_geo(
            wc_customer.get('billing', {}).get('country'),
            wc_customer.get('billing', {}).get('state'),
        )
        vals = CustomerMapper.to_partner_vals(wc_customer, country_id=country_id, state_id=state_id)
        return self.env['res.partner'].create(vals)

    @api.model
    def _create_partner_from_billing(self, backend, billing):
        """Create a res.partner from order billing address."""
        country_id, state_id = self._resolve_geo(
            billing.get('country'), billing.get('state')
        )
        vals = CustomerMapper.billing_to_partner_vals(
            billing, country_id=country_id, state_id=state_id
        )
        return self.env['res.partner'].create(vals)

    @api.model
    def _find_or_create_shipping_partner(self, parent, shipping, country_id, state_id):
        """Find or create a delivery-type child partner for the shipping address."""
        # If shipping == billing address (common), reuse parent
        bill = parent
        if (
            (shipping.get('address_1') or '').strip().lower()
            == (bill.street or '').strip().lower()
            and (shipping.get('city') or '').strip().lower()
            == (bill.city or '').strip().lower()
        ):
            return parent

        # Look for existing delivery child
        existing = self.env['res.partner'].search([
            ('parent_id', '=', parent.id),
            ('type', '=', 'delivery'),
        ], limit=1)
        if existing:
            return existing

        vals = CustomerMapper.shipping_to_partner_vals(
            shipping, parent.id, country_id=country_id, state_id=state_id,
        )
        return self.env['res.partner'].create(vals)

    @api.model
    def _resolve_geo(self, country_code, state_code):
        """Resolve country/state codes to Odoo IDs.

        :param country_code: ISO 3166-1 alpha-2 code (e.g. 'CA')
        :param state_code: ISO 3166-2 subdivision code (e.g. 'ON')
        :returns: (country_id or None, state_id or None)
        """
        country_id = None
        state_id = None
        if country_code:
            country = self.env['res.country'].search(
                [('code', '=', country_code.upper())], limit=1
            )
            if country:
                country_id = country.id
                if state_code:
                    state = self.env['res.country.state'].search([
                        ('country_id', '=', country_id),
                        ('code', '=', state_code.upper()),
                    ], limit=1)
                    if state:
                        state_id = state.id
        return country_id, state_id
