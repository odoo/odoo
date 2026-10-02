import logging
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta

from odoo import SUPERUSER_ID, _, api, fields, models

from ...components.backend_adapter import WooAPI, WooLocation

_logger = logging.getLogger(__name__)


IMPORT_DELTA_BUFFER = 30  # seconds


class WooBackend(models.Model):
    """Backend for WooCommerce"""

    _name = "woo.backend"
    _description = "WooCommerce Backend"
    _inherit = ["mail.thread", "connector.backend"]

    @api.model
    def _get_stock_field_id(self):
        """
        Get the ID of the 'virtual_available' field in the 'product.product'
        model.
        """
        field = self.env["ir.model.fields"].search(
            [("model", "=", "product.product"), ("name", "=", "virtual_available")],
            limit=1,
        )
        return field

    name = fields.Char(
        string="Name", required=True, help="Enter the name of the WooCommerce backend."
    )
    version = fields.Selection(
        selection=[("wc/v3", "V3")],
        default="wc/v3",
        required=True,
        help="Select the WooCommerce API version you want to use.",
    )
    default_limit = fields.Integer(
        string="Default Limit",
        default=10,
        help="Set the default limit for data imports.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company", required=True, string="Company"
    )
    sale_team_id = fields.Many2one(
        comodel_name="crm.team",
        string="Sales Team",
        help="Select the Sales Team to associate it with Sale Order.",
    )
    location = fields.Char(
        string="Location(Live)", help="Enter the Live Location for WooCommerce."
    )
    client_id = fields.Char(
        string="Client ID(Live)",
        help="Enter the Client ID for Live Mode (Username for Basic Authentication).",
    )
    client_secret = fields.Char(
        string="Secret key(Live)",
        help="Enter the Secret Key for Live Mode (Password for Basic Authentication).",
    )
    test_mode = fields.Boolean(
        string="Test Mode", default=True, help="Toggle between Test and Live modes."
    )
    test_location = fields.Char(
        string="Test Location", help="Enter the Test Location for WooCommerce."
    )
    test_client_id = fields.Char(
        string="Client ID",
        help="Enter the Client ID for Test Mode (Username for Basic Authentication).",
    )
    test_client_secret = fields.Char(
        string="Secret key",
        help="Enter the Secret Key for Test Mode (Password for Basic Authentication).",
    )
    mark_completed = fields.Boolean(
        string="Mark Order Completed On Delivery",
        help="""If Mark Completed is True,
        we can update the sale order status export functionality
        for WooCommerce orders whose status is not completed.""",
    )
    tracking_info = fields.Boolean(
        string="Send Tracking Information",
        help="""If Mark Completed is True, this field will be visible,
        and we can add tracking information at the DO (Delivery Order) level to
        update the sale order status as well as Tracking Info in WooCommerce.""",
    )
    import_orders_from_date = fields.Datetime(string="Import Orders from date")
    order_prefix = fields.Char(string="Sale Order Prefix", default="WOO_")
    import_products_from_date = fields.Datetime(
        string="Import products from date",
        help="""Specify the date and time to initiate the process of import for
        Basic, Grouped, and Variant type products.Only products modified or added
        after this date will be considered in the import.""",
    )
    import_products_tmpl_from_date = fields.Datetime(
        string="Import product Templates from date",
        help="""Specify the date and time to initiate the process of import for
        Product Templates.This includes Variable type products.Only templates
        modified or added after this date will be considered in the import.""",
    )
    without_sku = fields.Boolean(
        string="Allow Product without SKU",
        help="""If this Boolean is set to True, the system will import products
        that do not have an assigned SKU. Please enable this option if you want
        to include products without SKU in the import process.""",
    )
    product_categ_id = fields.Many2one(
        comodel_name="product.category",
        string="Product Category",
        required=True,
        help="Set Odoo Product Category for imported WooCommerce products.",
    )
    import_partners_from_date = fields.Datetime(string="Import partners from date")
    without_email = fields.Boolean(
        string="Allow Partners without Email",
        help="""When the boolean is 'True,' partners can be imported without needing
        an email address.""",
    )
    include_tax = fields.Boolean(string="Tax Include", readonly=True)
    woo_sale_status_ids = fields.Many2many(
        comodel_name="woo.sale.status",
        string="Filter Sale Orders Based on their Status",
        help="""Select the sale order statuses to filter during import.
        Only orders with the selected statuses will be imported.
        This allows you to narrow down which orders are imported based on their
         status.""",
    )
    default_product_type = fields.Selection(
        [
            ("consu", "Consumable"),
            ("service", "Service"),
            ("product", "Storable Product"),
        ],
        string="Default Product Type",
        default="consu",
        required=True,
    )

    default_shipping_method_id = fields.Many2one(
        comodel_name="delivery.carrier",
        string="Default Shipping Method",
        help="Select the default shipping method for imported orders.",
    )
    default_carrier_product_id = fields.Many2one(
        comodel_name="product.product",
        string="Default Carrier Product",
        domain=[("type", "=", "service")],
        help="""Select the default product delivery carrier for imported
        shipping methods.""",
    )
    default_fee_product_id = fields.Many2one(
        comodel_name="product.product",
        string="Default Fee Product",
        domain=[("type", "=", "service")],
        help="Select the default fee product for imported orders.",
    )
    update_stock_inventory = fields.Boolean()
    warehouse_id = fields.Many2one(
        comodel_name="stock.warehouse",
        string="Default Warehouse",
        check_company=True,
        help="Warehouse used Sale Order.",
    )
    product_stock_field_id = fields.Many2one(
        comodel_name="ir.model.fields",
        string="Product Stock Field",
        default=_get_stock_field_id,
        domain="[('model', 'in', ['product.product', 'product.template']),"
        " ('ttype', '=', 'float')]",
        help="Choose the field of the product which will be used for "
        "stock inventory updates.\nIf empty, Quantity Available "
        "is used.",
    )
    woo_setting_id = fields.Many2one(comodel_name="woo.settings")
    stock_update = fields.Boolean(related="woo_setting_id.stock_update")
    recompute_qty_step = fields.Integer(string="Recompute Quantity Batch", default=1000)
    access_token = fields.Char(string="Access Token(Live)", readonly=True)
    test_access_token = fields.Char(string="Access Token(Staging)", readonly=True)
    webhook_config = fields.Html(
        string="Webhook Configurations",
        readonly=True,
        compute="_compute_webhook_config",
    )
    stock_inventory_warehouse_ids = fields.Many2many(
        comodel_name="stock.warehouse",
        string="Stock Inventory Warehouse",
        help="Warehouse used to compute the stock quantities.",
    )
    process_return_automatically = fields.Boolean(
        help="""When set to 'True', returns associated with the sale order will be
        processed and validated automatically.""",
    )
    activity_user_id = fields.Many2one("res.users", string="Responsible User")

    @api.depends("test_mode", "test_access_token", "access_token")
    def _compute_webhook_config(self):
        """
        Compute method for creating dynamic Html Content for webhook configration
        tab
        """
        for record in self:
            web_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
            token = (
                record.test_access_token if record.test_mode else record.access_token
            )
            dynamic_html = """
            <div>
                <h2>Follow these steps to set up a WooCommerce webhook for
                bad_connector_woocommerce integration:</h2>
                <ol>
                    <li>Navigate to WooCommerce > Settings > Advanced > Webhooks.</li>
                    <li>Click "Add Webhook" and provide the following details:</li>
                </ol>
                <ul>
                    <li><strong>Name:</strong> Update Product</li>
                    <li><strong>Status:</strong> Active</li>
                    <li><strong>Topic:</strong> Product Update</li>
                    <li><strong>Delivery URL:</strong>
                        {web_url}/update_product/woo_webhook/{token}
                    </li>
                    <li><strong>API Version:</strong> WP REST API Integration V3</li>
                </ul>
                <p><strong>Note:</strong> Retrieve the Access Token from WooCommerce
                 Backends by navigating to Advanced Configuration > DEFAULT
                 CONFIGURATION.Customize the Delivery URL based on the desired
                 webhook type:</p>
                <ul>
                    <li>For "Update Order":
                        {web_url}/update_order/woo_webhook/{token}
                    </li>
                    <li>For "Create Order":
                        {web_url}/create_order/woo_webhook/{token}
                    </li>
                    <li>For "Create Product":
                        {web_url}/create_product/woo_webhook/{token}
                    </li>
                </ul>
            </div>
            """.format(
                web_url=web_url, token=token
            )
            record.webhook_config = dynamic_html

    force_import_partners = fields.Boolean(
        help="""If true, customers will be imported from Woocommerce,
        irrespective of whether the data is up-to-date or not."""
    )
    force_import_products = fields.Boolean(
        help="""If true, products will be imported from Woocommerce,
        irrespective of whether the data is up-to-date or not."""
    )
    force_import_variable_products = fields.Boolean(
        help="""If true, variable products will be imported from Woocommerce,
        irrespective of whether the data is up-to-date or not."""
    )

    @api.onchange("update_stock_inventory", "stock_update")
    def _onchange_update_stock_inventory(self):
        """
        Handle the update of stock inventory based on WooCommerce settings.
        If 'update_stock_inventory' is attempted to be set to True when 'stock_update'
        is False, it automatically sets 'update_stock_inventory' to False and displays
        a warning message.
        """
        if not self.stock_update and self.update_stock_inventory:
            self.update_stock_inventory = False
            return {
                "warning": {
                    "title": "Warning",
                    "message": "You cannot set 'update_stock_inventory' to True "
                    "when 'stock_update' is False in the WooCommerce settings "
                    "level for Mange Stock.",
                }
            }

    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Default Currency",
        help="Select the default Currency for imported products and orders.",
    )

    def _get_weight_uom_domain(self):
        """Return domain for 'weight_uom_id' based on category
        'uom.product_uom_categ_kgm'."""
        category_id = self.env.ref("uom.product_uom_categ_kgm")
        return [("category_id", "=", category_id.id)]

    weight_uom_id = fields.Many2one(
        "uom.uom",
        string="Weight UOM",
        domain=_get_weight_uom_domain,
        help="Select a weight unit of measure.",
    )

    def _get_length_uom_domain(self):
        """Return domain for 'dimension_uom_id' based on category
        'uom.uom_categ_length'."""
        category_id = self.env.ref("uom.uom_categ_length")
        return [("category_id", "=", category_id.id)]

    dimension_uom_id = fields.Many2one(
        "uom.uom",
        string="Dimension UOM",
        domain=_get_length_uom_domain,
        help="Select a dimension unit of measure.",
    )

    @api.onchange("company_id")
    def _onchange_company(self):
        """Set sale team id and warehouse id False everytime company_id is changed"""
        self.sale_team_id = False
        self.warehouse_id = False

    def get_filters(self, model=None):
        """New Method: Returns the filter"""
        # model: In case we want to update the filter based on the model name
        return {}

    def get_job_options(self, model=None, export=False, batch=True):
        """New Method: Returns the filter"""
        # model: In case we want to update the job options based on the model name
        return {}

    @api.model
    def create_activity(
        self, record, message, activity_type=None, date=None, user=None
    ):
        """generic method to create activity in given `record`"""
        if not record:
            return
        responsible_id = user and user.id or SUPERUSER_ID
        date = date or fields.Date.today()
        activity_type = activity_type or "mail.mail_activity_data_warning"
        message = message or _("Something wrong. Please check!!!")
        record.activity_schedule(
            activity_type,
            date,
            note=message,
            user_id=responsible_id,
        )

    def get_additional_filter(self):
        """Add Filter"""
        return {"page": 1, "per_page": self.default_limit}

    def _sync_from_date(
        self,
        model,
        from_date_field=None,
        filters=None,
        priority=None,
        date_field=None,
        export=False,
        with_delay=True,
        force=False,
        force_update_field=None,
        job_options=None,
        **kwargs
    ):
        """New Method: Generic Method to import/export records based on the params"""
        self.ensure_one()
        filters = filters or self.get_filters(model)
        filters.update(self.get_additional_filter())
        start_time = datetime.now()
        backend_vals = {}
        binding_model = self.env[model]
        from_date = self[from_date_field] if from_date_field else False
        if from_date:
            filters["modified_after"] = fields.Datetime.to_string(from_date)
            filters["dates_are_gmt"] = True
        if with_delay:
            job_options = job_options or self.get_job_options(
                binding_model, export=export, batch=True
            )
            if "description" not in job_options:
                description = (
                    binding_model.export_batch.__doc__ or "Preparing Batch Export Of"
                    if export
                    else binding_model.import_batch.__doc__
                    or "Preparing Batch Import Of"
                )
                job_options["description"] = self.get_queue_job_description(
                    description, binding_model._description
                )
            if priority or priority == 0:
                job_options["priority"] = priority
            binding_model = binding_model.with_company(self.company_id).with_delay(
                **job_options or {}
            )
        if export:
            self._export_from_date(
                binding_model,
                start_time,
                from_date_field=from_date_field,
                filters=filters,
                date_field=date_field,
                job_options=job_options,
                **kwargs
            )
        else:
            force = self[force_update_field] if force_update_field else False
            self._import_from_date(
                binding_model=binding_model,
                from_date_field=from_date_field,
                filters=filters,
                job_options=job_options,
                force=force,
                **kwargs
            )
            if force:
                backend_vals[force_update_field] = False
        if from_date_field:
            start_time = start_time - timedelta(seconds=IMPORT_DELTA_BUFFER)
            start_time = fields.Datetime.to_string(start_time)
            backend_vals.update({from_date_field: start_time})
        self.update_backend_vals(backend_vals, **kwargs)

    def update_backend_vals(self, backend_vals, **kwargs):
        """Method to write the backend values"""
        self.write(backend_vals)

    def get_queue_job_description(self, prefix, model):
        """New method that returns the queue job description"""
        if not prefix or not model:
            _logger.warning("Queue Job description may not be appropriate!")
        return "{} {}".format(prefix or "", model)

    def _import_from_date(
        self,
        binding_model,
        from_date_field,
        priority=None,
        filters=None,
        job_options=None,
        force=False,
        **kwargs
    ):
        """Method to add a filter based on the date."""
        binding_model.import_batch(
            backend=self,
            filters=filters,
            force=force,
            job_options=job_options,
            **kwargs
        )

    def toggle_test_mode(self):
        """Test Mode"""
        for record in self:
            record.test_mode = not record.test_mode

    @contextmanager
    def work_on(self, model_name, **kwargs):
        """Add the work on for woo."""
        self.ensure_one()
        location = self.location
        client_id = self.client_id
        client_secret = self.client_secret

        if self.test_mode:
            location = self.test_location
            client_id = self.test_client_id
            client_secret = self.test_client_secret

        woo_location = WooLocation(
            location=location,
            client_id=client_id,
            client_secret=client_secret,
            version=self.version,
            test_mode=self.test_mode,
        )

        with WooAPI(woo_location) as woo_api:
            with super(WooBackend, self).work_on(
                model_name, woo_api=woo_api, **kwargs
            ) as work:
                yield work

    def import_partners(self):
        """Import Partners from backend"""
        for backend in self:
            backend._sync_from_date(
                model="woo.res.partner",
                priority=5,
                export=False,
                force_update_field="force_import_partners",
            )
        return True

    @api.model
    def cron_import_partners(self, domain=None):
        """Cron for import_partners"""
        backend_ids = self.search(domain or [])
        backend_ids.import_partners()

    def import_products(self):
        """Import Products from backend"""
        for backend in self:
            backend._sync_from_date(
                model="woo.product.product",
                from_date_field="import_products_from_date",
                priority=5,
                export=False,
                force_update_field="force_import_products",
                filters={"type": "simple"},
            )
        return True

    @api.model
    def cron_import_products(self, domain=None):
        """Cron for import_products"""
        backend_ids = self.search(domain or [])
        backend_ids.import_products()

    def import_product_tags(self):
        """Import Product Tags from backend"""
        for backend in self:
            backend._sync_from_date(
                model="woo.product.tag",
                priority=5,
                export=False,
            )
        return True

    @api.model
    def cron_import_product_tags(self, domain=None):
        """Cron for import_product_tags"""
        backend_ids = self.search(domain or [])
        backend_ids.import_product_tags()

    def import_product_attributes(self):
        """Import Product Attribute from backend"""
        for backend in self:
            backend._sync_from_date(
                model="woo.product.attribute",
                priority=5,
                export=False,
            )
        return True

    @api.model
    def cron_import_product_attributes(self, domain=None):
        """Cron for import_product_attributes"""
        backend_ids = self.search(domain or [])
        backend_ids.import_product_attributes()

    def import_product_categories(self):
        """Import Product Category from backend"""
        for backend in self:
            backend._sync_from_date(
                model="woo.product.category",
                priority=5,
                export=False,
            )
        return True

    @api.model
    def cron_import_product_categories(self, domain=None):
        """Cron for import_product_categories"""
        backend_ids = self.search(domain or [])
        backend_ids.import_product_categories()

    def import_taxes(self):
        """Import Taxes from backend"""
        for backend in self:
            backend._sync_from_date(
                model="woo.tax",
                priority=5,
                export=False,
            )
        return True

    @api.model
    def cron_import_account_tax(self, domain=None):
        """Cron for import_taxes"""
        backend_ids = self.search(domain or [])
        backend_ids.import_taxes()

    def import_sale_orders(self):
        """Import Orders from backend"""
        for backend in self:
            filters = {}
            if backend.woo_sale_status_ids:
                status = backend.mapped("woo_sale_status_ids").mapped("code")
                filters = {
                    "status": ",".join(status),
                }
            backend._sync_from_date(
                model="woo.sale.order",
                from_date_field="import_orders_from_date",
                priority=5,
                filters=filters,
            )
        return True

    @api.model
    def cron_import_sale_orders(self, domain=None):
        """Cron for import_sale_orders"""
        backend_ids = self.search(domain or [])
        backend_ids.import_sale_orders()

    def export_sale_order_status(self):
        """Export Sale Order Status"""
        for backend in self:
            sale_orders = self.env["sale.order"].search(
                [
                    ("woo_bind_ids.backend_id", "=", backend.id),
                    ("is_final_status", "!=", True),
                    ("has_done_picking", "=", True),
                    ("woo_order_status_code", "!=", "refunded"),
                ]
            )
            for sale_order in sale_orders:
                sale_order.with_context(execute_from_cron=True).export_delivery_status()

    @api.model
    def cron_export_sale_order_status(self, domain=None):
        """Cron of Export sale order status"""
        if domain is None:
            domain = []
        domain.append(("mark_completed", "=", "True"))
        backend_ids = self.search(domain or [])
        backend_ids.export_sale_order_status()

    def sync_metadata(self):
        """Import the data regarding country, state and settings"""
        for backend in self:
            backend._sync_from_date(
                model="woo.res.country",
                priority=5,
                export=False,
            )
            backend._sync_from_date(
                model="woo.settings",
                priority=5,
                export=False,
            )
            backend._sync_from_date(
                model="woo.delivery.carrier",
                priority=5,
                export=False,
            )
            backend._sync_from_date(
                model="woo.payment.gateway",
                priority=5,
                export=False,
            )
        return True

    @api.model
    def cron_import_metadata(self, domain=None):
        """Cron for sync_metadata"""
        backend_ids = self.search(domain or [])
        backend_ids.sync_metadata()

    def _domain_for_update_product_stock_qty(self):
        """Domain to search WooCommerce product"""
        return [
            ("backend_id", "in", self.ids),
            ("detailed_type", "=", "product"),
            ("stock_management", "=", True),
            ("backend_id.update_stock_inventory", "=", True),
        ]

    def update_product_stock_qty(self):
        """Export the Stock Inventory"""
        domain = self._domain_for_update_product_stock_qty()
        woo_products = self.env["woo.product.product"].search(domain)
        woo_products.recompute_woo_qty()
        return True

    @api.model
    def cron_update_stock_qty(self, domain=None):
        """Cron for Update Stock qty"""
        backend_ids = self.search(domain or [])
        backend_ids.update_product_stock_qty()

    def import_product_templates(self):
        """Import Product templates from backend"""
        for backend in self:
            backend._sync_from_date(
                model="woo.product.template",
                from_date_field="import_products_tmpl_from_date",
                priority=5,
                force_update_field="force_import_variable_products",
                export=False,
                filters={"type": "variable"},
            )
        return True

    @api.model
    def cron_import_product_templates(self, domain=None):
        """Cron for import_product_templates"""
        backend_ids = self.search(domain or [])
        backend_ids.import_product_templates()

    def _domain_for_export_refund(self):
        """Domain to search WooCommerce Order Refunds"""
        return [
            ("sale_id.woo_bind_ids.backend_id", "in", self.ids),
            ("is_refund", "=", True),
            ("woo_return_bind_ids", "=", False),
            ("sale_id.woo_order_status_code", "!=", "refunded"),
        ]

    def export_refunds(self):
        """Export Refunds"""
        domain = self._domain_for_export_refund()
        woo_order_refunds = self.env["stock.picking"].search(domain)
        for woo_order_refund in woo_order_refunds:
            woo_order_refund.export_refund()
        return True

    @api.model
    def cron_export_refunds(self, domain=None):
        """Cron for export_refunds"""
        backend_ids = self.search(domain or [])
        backend_ids.export_refunds()

    def generate_token(self):
        """Generates a unique access token"""
        for backend in self:
            token = str(uuid.uuid4())
            if backend.test_mode:
                backend.test_access_token = token
            else:
                backend.access_token = token
