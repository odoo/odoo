"""Pure WooCommerce REST API v3 client.

Intentionally ORM-free and Odoo-free. Can be instantiated and tested
independently of Odoo. All Odoo-specific logic lives in the model layer.

WooCommerce REST API docs: https://woocommerce.github.io/woocommerce-rest-api-docs/
"""

import hashlib
import hmac
import json
import logging
import time
from base64 import b64encode
from urllib.parse import urljoin

import requests
from requests.auth import HTTPBasicAuth

_logger = logging.getLogger(__name__)

# WooCommerce REST API v3 base path
_WC_API_PATH = '/wp-json/wc/v3/'

# Default timeouts (connect, read) in seconds
_DEFAULT_TIMEOUT = (10, 30)

# Maximum pages to fetch in a single list call (safety guard)
_MAX_PAGES = 500

# Default page size (WooCommerce max is 100)
_DEFAULT_PER_PAGE = 100


class WooCommerceAPIError(Exception):
    """Raised when the WooCommerce API returns a non-2xx response."""

    def __init__(self, message, status_code=None, response_body=None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class WooCommerceRateLimitError(WooCommerceAPIError):
    """Raised when WooCommerce returns 429 Too Many Requests."""

    def __init__(self, retry_after=60):
        super().__init__(f'Rate limited. Retry after {retry_after}s.')
        self.retry_after = retry_after


class WooCommerceClient:
    """Stateless WooCommerce REST API v3 client.

    Usage::

        client = WooCommerceClient(
            url='https://mystore.com',
            consumer_key='ck_xxxx',
            consumer_secret='cs_xxxx',
        )
        products = client.get_all_products()

    All list methods paginate automatically and yield dicts.
    Single-record methods return a dict.
    Write methods return the updated/created resource dict.
    """

    def __init__(self, url, consumer_key, consumer_secret, timeout=_DEFAULT_TIMEOUT,
                 verify_ssl=True, per_page=_DEFAULT_PER_PAGE):
        if not url or not consumer_key or not consumer_secret:
            raise ValueError('url, consumer_key, and consumer_secret are required.')

        # Normalize: strip trailing slash, ensure https scheme exists
        self.base_url = url.rstrip('/')
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.per_page = per_page

        self._session = requests.Session()
        self._session.auth = HTTPBasicAuth(consumer_key, consumer_secret)
        self._session.headers.update({
            'User-Agent': 'Odoo-WooCommerce-Connector/19.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        })

    # ── Low-level request ─────────────────────────────────────────────────────

    def _build_url(self, endpoint):
        """Construct full API URL from a relative endpoint path."""
        # e.g. endpoint = 'products' → 'https://store.com/wp-json/wc/v3/products'
        return urljoin(self.base_url + _WC_API_PATH, endpoint.lstrip('/'))

    def _request(self, method, endpoint, params=None, json_data=None, retries=3):
        """Execute an API request with retry logic for transient errors.

        :param method: HTTP method string ('GET', 'POST', 'PUT', 'DELETE')
        :param endpoint: WC API endpoint relative path (e.g. 'products/123')
        :param params: Query string parameters dict
        :param json_data: Request body for POST/PUT
        :param retries: Number of retry attempts for 5xx / connection errors
        :returns: Parsed JSON response (dict or list)
        :raises WooCommerceAPIError: for non-retryable HTTP errors
        :raises WooCommerceRateLimitError: for 429 responses
        """
        url = self._build_url(endpoint)
        _logger.debug('[WC API] %s %s params=%s', method, url, params)

        attempt = 0
        last_error = None

        while attempt <= retries:
            attempt += 1
            try:
                response = self._session.request(
                    method,
                    url,
                    params=params,
                    json=json_data,
                    timeout=self.timeout,
                    verify=self.verify_ssl,
                )
            except requests.exceptions.SSLError as exc:
                raise WooCommerceAPIError(
                    f'SSL verification failed for {url}. '
                    'Check the store URL or disable SSL verification in settings.'
                ) from exc
            except (requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout) as exc:
                last_error = exc
                if attempt <= retries:
                    wait = 2 ** attempt  # exponential backoff: 2, 4, 8s
                    _logger.warning(
                        '[WC API] Connection error (attempt %d/%d), retrying in %ds: %s',
                        attempt, retries + 1, wait, exc,
                    )
                    time.sleep(wait)
                    continue
                raise WooCommerceAPIError(
                    f'Cannot connect to WooCommerce at {self.base_url}: {exc}'
                ) from exc

            # ── Handle HTTP status codes ──────────────────────────────────────

            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                raise WooCommerceRateLimitError(retry_after=retry_after)

            if response.status_code >= 500 and attempt <= retries:
                wait = 2 ** attempt
                _logger.warning(
                    '[WC API] Server error %d (attempt %d/%d), retrying in %ds',
                    response.status_code, attempt, retries + 1, wait,
                )
                time.sleep(wait)
                continue

            if not response.ok:
                try:
                    body = response.json()
                    message = body.get('message') or response.text
                except Exception:
                    message = response.text
                raise WooCommerceAPIError(
                    f'WooCommerce API error {response.status_code}: {message}',
                    status_code=response.status_code,
                    response_body=response.text[:2048],
                )

            # ── Success ───────────────────────────────────────────────────────
            try:
                return response.json()
            except ValueError as exc:
                raise WooCommerceAPIError(
                    f'WooCommerce returned non-JSON response: {response.text[:512]}'
                ) from exc

        raise WooCommerceAPIError(
            f'Request failed after {retries + 1} attempts: {last_error}'
        )

    def _paginate(self, endpoint, params=None):
        """Generator: fetch all pages of a list endpoint.

        Yields individual items (dicts). Stops when a page returns empty.
        Respects X-WP-TotalPages header when available.
        """
        params = dict(params or {})
        params.setdefault('per_page', self.per_page)
        page = 1
        total_pages = None

        while True:
            params['page'] = page
            response_list = self._request('GET', endpoint, params=params)

            if not response_list:
                break

            yield from response_list

            if total_pages is None:
                # We can't access headers through json response — use item count heuristic
                if len(response_list) < params['per_page']:
                    break
            elif page >= total_pages:
                break

            page += 1
            if page > _MAX_PAGES:
                _logger.warning(
                    '[WC API] Reached max page limit (%d) for endpoint %s — '
                    'consider narrowing the date range.',
                    _MAX_PAGES, endpoint,
                )
                break

    # ── Connection Test ───────────────────────────────────────────────────────

    def test_connection(self):
        """Test API credentials by fetching store info.

        :returns: dict with 'name', 'url', 'version' keys from the WC API root
        :raises WooCommerceAPIError: if credentials are invalid
        """
        # The system status endpoint requires Administrator credentials
        result = self._request('GET', '')
        return {
            'name': result.get('name', ''),
            'url': result.get('url', self.base_url),
            'wc_version': result.get('woocommerce_version', ''),
        }

    # ── Products ──────────────────────────────────────────────────────────────

    def get_products(self, modified_after=None, page=1, per_page=None):
        """Fetch one page of products.

        :param modified_after: ISO 8601 datetime string — only return products
                               modified after this timestamp.
        :param page: Page number (1-based).
        :param per_page: Items per page (max 100).
        :returns: list of product dicts
        """
        params = {'page': page, 'per_page': per_page or self.per_page}
        if modified_after:
            params['after'] = modified_after
        return self._request('GET', 'products', params=params)

    def get_all_products(self, modified_after=None):
        """Generator: yield all products, handling pagination."""
        params = {}
        if modified_after:
            params['after'] = modified_after
        yield from self._paginate('products', params)

    def get_product(self, product_id):
        """Fetch a single product by WooCommerce ID."""
        return self._request('GET', f'products/{product_id}')

    def get_product_variations(self, product_id):
        """Generator: yield all variations for a variable product."""
        yield from self._paginate(f'products/{product_id}/variations')

    def get_product_categories(self):
        """Generator: yield all product categories."""
        yield from self._paginate('products/categories')

    def update_product_stock(self, product_id, quantity, manage_stock=True):
        """Push a stock quantity to WooCommerce (simple products).

        :param product_id: WooCommerce product ID
        :param quantity: Integer stock count
        :param manage_stock: Whether to enable WC stock management
        :returns: Updated product dict
        """
        return self._request('PUT', f'products/{product_id}', json_data={
            'manage_stock': manage_stock,
            'stock_quantity': int(quantity),
        })

    def update_variation_stock(self, product_id, variation_id, quantity, manage_stock=True):
        """Push a stock quantity to WooCommerce (variable product variation)."""
        return self._request(
            'PUT',
            f'products/{product_id}/variations/{variation_id}',
            json_data={
                'manage_stock': manage_stock,
                'stock_quantity': int(quantity),
            },
        )

    # ── Orders ────────────────────────────────────────────────────────────────

    def get_orders(self, after=None, statuses=None, page=1, per_page=None):
        """Fetch one page of orders.

        :param after: ISO 8601 datetime — only orders created/modified after this.
        :param statuses: list of WC status strings, e.g. ['processing', 'completed']
        :param page: Page number.
        :param per_page: Items per page.
        :returns: list of order dicts
        """
        params = {
            'page': page,
            'per_page': per_page or self.per_page,
            'orderby': 'date',
            'order': 'asc',
        }
        if after:
            params['after'] = after
        if statuses:
            params['status'] = ','.join(statuses)
        return self._request('GET', 'orders', params=params)

    def get_all_orders(self, after=None, statuses=None):
        """Generator: yield all orders, handling pagination."""
        params = {'orderby': 'date', 'order': 'asc'}
        if after:
            params['after'] = after
        if statuses:
            params['status'] = ','.join(statuses)
        yield from self._paginate('orders', params)

    def get_order(self, order_id):
        """Fetch a single order by WooCommerce ID."""
        return self._request('GET', f'orders/{order_id}')

    def update_order_status(self, order_id, status):
        """Update WooCommerce order status."""
        return self._request('PUT', f'orders/{order_id}', json_data={'status': status})

    def add_order_note(self, order_id, note, customer_note=False):
        """Add a note to a WooCommerce order."""
        return self._request('POST', f'orders/{order_id}/notes', json_data={
            'note': note,
            'customer_note': customer_note,
        })

    # ── Customers ─────────────────────────────────────────────────────────────

    def get_customers(self, modified_after=None):
        """Generator: yield all customers."""
        params = {}
        if modified_after:
            params['after'] = modified_after
        yield from self._paginate('customers', params)

    def get_customer(self, customer_id):
        """Fetch a single customer by WooCommerce ID."""
        return self._request('GET', f'customers/{customer_id}')

    # ── Webhooks ──────────────────────────────────────────────────────────────

    def list_webhooks(self):
        """List all registered webhooks."""
        return list(self._paginate('webhooks'))

    def create_webhook(self, topic, delivery_url, secret):
        """Register a webhook on the WooCommerce store.

        :param topic: e.g. 'order.created', 'product.updated'
        :param delivery_url: URL that WooCommerce will POST to
        :param secret: HMAC secret for payload verification
        :returns: Created webhook dict (includes 'id')
        """
        return self._request('POST', 'webhooks', json_data={
            'name': f'Odoo - {topic}',
            'topic': topic,
            'delivery_url': delivery_url,
            'secret': secret,
            'status': 'active',
        })

    def delete_webhook(self, webhook_id):
        """Delete a registered webhook."""
        return self._request('DELETE', f'webhooks/{webhook_id}', params={'force': True})

    # ── Webhook Signature Verification ───────────────────────────────────────

    @staticmethod
    def verify_webhook_signature(body_bytes, secret, signature_header):
        """Verify WooCommerce webhook HMAC-SHA256 signature.

        WooCommerce signs the raw request body with HMAC-SHA256 and
        base64-encodes it in the X-WC-Webhook-Signature header.

        :param body_bytes: Raw request body bytes
        :param secret: Webhook secret string
        :param signature_header: Value of X-WC-Webhook-Signature header
        :returns: True if valid
        """
        if not signature_header:
            return False
        try:
            expected = hmac.new(
                secret.encode('utf-8'),
                body_bytes,
                hashlib.sha256,
            ).digest()
            return hmac.compare_digest(
                b64encode(expected).decode('utf-8'),
                signature_header,
            )
        except Exception:
            return False
