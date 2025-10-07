import logging
from woocommerce import API

from odoo import models, fields, api
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class EgEComInstance(models.Model):
    _inherit = 'eg.ecom.instance'
    _description = 'Api Integration'

    provider = fields.Selection(selection_add=[("eg_woocommerce", "Woocommerce")])
    consumer_key = fields.Char(string='Consumer Key')
    consumer_secret = fields.Char(string='Consumer Secret')
    woocommerce_version = fields.Selection([('wc/v1', 'Version-1'), ('wc/v2', 'Version-2'), ('wc/v3', 'Version-3')],
                                           string='WooCommerce Version')
    website_type = fields.Selection([('http', 'HTTP'), ('https', 'HTTPS')])
    timeout = fields.Integer(string='Timeout')
    product_backorder = fields.Selection([("no", "No"), ("notify", "Notify"), ("yes", "Yes")])
    product_status = fields.Selection(
        [("draft", "Draft"), ("pending", "Pending"), ("private", "Private"), ("publish", "Publish")])
    product_catalog_visibility = fields.Selection(
        [("visible", "Visible"), ("catalog", "Catalog"), ("search", "Search"), ("hidden", "Hidden")])
    product_tax_status = fields.Selection([('taxable', 'Taxable'), ('shipping', 'Shipping'), ('none', 'None')], )
    order_state_line_ids = fields.One2many(comodel_name='order.state.line',
                                           inverse_name='instance_id')  # TODO: Change name
    eg_discount_product_id = fields.Many2one(comodel_name='eg.product.product', string='Discount Product')
    last_order_date = fields.Datetime(string="Last Order Date", readonly=True)
    export_stock_date = fields.Datetime(string="Export Stock Date", readonly=True)

    def test_connection_of_instance(self):
        """
        In this test connection from woocommerce.
        :return: Nothing
        """
        if self.provider != "eg_woocommerce":
            return super(EgEComInstance, self).test_connection_of_instance()
        wcapi = self.get_wcapi_connection()
        woo_status = wcapi.get("").status_code
        if woo_status == 200:
            self.color = 10
            self.connection_message = "Connection is Successfully"
        else:
            self.color = 1
            self.connection_message = "Something is wrong !!! not connect to Woocommerce"

    def get_wcapi_connection(self):
        if self.website_type == 'http':
            wcapi = API(
                url=self.url,
                consumer_key=self.consumer_key,
                consumer_secret=self.consumer_secret,
                wp_api=True,
                version=self.woocommerce_version,
                timeout=self.timeout
            )
        else:
            wcapi = API(
                url=self.url,
                consumer_key=self.consumer_key,
                consumer_secret=self.consumer_secret,
                wp_api=True,
                version=self.woocommerce_version,
                query_string_auth=True,
                timeout=self.timeout
            )
        return wcapi

    def create_more_product(self):
        count = 150
        while count > 0:
            name = "Woo{}".format(count)
            self.env["product.template"].create({'name': name,
                                                 'list_price': 250.5,
                                                 'default_code': name,
                                                 'standard_price': 150.2,
                                                 'sale_ok': True,
                                                 'purchase_ok': True,
                                                 'weight': 1.2,
                                                 'type': 'product',
                                                 'qty_available': 180})
            count -= 1
