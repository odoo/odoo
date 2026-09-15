from collections import defaultdict
from uuid import uuid4

from odoo import SUPERUSER_ID, Command, _, api, fields, models, tools
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.http import request
from odoo.service.common import exp_version
from odoo.tools import SQL

from ..tools import debug_log as dbg
from odoo.addons.point_of_sale.models.pos_printer import format_epson_certified_domain

DEFAULT_LIMIT_LOAD_PRODUCT = 5000
DEFAULT_LIMIT_LOAD_PARTNER = 100


class PosConfig(models.Model):
    _name = "pos.config"
    _inherit = ["mixin.pos.bus", "mixin.pos.load"]
    _description = "Point of Sale Configuration"
    _check_company_auto = True

    def _get_default_warehouse(self):
        return self.env["stock.warehouse"].search(
            self.env["stock.warehouse"]._check_company_domain(self.env.company),
            limit=1,
        )

    def _default_warehouse_id(self):
        return self._get_default_warehouse().id

    def _default_picking_type_id(self):
        return self._get_default_warehouse().pos_type_id.id

    def _default_journal_id(self):
        return self.env["account.journal"]._get_or_create_company_account_journal()

    def _default_invoice_journal_id(self):
        return self.env["account.journal"].search(
            [
                *self.env["account.journal"]._check_company_domain(self.env.company),
                ("type", "=", "sale"),
            ],
            limit=1,
        )

    def _default_payment_method_ids(self):
        domain = [
            *self.env["pos.payment.method"]._check_company_domain(self.env.company),
            ("split_transactions", "=", False),
            "|",
            ("journal_id", "=", False),
            ("journal_id.currency_id", "in", (False, self.env.company.currency_id.id)),
        ]
        non_cash_pm = self.env["pos.payment.method"].search(
            domain + [("is_cash_count", "=", False)]
        )
        available_cash_pm = self.env["pos.payment.method"].search(
            domain + [("is_cash_count", "=", True), ("config_ids", "=", False)], limit=1
        )
        return non_cash_pm | available_cash_pm

    def _default_group_pos_manager_id(self):
        return self.env.ref("point_of_sale.group_pos_manager")

    def _default_group_pos_user_id(self):
        return self.env.ref("point_of_sale.group_pos_user")

    def _default_tip_product_id(self):
        tip_product_id = self.env.ref(
            "point_of_sale.product_product_tip", raise_if_not_found=False
        )
        if (
            not tip_product_id
            or not tip_product_id.sudo().active
            or (
                tip_product_id.sudo().company_id
                and tip_product_id.sudo().company_id != self.env.company
            )
        ):
            tip_product_id = self.env["product.product"].search(
                [
                    ("default_code", "=", "TIPS"),
                    ("active", "=", True),
                    ("company_id", "in", [False, self.env.company.id]),
                ],
                limit=1,
            )
        return tip_product_id

    name = fields.Char(
        string="Point of Sale",
        required=True,
        help="An internal identification of the point of sale.",
    )
    printer_ids = fields.Many2many(
        comodel_name="pos.printer",
        relation="pos_config_printer_rel",
        column1="config_id",
        column2="printer_id",
        string="Order Printers",
    )
    is_order_printer = fields.Boolean(string="Order Printer")
    is_installed_account_accountant = fields.Boolean(
        string="Is the Full Accounting Installed",
        compute="_compute_is_installed_account_accountant",
    )
    picking_type_id = fields.Many2one(
        comodel_name="stock.picking.type",
        string="Operation Type",
        default=_default_picking_type_id,
        required=True,
        domain=lambda self: [
            ("code", "=", "outgoing"),
            ("warehouse_id.company_id", "=", self.env.company.id),
        ],
        ondelete="restrict",
    )
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Point of Sale Journal",
        default=_default_journal_id,
        domain=[("type", "in", ("general", "sale"))],
        ondelete="restrict",
        check_company=True,
        help="Accounting journal used to post POS session journal entries and POS invoice payments.",
    )
    invoice_journal_id = fields.Many2one(
        comodel_name="account.journal",
        default=_default_invoice_journal_id,
        domain=[("type", "=", "sale")],
        check_company=True,
        help="Accounting journal used to create invoices.",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        compute="_compute_currency_id",
        compute_sudo=True,
        store=True,
    )
    order_seq_id = fields.Many2one(
        comodel_name="ir.sequence",
        string="Order Sequence",
        copy=False,
        readonly=True,
    )
    order_backend_seq_id = fields.Many2one(
        comodel_name="ir.sequence",
        string="Order Backend Sequence",
        copy=False,
        readonly=True,
    )
    order_line_seq_id = fields.Many2one(
        comodel_name="ir.sequence",
        string="Order Line Sequence",
        copy=False,
        readonly=True,
    )
    device_seq_id = fields.Many2one(
        comodel_name="ir.sequence",
        string="Device Sequence",
        copy=False,
        readonly=True,
    )
    iface_cashdrawer = fields.Boolean(
        string="Cashdrawer",
        help="Automatically open the cashdrawer.",
    )
    iface_electronic_scale = fields.Boolean(
        string="Electronic Scale",
        help="Enables Electronic Scale integration.",
    )
    iface_print_via_proxy = fields.Boolean(
        string="Print via Proxy",
        help="Bypass browser printing and prints via the hardware proxy.",
    )
    iface_scan_via_proxy = fields.Boolean(
        string="Scan via Proxy",
        help="Enable barcode scanning with a remotely connected barcode scanner and card swiping with a Vantiv card reader.",
    )
    iface_big_scrollbars = fields.Boolean(
        string="Large Scrollbars",
        help="For imprecise industrial touchscreens.",
    )
    iface_group_by_categ = fields.Boolean(
        string="Group products by categories",
        help="Display products grouped by categories.",
    )
    iface_print_auto = fields.Boolean(
        string="Automatic Receipt Printing",
        default=False,
        help="The receipt will automatically be printed at the end of each order.",
    )
    iface_print_skip_screen = fields.Boolean(
        string="Skip Preview Screen",
        default=True,
        help="The receipt screen will be skipped if the receipt can be printed automatically.",
    )
    iface_tax_included = fields.Selection(
        selection=[("subtotal", "Tax-Excluded Price"), ("total", "Tax-Included Price")],
        string="Tax Display",
        default="total",
        required=True,
    )
    iface_available_categ_ids = fields.Many2many(
        comodel_name="pos.category",
        string="Available PoS Product Categories",
        help="The point of sale will only display products which are within one of the selected category trees. If no category is specified, all available products will be shown",
    )
    customer_display_bg_img = fields.Image(
        string="Background Image",
        max_width=1920,
        max_height=1920,
    )
    customer_display_bg_img_name = fields.Char(string="Background Image Name")
    restrict_price_control = fields.Boolean(
        string="Restrict Price Modifications to Managers",
        help="Only users with Manager access rights for PoS app can modify the product prices on orders.",
    )
    is_margins_costs_accessible_to_every_user = fields.Boolean(
        string="Margins & Costs",
        default=False,
        help="When disabled, only PoS manager can view the margin and cost of product among the Product info.",
    )
    cash_control = fields.Boolean(
        string="Advanced Cash Control",
        compute="_compute_cash_control",
        help="Check the amount of the cashbox at opening and closing.",
    )
    set_maximum_difference = fields.Boolean(
        help="Set a maximum difference allowed between the expected and counted money during the closing of the session."
    )
    receipt_header = fields.Text(
        help="A short text that will be inserted as a header in the printed receipt."
    )
    receipt_footer = fields.Text(
        help="A short text that will be inserted as a footer in the printed receipt."
    )
    basic_receipt = fields.Boolean(
        help="Print basic ticket without prices. Can be used for gifts."
    )
    proxy_ip = fields.Char(
        string="IP Address",
        size=45,
        help="The hostname or ip address of the hardware proxy, Will be autodetected if left empty.",
    )
    active = fields.Boolean(default=True)
    uuid = fields.Char(
        default=lambda self: str(uuid4()),
        copy=False,
        readonly=True,
        help="A globally unique identifier for this pos configuration, used to prevent conflicts in client-generated data.",
    )
    session_ids = fields.One2many(
        comodel_name="pos.session",
        inverse_name="config_id",
        string="Sessions",
    )
    current_session_id = fields.Many2one(
        comodel_name="pos.session",
        compute="_compute_current_session",
    )
    current_session_state = fields.Char(compute="_compute_current_session")
    number_of_rescue_session = fields.Integer(
        string="Number of Rescue Session",
        compute="_compute_current_session",
    )
    last_session_closing_cash = fields.Float(compute="_compute_last_session")
    last_session_closing_date = fields.Date(compute="_compute_last_session")
    pos_session_username = fields.Char(compute="_compute_current_session_user")
    pos_session_state = fields.Char(compute="_compute_current_session_user")
    pos_session_duration = fields.Char(compute="_compute_current_session_user")
    pricelist_id = fields.Many2one(
        comodel_name="product.pricelist",
        string="Default Pricelist",
        help="The pricelist used if no customer is selected or if the customer has no Sale Pricelist configured if any.",
    )
    available_pricelist_ids = fields.Many2many(
        comodel_name="product.pricelist",
        string="Available Pricelists",
        help="Make several pricelists available in the Point of Sale. You can also apply a pricelist to specific customers from their contact form (in Sales tab). To be valid, this pricelist must be listed here as an available pricelist. Otherwise the default pricelist will apply.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        required=True,
    )
    group_pos_manager_id = fields.Many2one(
        comodel_name="res.groups",
        string="Point of Sale Manager Group",
        default=_default_group_pos_manager_id,
        help="This field is there to pass the id of the pos manager group to the point of sale client.",
    )
    group_pos_user_id = fields.Many2one(
        comodel_name="res.groups",
        string="Point of Sale User Group",
        default=_default_group_pos_user_id,
        help="This field is there to pass the id of the pos user group to the point of sale client.",
    )
    iface_tipproduct = fields.Boolean(string="Product tips")
    tip_product_id = fields.Many2one(
        comodel_name="product.product",
        default=_default_tip_product_id,
        check_company=True,
        help="This product is used as reference on customer receipts.",
    )
    fiscal_position_ids = fields.Many2many(
        comodel_name="account.fiscal.position",
        string="Fiscal Positions",
        help="This is useful for restaurants with onsite and take-away services that imply specific tax rates.",
    )
    default_fiscal_position_id = fields.Many2one(comodel_name="account.fiscal.position")
    default_bill_ids = fields.Many2many(
        comodel_name="pos.bill",
        string="Coins/Bills",
    )
    use_pricelist = fields.Boolean(string="Use a pricelist.")
    use_presets = fields.Boolean()
    default_preset_id = fields.Many2one(comodel_name="pos.preset")
    available_preset_ids = fields.Many2many(
        comodel_name="pos.preset",
        string="Available Presets",
    )
    tax_regime_selection = fields.Boolean(string="Tax Regime Selection value")
    limit_categories = fields.Boolean(string="Restrict Categories")
    module_pos_restaurant = fields.Boolean(string="Is a Bar/Restaurant")
    module_pos_avatax = fields.Boolean(
        string="AvaTax PoS Integration",
        help="Use automatic taxes mapping with Avatax in PoS",
    )
    module_pos_discount = fields.Boolean(string="Global Discounts")
    module_pos_appointment = fields.Boolean(string="Online Booking")
    is_posbox = fields.Boolean(string="PosBox")
    is_header_or_footer = fields.Boolean(string="Custom Header & Footer")
    module_pos_hr = fields.Boolean(help="Show employee login screen")
    amount_authorized_diff = fields.Float(
        string="Amount Authorized Difference",
        help="This field depicts the maximum difference allowed between the ending balance and the theoretical cash when "
        "closing a session, for non-POS managers. If this maximum is reached, the user will have an error message at "
        "the closing of his session saying that he needs to contact his manager.",
    )
    payment_method_ids = fields.Many2many(
        comodel_name="pos.payment.method",
        string="Payment Methods",
        default=lambda self: self._default_payment_method_ids(),
        copy=False,
    )
    company_has_template = fields.Boolean(
        string="Company has chart of accounts",
        compute="_compute_company_has_template",
    )
    current_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Current Session Responsible",
        compute="_compute_current_session_user",
    )
    other_devices = fields.Boolean(
        help="Connect devices to your PoS without an IoT Box."
    )
    rounding_method = fields.Many2one(
        comodel_name="account.cash.rounding",
        string="Cash rounding",
    )
    cash_rounding = fields.Boolean()
    only_round_cash_method = fields.Boolean(string="Only apply rounding on cash")
    has_active_session = fields.Boolean(compute="_compute_current_session")
    manual_discount = fields.Boolean(
        string="Line Discounts",
        default=True,
    )
    ship_later = fields.Boolean()
    warehouse_id = fields.Many2one(
        comodel_name="stock.warehouse",
        default=_default_warehouse_id,
        ondelete="restrict",
    )
    route_id = fields.Many2one(
        comodel_name="stock.route",
        string="Spefic route for products delivered later.",
    )
    picking_policy = fields.Selection(
        selection=[
            ("direct", "As soon as possible"),
            ("one", "When all products are ready"),
        ],
        string="Shipping Policy",
        default="direct",
        required=True,
        help="If you deliver all products at once, the delivery order will be scheduled based on the greatest "
        "product lead time. Otherwise, it will be based on the shortest.",
    )
    auto_validate_terminal_payment = fields.Boolean(
        default=True,
        help="Automatically validates orders paid with a payment terminal.",
    )
    trusted_config_ids = fields.Many2many(
        comodel_name="pos.config",
        relation="pos_config_trust_relation",
        column1="is_trusting",
        column2="is_trusted",
        string="Trusted Point of Sale Configurations",
        domain="[('company_id', '=', company_id)]",
    )
    show_product_images = fields.Boolean(
        default=True,
        help="Show product images in the Point of Sale interface.",
    )
    show_category_images = fields.Boolean(
        default=True,
        help="Show category images in the Point of Sale interface.",
    )
    note_ids = fields.Many2many(
        comodel_name="pos.note",
        string="Note Models",
        help="The predefined notes of this point of sale.",
    )
    module_pos_sms = fields.Boolean(
        string="SMS Enabled",
        help="Activate SMS feature for point_of_sale",
    )
    is_closing_entry_by_product = fields.Boolean(
        string="Closing Entry by product",
        help="Display the breakdown of sales lines by product in the automatically generated closing entry.",
    )
    order_edit_tracking = fields.Boolean(
        string="Track orders edits",
        default=False,
        help="Store edited orders in the backend",
    )
    last_data_change = fields.Datetime(
        string="Last Write Date",
        compute="_compute_last_data_change",
        store=True,
        readonly=True,
    )
    fallback_nomenclature_id = fields.Many2one(comodel_name="barcode.nomenclature")
    epson_printer_ip = fields.Char(
        string="Epson Printer IP",
        help="Local IP address of an Epson receipt printer, or its serial number if the "
        "'Automatic Certificate Update' option is enabled in the printer settings.",
    )
    use_fast_payment = fields.Boolean(
        string="Fast Payment Validation",
        help="Enable fast payment methods to validate orders on the product screen.",
    )
    fast_payment_method_ids = fields.Many2many(
        comodel_name="pos.payment.method",
        relation="pos_payment_method_config_fast_validation_relation",
        string="Fast Payment Methods",
        compute="_compute_fast_payment_method_ids",
        store=True,
        readonly=False,
        help="These payment methods will be available for fast payment",
    )
    statistics_for_current_session = fields.Json(
        string="Session Statistics",
        compute="_compute_statistics_for_current_session",
    )

    def _get_next_order_refs(self, device_identifier="0"):
        next_number = self.order_backend_seq_id._next()
        year_2_digits = fields.Datetime.context_timestamp(
            self, fields.Datetime.now()
        ).strftime("%y")
        digits = "".join(c for c in next_number if c.isdigit()) or "0"
        tracking_number = f"{int(digits) % 1000}"
        dbg.logic.debug(
            "[config:%s] next order refs: seq=%s device=%s -> %s / %s",
            self.id,
            next_number,
            device_identifier,
            f"{year_2_digits}{device_identifier}-{self.id}-{next_number}",
            tracking_number,
        )
        return (
            f"{year_2_digits}{device_identifier}-{self.id}-{next_number}",
            tracking_number,
        )

    def notify_synchronisation(self, session_id, device_identifier, records=None):
        if records is None:
            records = {}
        self.check_singleton()
        static_records = {}
        self._check_trusted_config_compatibility()

        for model, ids in records.items():
            browsed = self.env[model].browse(ids).exists()
            static_records[model] = self.env[model]._load_pos_data_read(browsed, self)

        dbg.pipeline.debug(
            "[config:%s] SYNCHRONISATION -> session=%s device=%s records=%s trusted=%s",
            self.id,
            session_id,
            device_identifier,
            dbg.lazy(lambda: {k: len(v) for k, v in records.items()}),
            self.trusted_config_ids.ids,
        )
        self._notify(
            "SYNCHRONISATION",
            {
                "static_records": static_records,
                "session_id": session_id,
                "device_identifier": device_identifier,
                "records": records,
            },
        )

        for config in self.trusted_config_ids:
            config._notify(
                "SYNCHRONISATION",
                {
                    "static_records": static_records,
                    "session_id": config.current_session_id.id,
                    "device_identifier": 0,
                    "records": records,
                },
            )

    @dbg.timed
    def read_config_open_orders(self, domain, record_ids=None):
        self.check_singleton()
        if record_ids is None:
            record_ids = {}
        delete_record_ids = {}
        dynamic_records = {}

        for model in dict.fromkeys([*domain, *record_ids]):
            ids = record_ids.get(model, [])
            browsed = self.env[model].browse(ids)
            existing = browsed.exists()

            if model in domain:
                dynamic_records[model] = self.env[model].search(domain[model])  # noqa: E8507 - one query per model
            delete_record_ids[model] = (browsed - existing).ids
            if model == "pos.order":
                delete_record_ids[model] += (
                    existing._filtered_access("read")
                    .filtered(lambda r: r.state == "cancel")
                    .ids
                )
            dbg.logic.debug(
                "[config:%s] open orders %s: %d known, %s found, %d to delete",
                self.id,
                model,
                len(ids),
                dbg.rec(dynamic_records.get(model, self.env[model])),
                len(delete_record_ids[model]),
            )

        pos_order_data = dynamic_records.get("pos.order") or self.env["pos.order"]
        data = pos_order_data.read_pos_data([], self)

        for key, records in dynamic_records.items():
            rows_by_id = {row["id"]: row for row in data.get(key, [])}
            serialized = self.env[key].browse(rows_by_id)
            missing = records - serialized
            if missing:
                rows_by_id.update(
                    {
                        row["id"]: row
                        for row in self.env[key]._load_pos_data_read(missing, self)
                    }
                )
            dynamic_records[key] = [
                rows_by_id[record_id]
                for record_id in (records | serialized).ids
                if record_id in rows_by_id
            ]

        for key, value in data.items():
            if key not in dynamic_records:
                dynamic_records[key] = value

        return {
            "dynamic_records": dynamic_records,
            "deleted_record_ids": delete_record_ids,
        }

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [("id", "=", config.id)]

    @dbg.timed
    def get_pos_ui_product_pricelist_item_by_product(
        self, product_tmpl_ids, product_ids
    ):
        self.check_singleton()
        items = self.env["product.pricelist.item"].search(
            [
                "&",
                ("pricelist_id", "in", self._get_available_pricelists().ids),
                *self.env["product.pricelist.item"]._check_company_domain(
                    self.company_id
                ),
                "|",
                "&",
                ("product_id", "=", False),
                ("product_tmpl_id", "in", product_tmpl_ids),
                ("product_id", "in", product_ids),
            ]
        )
        return {
            "product.pricelist.item": items.read(
                self.env["product.pricelist.item"]._load_pos_data_fields(self),
                load=False,
            ),
            "product.pricelist": items.pricelist_id.read(
                self.env["product.pricelist"]._load_pos_data_fields(self), load=False
            ),
        }

    @api.model
    def _get_pos_client_computed_fields(self):
        return {"cash_control", "current_session_id", "display_name"}

    @api.model
    def _get_pos_client_excluded_fields(self):
        return {"session_ids"}

    @api.model
    def _load_pos_data_fields(self, config):
        computed = self._get_pos_client_computed_fields()
        excluded = self._get_pos_client_excluded_fields()
        return [
            name
            for name, field in self._fields.items()
            if name not in excluded
            and field.type != "binary"
            and (field.store or name in computed)
        ]

    @api.model
    def _load_pos_data_read(self, records, config):
        read_records = super()._load_pos_data_read(records, config)
        if not read_records:
            return read_records

        record = read_records[0]
        record["_server_version"] = exp_version()
        record["_base_url"] = config.get_base_url()
        record["access_token"] = config.access_token
        record["_data_server_date"] = (
            self.env.context.get("pos_last_server_date") or self.env.cr.now()
        )
        record["_has_cash_move_perm"] = self.env.user.has_group(
            "account.group_account_invoice"
        )
        record["_has_cash_delete_perm"] = self.env.user.has_group(
            "account.group_account_basic"
        )
        record["_pos_special_products_ids"] = config._get_special_products().ids

        taxes = self.env["account.tax"].search(
            self.env["account.tax"]._load_pos_data_domain({}, config)
        )
        product_fields = taxes._eval_taxes_computation_prepare_product_fields()
        record["_product_default_values"] = self.env[
            "account.tax"
        ]._eval_taxes_computation_prepare_product_default_values(product_fields)

        if not record["use_pricelist"]:
            record["pricelist_id"] = False
        record["_IS_VAT"] = (
            config.company_id.country_id.id
            in self.env.ref("base.europe").country_ids.ids
        )
        dbg.logic.debug(
            "[config:%s] client record: server_date=%s cash_move=%s cash_delete=%s"
            " special_products=%s pricelist=%s vat=%s",
            config.id,
            record["_data_server_date"],
            record["_has_cash_move_perm"],
            record["_has_cash_delete_perm"],
            record["_pos_special_products_ids"],
            record["pricelist_id"],
            record["_IS_VAT"],
        )
        return read_records

    @api.depends("payment_method_ids")
    def _compute_fast_payment_method_ids(self):
        for config in self:
            config.fast_payment_method_ids = config.fast_payment_method_ids.filtered(
                lambda pm, config=config: pm.id in config.payment_method_ids.ids
            )

    @api.constrains("use_fast_payment")
    def _check_fast_payment_methods(self):
        for config in self:
            if config.use_fast_payment and not config.fast_payment_method_ids:
                raise ValidationError(
                    _(
                        "Fast payment validation on the point of sale %s needs at "
                        "least one fast payment method.",
                        config.name,
                    )
                )

    @api.depends("payment_method_ids.is_cash_count")
    def _compute_cash_control(self):
        for config in self:
            config.cash_control = bool(
                config.payment_method_ids.filtered("is_cash_count")
            )

    @api.depends("company_id.chart_template", "company_id.root_id.chart_template")
    def _compute_company_has_template(self):
        for config in self:
            root = config.company_id.root_id.sudo()
            config.company_has_template = bool(
                config.company_id.chart_template
                or root.chart_template
                or root._existing_accounting()
            )
            dbg.logic.debug(
                "[config:%s] chart available=%s company_chart=%s root_chart=%s",
                config.id,
                config.company_has_template,
                config.company_id.chart_template,
                root.chart_template,
            )

    def _compute_is_installed_account_accountant(self):
        accounting = (
            self.env["ir.module.module"]
            .sudo()
            .search([("name", "=", "account"), ("state", "=", "installed")])
        )
        for pos_config in self:
            pos_config.is_installed_account_accountant = bool(accounting)

    @api.depends(
        "journal_id.currency_id",
        "journal_id.company_id.currency_id",
        "company_id",
        "company_id.currency_id",
    )
    def _compute_currency_id(self):
        for pos_config in self:
            if pos_config.journal_id:
                pos_config.currency_id = (
                    pos_config.journal_id.currency_id.id
                    or pos_config.journal_id.company_id.sudo().currency_id.id
                )
            else:
                pos_config.currency_id = pos_config.company_id.sudo().currency_id.id

    def _get_open_sessions(self):
        persisted = self.filtered("id")
        sessions = (
            self.env["pos.session"].search_fetch(
                [("config_id", "in", persisted.ids), ("state", "!=", "closed")],
                ["config_id", "state", "rescue"],
            )
            if persisted
            else self.env["pos.session"]
        )
        # Onchange records can contain sessions that have not reached the database.
        return sessions | (self - persisted).session_ids.filtered(
            lambda session: session.state != "closed"
        )

    @api.depends("session_ids", "session_ids.state", "session_ids.rescue")
    def _compute_current_session(self):
        sessions_by_config = (
            self.filtered("id")._get_open_sessions().grouped("config_id")
        )
        for pos_config in self:
            open_sessions = (
                sessions_by_config.get(pos_config, self.env["pos.session"])
                if pos_config.id
                else pos_config._get_open_sessions()
            )
            session = open_sessions.filtered(lambda s: not s.rescue)[:1]
            pos_config.has_active_session = bool(open_sessions)
            pos_config.current_session_id = session
            pos_config.current_session_state = session.state or False
            pos_config.number_of_rescue_session = len(open_sessions.filtered("rescue"))
            dbg.logic.debug(
                "[config:%s] current session %s state=%s rescue=%d",
                pos_config.id,
                session.id,
                session.state or None,
                pos_config.number_of_rescue_session,
            )

    @api.depends_context("tz", "lang", "uid")
    @api.depends(
        "current_session_id",
        "session_ids.start_at",
        "session_ids.cash_register_balance_start",
        "session_ids.order_ids.state",
        "session_ids.order_ids.amount_total",
        "session_ids.order_ids.is_refund",
        "session_ids.order_ids.refunded_order_id",
        "currency_id",
        "currency_id.symbol",
        "currency_id.position",
        "currency_id.rounding",
        "currency_id.decimal_places",
    )
    def _compute_statistics_for_current_session(self):
        for config in self:
            session = config.current_session_id
            config.statistics_for_current_session = (
                config._get_statistics_for_session(session) if session else False
            )

    def _get_statistics_for_session(self, session):
        self.check_singleton()
        currency = self.currency_id
        statistics = {
            "cash": {
                "raw_opening_cash": session.cash_register_balance_start,
                "opening_cash": currency.format(session.cash_register_balance_start),
            },
            "date": {
                "is_started": bool(session.start_at),
                "start_date": fields.Datetime.context_timestamp(
                    self, session.start_at
                ).strftime("%b %d")
                if session.start_at
                else False,
            },
            "orders": {
                "paid": False,
                "draft": False,
            },
        }

        all_paid_orders = session.order_ids.filtered(
            lambda o: o.state in ["paid", "done"]
        )
        refund_orders = all_paid_orders.filtered(lambda o: o.is_refund)
        draft_orders = session.order_ids.filtered(lambda o: o.state == "draft")
        non_refund_orders = all_paid_orders - refund_orders

        refund_totals = defaultdict(float)
        for refund in refund_orders:
            if refund.refunded_order_id:
                refund_totals[refund.refunded_order_id.id] += abs(refund.amount_total)

        paid_order_count = sum(
            1
            for order in non_refund_orders
            if order.id not in refund_totals
            or currency.compare_amounts(
                refund_totals.get(order.id, 0.0), order.amount_total
            )
        )

        total_paid = currency.round(sum(all_paid_orders.mapped("amount_total")))
        if paid_order_count or not currency.is_zero(total_paid):
            statistics["orders"]["paid"] = self._prepare_order_statistics(
                currency, total_paid, paid_order_count
            )

        if draft_orders:
            total_draft = currency.round(sum(draft_orders.mapped("amount_total")))
            statistics["orders"]["draft"] = self._prepare_order_statistics(
                currency, total_draft, len(draft_orders)
            )

        return statistics

    def _prepare_order_statistics(self, currency, amount, count):
        formatted = currency.format(amount)
        return {
            "amount": amount,
            "count": count,
            "display": (
                _("%(amount)s (%(count)s order)", amount=formatted, count=count)
                if count == 1
                else _("%(amount)s (%(count)s orders)", amount=formatted, count=count)
            ),
        }

    @api.depends_context("tz", "uid")
    @api.depends(
        "session_ids.state",
        "session_ids.stop_at",
        "session_ids.cash_register_balance_end_real",
    )
    def _compute_last_session(self):
        last_by_config = {}
        for group in self.env["pos.session"]._read_group(
            [
                ("config_id", "in", self.ids),
                ("state", "=", "closed"),
                ("stop_at", "!=", False),
            ],
            groupby=["config_id"],
            aggregates=["stop_at:max"],
        ):
            last_by_config[group[0].id] = group[1]

        sessions = self.env["pos.session"].search(
            [
                ("config_id", "in", list(last_by_config)),
                ("stop_at", "in", list(last_by_config.values())),
                ("state", "=", "closed"),
            ]
        )
        balance_by_config = {
            session.config_id.id: session.cash_register_balance_end_real
            for session in sessions.sorted(
                lambda session: (session.stop_at, session.id)
            )
            if session.stop_at == last_by_config.get(session.config_id.id)
        }

        for pos_config in self:
            stop_at = last_by_config.get(pos_config.id)
            pos_config.last_session_closing_date = (
                fields.Datetime.context_timestamp(pos_config, stop_at).date()
                if stop_at
                else False
            )
            pos_config.last_session_closing_cash = balance_by_config.get(
                pos_config.id, 0
            )

    @api.depends(
        "current_session_id",
        "session_ids.state",
        "session_ids.start_at",
        "session_ids.user_id.name",
    )
    def _compute_current_session_user(self):
        now = fields.Datetime.now()
        for pos_config in self:
            session = pos_config.current_session_id
            pos_config.pos_session_username = session.user_id.sudo().name or False
            pos_config.pos_session_state = session.state or False
            pos_config.pos_session_duration = str(
                (now - session.start_at).days if session.start_at else 0
            )
            pos_config.current_user_id = session.user_id

    @api.constrains("rounding_method", "cash_rounding")
    def _check_rounding_method_strategy(self):
        for config in self:
            if (
                config.cash_rounding
                and config.rounding_method
                and config.rounding_method.strategy != "add_invoice_line"
            ):
                selection_value = "Add a rounding line"
                for key, val in (
                    self.env["account.cash.rounding"]
                    ._fields["strategy"]
                    ._description_selection(config.env)
                ):
                    if key == "add_invoice_line":
                        selection_value = val
                        break
                raise ValidationError(
                    _(
                        "The cash rounding strategy of the point of sale %(pos)s must be: '%(value)s'",
                        pos=config.name,
                        value=selection_value,
                    )
                )

    def _check_profit_loss_cash_journal(self):
        if self.cash_control and self.payment_method_ids:
            for method in self.payment_method_ids:
                if method.is_cash_count and (
                    not method.journal_id.loss_account_id
                    or not method.journal_id.profit_account_id
                ):
                    raise ValidationError(
                        _("You need a loss and profit account on your cash journal.")
                    )

    @api.constrains("company_id", "payment_method_ids")
    def _check_company_payment(self):
        for config in self:
            if any(
                method.company_id != config.company_id
                for method in config.payment_method_ids
            ):
                raise ValidationError(
                    _(
                        "The payment methods for the point of sale %s must belong to its company.",
                        config.name,
                    )
                )

    @api.constrains(
        "pricelist_id",
        "use_pricelist",
        "available_pricelist_ids",
        "journal_id",
        "invoice_journal_id",
        "payment_method_ids",
        "company_id",
    )
    def _check_currencies(self):
        for config in self:
            if (
                config.use_pricelist
                and config.pricelist_id
                and config.pricelist_id not in config.available_pricelist_ids
            ):
                raise ValidationError(
                    _(
                        "The default pricelist must be included in the available pricelists."
                    )
                )

            for pm in config.payment_method_ids:
                if (
                    pm.journal_id
                    and pm.journal_id.currency_id
                    and pm.journal_id.currency_id != config.currency_id
                ):
                    raise ValidationError(
                        _(
                            "All payment methods must be in the same currency as the Sales Journal or the company currency if that is not set."
                        )
                    )

            if config.use_pricelist and any(
                config.available_pricelist_ids.mapped(
                    lambda pricelist, config=config: (
                        pricelist.currency_id != config.currency_id
                    )
                )
            ):
                raise ValidationError(
                    _(
                        "All available pricelists must be in the same currency as the company or"
                        " as the Sales Journal set on this point of sale if you use"
                        " the Accounting application."
                    )
                )
            if (
                config.invoice_journal_id.currency_id
                and config.invoice_journal_id.currency_id != config.currency_id
            ):
                raise ValidationError(
                    _(
                        "The invoice journal must be in the same currency as the Sales Journal or the company currency if that is not set."
                    )
                )

    def _check_payment_method_ids(self):
        self.check_singleton()
        if not self.payment_method_ids:
            raise ValidationError(
                _(
                    "You must have at least one payment method configured to launch a session."
                )
            )

    @api.constrains("company_id", "pricelist_id", "available_pricelist_ids")
    def _check_pricelists(self):
        for config in self.sudo():
            if (
                config.pricelist_id.company_id
                and config.pricelist_id.company_id != config.company_id
            ):
                raise ValidationError(
                    _(
                        "The default pricelist must belong to no company or the company of the point of sale."
                    )
                )

    @api.constrains("company_id", "available_pricelist_ids")
    def _check_companies(self):
        for config in self:
            if any(
                pricelist.company_id.id not in [False, config.company_id.id]
                for pricelist in config.available_pricelist_ids
            ):
                raise ValidationError(
                    _(
                        "The selected pricelists must belong to no company or the company of the point of sale."
                    )
                )

    def _check_company_has_template(self):
        self.check_singleton()
        if not self.company_has_template:
            raise ValidationError(
                _(
                    'No chart of account configured, go to the "configuration / settings" menu, and '
                    "install one from the Invoicing tab."
                )
            )

    @api.constrains("payment_method_ids")
    def _check_payment_method_ids_journal(self):
        for config in self:
            for cash_method in config.payment_method_ids.filtered(
                lambda m: m.journal_id.type == "cash"
            ):
                if cash_method.config_ids - config:
                    raise ValidationError(
                        _(
                            "This cash payment method is already used in another Point of Sale.\n"
                            "A new cash payment method should be created for this Point of Sale."
                        )
                    )
                if len(cash_method.journal_id.pos_payment_method_ids) > 1:
                    raise ValidationError(
                        _(
                            "You cannot use the same journal on multiples cash payment methods."
                        )
                    )

    @api.constrains("trusted_config_ids", "company_id", "journal_id")
    def _check_trusted_config_ids(self):
        configs = self.sudo().with_context(active_test=False)
        configs |= configs.search([("trusted_config_ids", "in", self.ids)])
        configs._check_trusted_config_compatibility()

    def _check_trusted_config_compatibility(self):
        for config in self:
            for trusted_config in config.trusted_config_ids:
                if trusted_config.company_id != config.company_id:
                    raise ValidationError(
                        _(
                            "You can only share open orders with configurations in the same company."
                        )
                    )
                if trusted_config.currency_id != config.currency_id:
                    raise ValidationError(
                        _(
                            "You cannot share open orders with configuration that does not use the same currency."
                        )
                    )

    def _check_header_footer(self, values):
        if (
            not self.env.is_admin()
            and {"is_header_or_footer", "receipt_header", "receipt_footer"}
            & values.keys()
        ):
            raise AccessError(
                _("Only administrators can edit receipt headers and footers")
            )

    def _check_company_has_fiscal_country(self):
        self.check_singleton()
        if not self.company_id.account_fiscal_country_id:
            raise ValidationError(_("The company must have a fiscal country set."))

    _COMPANY_DEPENDENT_DEFAULTS = (
        "picking_type_id",
        "warehouse_id",
        "journal_id",
        "invoice_journal_id",
        "payment_method_ids",
        "tip_product_id",
    )

    def _add_company_defaults(self, vals):
        company = self.env["res.company"].browse(vals["company_id"])
        defaults = self.with_company(company).default_get(
            list(self._COMPANY_DEPENDENT_DEFAULTS)
        )
        for field_name in self._COMPANY_DEPENDENT_DEFAULTS:
            if field_name not in vals and field_name in defaults:
                vals[field_name] = defaults[field_name]

    def _get_or_create_company_warehouse(self, company, name):
        Warehouse = self.env["stock.warehouse"]
        warehouse = Warehouse.search(Warehouse._check_company_domain(company), limit=1)
        if warehouse:
            return warehouse
        dbg.logic.debug(
            "no warehouse for company %s: creating one for config %r", company.id, name
        )
        return Warehouse.create({"code": (name or "POS")[:3], "company_id": company.id})

    @dbg.timed
    @api.model_create_multi
    def create(self, vals_list):
        dbg.lifecycle.debug(
            "pos.config.create: %d vals, keys=%s",
            len(vals_list),
            dbg.vals_keys(vals_list),
        )
        for vals in vals_list:
            company = (
                self.env["res.company"].browse(vals["company_id"])
                if vals.get("company_id")
                else self.env.company
            )
            self._get_or_create_company_warehouse(company, vals.get("name"))
            if vals.get("company_id") and vals["company_id"] != self.env.company.id:
                dbg.logic.debug(
                    "pos.config.create: company %s differs from env company %s,"
                    " defaults recomputed",
                    vals["company_id"],
                    self.env.company.id,
                )
                self._add_company_defaults(vals)
        for vals in vals_list:
            self._check_header_footer(vals)

        pos_configs = super().create(vals_list)
        for config in pos_configs:
            if not config.payment_method_ids:
                _dummy, payment_methods = config.with_company(
                    config.company_id
                )._create_journal_and_payment_methods()
                dbg.logic.debug(
                    "[config:%s] no payment methods given: created %s",
                    config.id,
                    payment_methods,
                )
                config.payment_method_ids = self.env["pos.payment.method"].browse(
                    payment_methods
                )
        pos_configs._create_sequences()
        pos_configs.sudo()._install_missing_modules()
        pos_configs._update_preparation_printers_menuitem_visibility()
        dbg.lifecycle.debug("pos.config.create: created %s", dbg.rec(pos_configs))
        return pos_configs

    _SEQUENCE_SPECS = (
        ("order_seq_id", "pos.order", 6),
        ("order_backend_seq_id", "pos.order.backend", 6),
        ("order_line_seq_id", "pos.order.line", 6),
        ("device_seq_id", "pos.device", 0),
    )

    def _get_sequence_name(self, field_name):
        self.check_singleton()
        return {
            "order_seq_id": _("POS order from config #%s", self.id),
            "order_backend_seq_id": _("POS order backend from config #%s", self.id),
            "order_line_seq_id": _("POS order line from config #%s", self.id),
            "device_seq_id": _("POS device from config #%s", self.id),
        }[field_name]

    def _prepare_sequence_vals(self, field_name, code, padding):
        self.check_singleton()
        return {
            "name": self._get_sequence_name(field_name),
            "code": code,
            "padding": padding,
            "company_id": self.company_id.id,
            "implementation": "no_gap",
        }

    def _create_sequences(self):
        vals_list = [
            pos_config._prepare_sequence_vals(field_name, code, padding)
            for pos_config in self
            for field_name, code, padding in self._SEQUENCE_SPECS
        ]
        sequences = self.env["ir.sequence"].sudo().create(vals_list)
        for index, pos_config in enumerate(self):
            offset = index * len(self._SEQUENCE_SPECS)
            for position, (field_name, _code, _padding) in enumerate(
                self._SEQUENCE_SPECS
            ):
                pos_config[field_name] = sequences[offset + position]

    def _get_next_session_name(self):
        self.check_singleton()
        sequence = (
            self.env["ir.sequence"]
            .sudo()
            .search(
                [
                    ("code", "=", "pos.session"),
                    ("company_id", "in", [self.company_id.id, False]),
                ],
                order="company_id, id",
                limit=1,
            )
        )
        if not sequence:
            dbg.logic.debug("[config:%s] no pos.session sequence: name '/'", self.id)
            return "/"
        prefix = self.name if sequence.prefix == "/" else ""
        dbg.logic.debug(
            "[config:%s] session sequence=%s company=%s active_company=%s",
            self.id,
            sequence.id,
            self.company_id.id,
            self.env.company.id,
        )
        return f"{prefix}{sequence.next_by_id()}"

    def register_new_device_identifier(self):
        self.check_singleton()
        identifier = self.sudo().device_seq_id._next()
        dbg.lifecycle.debug("[config:%s] device registered: %s", self.id, identifier)
        return {
            "device_identifier": identifier,
        }

    def _update_vals_default_tip_product(self, vals):
        if (
            "tip_product_id" in vals
            and not vals["tip_product_id"]
            and "iface_tipproduct" in vals
            and vals["iface_tipproduct"]
        ):
            companies = (
                self.env["res.company"].browse(vals.get("company_id"))
                or self.company_id
                or self.env.company
            )
            defaults = {
                company: self.with_company(company)._default_tip_product_id()
                for company in companies
            }
            if not all(defaults.values()):
                raise UserError(
                    _(
                        "The default tip product is missing. Please manually specify the tip product. (See Tips field.)"
                    )
                )
            product_ids = {product.id for product in defaults.values()}
            if len(product_ids) == 1:
                vals["tip_product_id"] = product_ids.pop()
            else:
                vals.pop("tip_product_id")
                return [
                    (configs, defaults[company])
                    for company, configs in self.grouped("company_id").items()
                ]
        return []

    def _update_preparation_printers_menuitem_visibility(self):
        prepa_printers_menuitem = self.sudo().env.ref(
            "point_of_sale.menu_pos_preparation_printer", raise_if_not_found=False
        )
        if prepa_printers_menuitem:
            prepa_printers_menuitem.active = (
                self.sudo()
                .env["pos.config"]
                .search_count(
                    [("is_order_printer", "=", True), ("active", "=", True)], limit=1
                )
                > 0
            )

    @api.depends(
        "use_pricelist",
        "pricelist_id",
        "available_pricelist_ids",
        "payment_method_ids",
        "limit_categories",
        "iface_available_categ_ids",
        "module_pos_hr",
        "module_pos_discount",
        "iface_tipproduct",
        "default_preset_id",
        "module_pos_appointment",
    )
    def _compute_last_data_change(self):
        self.last_data_change = self.env.cr.now()

    def write(self, vals):
        vals = dict(vals)
        dbg.lifecycle.debug(
            "pos.config.write: %s keys=%s from_settings=%s",
            dbg.rec(self),
            dbg.keys(vals),
            bool(self.env.context.get("from_settings_view")),
        )
        self._check_header_footer(vals)
        tip_updates = self._update_vals_default_tip_product(vals)
        if "is_order_printer" in vals and not vals["is_order_printer"]:
            vals["printer_ids"] = [fields.Command.clear()]

        self._update_vals_x2many_from_settings_view(vals)
        vals = self._prepare_vals_changed(vals)
        self._check_session_forbidden_changes(vals)

        for configs, product in tip_updates:
            configs.write({"tip_product_id": product.id})
        result = super().write(vals)

        if "payment_method_ids" in vals:
            self.env["pos.session"].search(
                [("config_id", "in", self.ids), ("state", "!=", "closed")]
            )._compute_cash_journal_id()

        for config in self:
            if (
                config.use_presets
                and config.default_preset_id
                and config.default_preset_id.id not in config.available_preset_ids.ids
            ):
                config.available_preset_ids |= config.default_preset_id

        if "use_fast_payment" not in vals:
            self.filtered(
                lambda config: (
                    config.use_fast_payment and not config.fast_payment_method_ids
                )
            ).use_fast_payment = False
        self.sudo()._update_fiscal_position_ids(vals)
        if any(k.startswith(("module_", "group_")) for k in vals):
            dbg.logic.debug(
                "pos.config.write: module_/group_ keys %s -> install check",
                sorted(k for k in vals if k.startswith(("module_", "group_"))),
            )
            self.sudo()._install_missing_modules()
        if {"is_order_printer", "active"} & vals.keys():
            self._update_preparation_printers_menuitem_visibility()
        return result

    @dbg.timed
    def _check_session_forbidden_changes(self, vals):
        forbidden_keys = [
            key for key in self._get_fields_forbidden_change() if key in vals
        ]
        if self.env.context.get("bypass_payment_method_ids_forbidden_change"):
            forbidden_keys = [
                key for key in forbidden_keys if key != "payment_method_ids"
            ]
        if vals.get("active"):
            forbidden_keys = [key for key in forbidden_keys if key != "active"]
        if not forbidden_keys:
            return
        opened_session = self.env["pos.session"].search(
            [("config_id", "in", self.ids), ("state", "!=", "closed")], limit=1
        )
        if opened_session:
            dbg.logic.debug(
                "pos.config.write: open session %s prevents changing %s",
                dbg.rec(opened_session),
                forbidden_keys,
            )
            forbidden_fields = [
                self._fields[key].get_description(self.env)["string"]
                for key in forbidden_keys
            ]
            raise UserError(
                _(
                    "Unable to modify this PoS Configuration because you can't modify %s while a session is open.",
                    ", ".join(forbidden_fields),
                )
            )

    def _update_vals_x2many_from_settings_view(self, vals):
        from_settings_view = self.env.context.get("from_settings_view")
        if not from_settings_view:
            return

        self.check_singleton()

        for x2many_field in list(vals):
            field = self._fields.get(x2many_field)
            if field and field.type in ("many2many", "one2many"):
                commands = vals[x2many_field]
                if any(
                    command[0] not in (Command.LINK, Command.CREATE)
                    for command in commands
                ):
                    continue
                linked_ids = set(self[x2many_field].ids)

                for command in commands:
                    if command[0] == Command.LINK:
                        _id = command[1]
                        linked_ids.discard(_id)

                unlink_commands = [Command.unlink(_id) for _id in sorted(linked_ids)]

                vals[x2many_field] = unlink_commands + vals[x2many_field]

    def _prepare_vals_changed(self, vals):
        from_settings_view = self.env.context.get("from_settings_view")
        if not from_settings_view:
            return vals
        new_vals = {}
        for field, val in vals.items():
            config_field = self._fields.get(field)
            if config_field:
                if config_field.type in ("many2many", "one2many") and any(
                    isinstance(command, (tuple, list))
                    and command[0] in (Command.CREATE, Command.UPDATE, Command.DELETE)
                    for command in val
                ):
                    # UPDATE conversion writes records; defer it until after validation.
                    new_vals[field] = val
                    continue
                cache_value = config_field.convert_to_cache(val, self)
                record_value = config_field.convert_to_record(cache_value, self)
                if record_value != self[field]:
                    new_vals[field] = val
        dbg.logic.debug(
            "[config:%s] settings write: %d of %d keys actually changed: %s",
            self.id,
            len(new_vals),
            len(vals),
            dbg.keys(new_vals),
        )
        return new_vals

    def _get_fields_forbidden_change(self):
        return ["module_pos_restaurant", "payment_method_ids", "active"]

    def unlink(self):
        dbg.lifecycle.debug("pos.config.unlink: %s", dbg.rec(self))
        sequences_to_delete = (
            self.order_seq_id
            | self.order_backend_seq_id
            | self.order_line_seq_id
            | self.device_seq_id
        )
        res = super().unlink()
        sequences_to_delete.sudo().unlink()
        self._update_preparation_printers_menuitem_visibility()
        return res

    def _update_fiscal_position_ids(self, vals):
        if "tax_regime_selection" in vals and not vals["tax_regime_selection"]:
            self.filtered("fiscal_position_ids").fiscal_position_ids = [Command.clear()]
            return
        for config in self:
            if (
                config.tax_regime_selection
                and config.default_fiscal_position_id
                and config.default_fiscal_position_id not in config.fiscal_position_ids
            ):
                config.fiscal_position_ids = [
                    Command.link(config.default_fiscal_position_id.id)
                ]

    def _install_missing_modules(self):
        expected = [
            fname[7:]
            for fname in self._fields
            if fname.startswith("module_")
            if any(pos_config[fname] for pos_config in self)
        ]
        if expected:
            STATES = ("installed", "to install", "to upgrade")
            modules = (
                self.env["ir.module.module"].sudo().search([("name", "in", expected)])
            )
            modules = modules.filtered(lambda module: module.state not in STATES)
            dbg.logic.debug(
                "_install_missing_modules: expected=%s to install=%s",
                expected,
                dbg.names(modules, "name"),
            )
            if modules:
                modules.button_immediate_install()
                return True
        return False

    def _get_or_create_current_session(self):
        if not self.current_session_id:
            dbg.lifecycle.debug(
                "[config:%s] no current session: creating one for uid %s",
                self.id,
                self.env.uid,
            )
            self.env["pos.session"].create(
                {"user_id": self.env.uid, "config_id": self.id}
            )
        return self.current_session_id

    def _prepare_action_open_ui(self):
        pos_url = "/pos/ui/%d?from_backend=True" % self.id
        debug = request and request.session.debug
        if debug:
            pos_url += "&debug=%s" % debug
        return {
            "type": "ir.actions.act_url",
            "url": pos_url,
            "target": "self",
        }

    def _get_urls_to_cache(self, debug):
        url_to_cache = [
            f"/pos/ui/{self.id}?from_backend=True",
            f"/pos/ui/{self.id}",
        ]
        return (
            self.env["ir.qweb"]._get_asset_urls(
                "point_of_sale.assets_prod", debug=debug
            )
            + url_to_cache
        )

    def _check_before_creating_new_session(self):
        self._check_company_has_template()
        self._check_companies()
        self._check_pricelists()
        self._check_company_payment()
        self._check_currencies()
        self._check_profit_loss_cash_journal()
        self._check_payment_method_ids()

    @dbg.timed
    def open_ui(self):
        self.check_singleton()
        dbg.pipeline.debug(
            "[config:%s] open_ui: uid=%s current_session=%s",
            self.id,
            self.env.uid,
            self.current_session_id.id or None,
        )
        if self.env.uid == SUPERUSER_ID and not tools.config["test_enable"]:
            raise UserError(
                _(
                    "You do not have permission to open a POS session. Please try opening a session with a different user"
                )
            )

        if not self.current_session_id:
            with dbg.timer(self.env, "[config:%s] pre-session checks", self.id):
                self._check_before_creating_new_session()
        self._check_fields(self._fields)

        self._check_company_has_fiscal_country()
        self._get_or_create_current_session()
        return self._prepare_action_open_ui()

    def close_ui(self):
        return self.open_ui()

    def action_view_current_session(self):
        self.check_singleton()
        return self._prepare_action_view_session(self.current_session_id.id)

    def _prepare_action_view_session(self, session_id):
        self._check_companies()
        self._check_pricelists()
        return {
            "name": _("Session"),
            "view_mode": "form,list",
            "res_model": "pos.session",
            "res_id": session_id,
            "view_id": False,
            "type": "ir.actions.act_window",
        }

    def action_view_rescue_sessions(self):
        rescue_session_ids = self.session_ids.filtered(
            lambda s: s.state != "closed" and s.rescue
        )

        if len(rescue_session_ids) == 1:
            return {
                "res_model": "pos.session",
                "view_mode": "form",
                "res_id": rescue_session_ids.id,
                "type": "ir.actions.act_window",
            }
        else:
            return {
                "name": _("Rescue Sessions"),
                "res_model": "pos.session",
                "view_mode": "list,form",
                "domain": [("id", "in", rescue_session_ids.ids)],
                "type": "ir.actions.act_window",
            }

    def get_limited_product_count(self):
        return self._get_pos_loading_limit(
            "limited_product_count", DEFAULT_LIMIT_LOAD_PRODUCT
        )

    def _get_limited_partner_count(self):
        return self._get_pos_loading_limit(
            "limited_customer_count", DEFAULT_LIMIT_LOAD_PARTNER
        )

    def _get_pos_loading_limit(self, name, default):
        config_param = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(f"point_of_sale.{name}", default)
        )
        try:
            count = int(config_param)
        except TypeError, ValueError, OverflowError:
            count = -1
        # PostgreSQL's LIMIT accepts a signed bigint, unlike Python's unbounded int.
        if 0 <= count < 2**63:
            return count
        dbg.logic.debug("%s %r unusable: default %s", name, config_param, default)
        return default

    @dbg.timed
    def get_limited_partners_loading(self, offset=0):
        self.check_singleton()
        partner_query = self.env["res.partner"]._search([])
        self.env["res.partner"].flush_model(["active", "name", "company_id"])
        self.env["pos.order"].flush_model(["partner_id", "company_id"])
        return self.env.execute_query(
            SQL(
                """
            WITH pm AS (
                SELECT partner_id, count(partner_id) AS order_count
                  FROM pos_order
                 WHERE company_id = %(company)s
              GROUP BY partner_id
            )
                SELECT partner.id
                  FROM res_partner AS partner
             LEFT JOIN pm ON partner.id = pm.partner_id
                 WHERE (partner.company_id = %(company)s OR partner.company_id IS NULL)
                   AND partner.active
                   AND partner.id IN (%(accessible_partners)s)
              ORDER BY COALESCE(pm.order_count, 0) DESC, partner.name, partner.id
                 LIMIT %(limit)s OFFSET %(offset)s
                """,
                company=self.company_id.id,
                accessible_partners=partner_query.select(),
                limit=self._get_limited_partner_count(),
                offset=offset,
            )
        )

    def action_pos_config_modal_edit(self):
        return {
            "view_mode": "form",
            "res_model": "pos.config",
            "type": "ir.actions.act_window",
            "target": "new",
            "res_id": self.id,
            "context": {"pos_config_open_modal": True},
        }

    def _add_trusted_config_id(self, config_id):
        self.trusted_config_ids += config_id

    def _remove_trusted_config_id(self, config_id):
        self.trusted_config_ids -= config_id

    def _get_payment_method(self, payment_type):
        for pm in self.payment_method_ids:
            if pm.type == payment_type:
                return pm
        return False

    def _get_special_products(self):
        if self:
            return self.tip_product_id
        return (
            self.env.ref("point_of_sale.product_product_tip", raise_if_not_found=False)
            or self.env["product.product"]
        )

    def update_customer_display(self, order, device_uuid):
        self.check_singleton()
        self._notify(f"UPDATE_CUSTOMER_DISPLAY-{device_uuid}", order)

    def _get_display_device_ip(self):
        self.check_singleton()
        return self.proxy_ip

    def _get_customer_display_data(self):
        self.check_singleton()
        return {
            "config_id": self.id,
            "access_token": self.access_token,
            "has_bg_img": bool(self.customer_display_bg_img),
            "company_id": self.company_id.id,
            "proxy_ip": self._get_display_device_ip(),
        }

    @api.model
    def _create_cash_payment_method(self, cash_journal_vals=None):
        if cash_journal_vals is None:
            cash_journal_vals = {}
        journal_vals = {
            "name": _("Cash"),
            "type": "cash",
            "company_id": self.env.company.id,
            **cash_journal_vals,
        }
        if (
            journal_vals["type"] != "cash"
            or journal_vals["company_id"] != self.env.company.id
        ):
            raise UserError(
                _("Cash provisioning requires a cash journal in the current company.")
            )
        company = self.env.company
        for journal_field, company_field in (
            ("profit_account_id", "default_cash_difference_income_account_id"),
            ("loss_account_id", "default_cash_difference_expense_account_id"),
        ):
            account = (
                company[company_field] | company.root_id[company_field]
            ).filtered("active")[:1]
            journal_vals.setdefault(journal_field, account.id)

        if "default_account_id" not in journal_vals:
            default_cash_account = (
                self.env["account.account"]
                .with_context(lang="en_US")
                .search(
                    [
                        ("account_type", "=", "asset_cash"),
                        ("active", "=", True),
                        ("name", "=", "Cash"),
                        ("company_ids", "in", self.env.company.root_id.id),
                    ],
                    limit=1,
                )
            )

            if default_cash_account:
                journal_vals["default_account_id"] = default_cash_account.id
        cash_journal = self.env["account.journal"].create(journal_vals)
        dbg.lifecycle.debug(
            "cash journal %s created (default account %s)",
            dbg.rec(cash_journal),
            dbg.rec(cash_journal.default_account_id),
        )
        return self.env["pos.payment.method"].create(
            {
                "name": _("Cash"),
                "journal_id": cash_journal.id,
                "company_id": self.env.company.id,
            }
        )

    def _create_journal_and_payment_methods(
        self, cash_ref=None, cash_journal_vals=None
    ):
        if cash_ref:
            cash_ref = self._get_suffixed_ref_name(cash_ref)
        journal = self.env["account.journal"]._get_or_create_company_account_journal()
        payment_methods = self.env["pos.payment.method"]

        cash_pm_from_ref = cash_ref and self.env.ref(cash_ref, raise_if_not_found=False)
        if cash_pm_from_ref:
            if cash_pm_from_ref._name != "pos.payment.method":
                raise UserError(_("The cash reference must identify a payment method."))
            try:
                cash_pm_from_ref.check_access("read")
                if cash_pm_from_ref.company_id != self.env.company:
                    raise UserError(
                        _(
                            "The referenced cash payment method must belong to the current company."
                        )
                    )
                if not cash_pm_from_ref.active or not cash_pm_from_ref.is_cash_count:
                    raise UserError(
                        _(
                            "The cash reference must identify an active cash payment method."
                        )
                    )
                cash_pm = cash_pm_from_ref
            except AccessError:
                dbg.logic.debug(
                    "cash method %s not readable: creating a new one", cash_ref
                )
                cash_pm = self._create_cash_payment_method(cash_journal_vals)
        else:
            cash_pm = self._create_cash_payment_method(cash_journal_vals)
        dbg.logic.debug(
            "journal+methods: cash_ref=%s -> cash method %s (from ref=%s)",
            cash_ref,
            dbg.rec(cash_pm),
            cash_pm == cash_pm_from_ref,
        )

        if cash_ref and cash_pm != cash_pm_from_ref:
            self.env["ir.model.data"]._update_xmlids(
                [
                    {
                        "xml_id": cash_ref,
                        "record": cash_pm,
                        "noupdate": True,
                    }
                ]
            )

        payment_methods |= cash_pm

        bank_pm = self.env["pos.payment.method"].search(
            [
                ("journal_id.type", "=", "bank"),
                ("company_id", "=", self.env.company.id),
                ("active", "=", True),
            ]
        )
        if not bank_pm:
            bank_journal = self.env["account.journal"].search(
                [
                    ("type", "=", "bank"),
                    ("active", "=", True),
                    ("company_id", "in", self.env.company.parent_ids.ids),
                ],
                limit=1,
            )
            if not bank_journal:
                raise UserError(
                    _(
                        "Ensure that there is an existing bank journal. Check if chart of accounts is installed in your company."
                    )
                )
            chart_template = self.with_context(
                allowed_company_ids=self.env.company.root_id.ids
            ).env["account.chart.template"]
            outstanding_account = (
                chart_template.ref(
                    "account_journal_payment_debit_account_id", raise_if_not_found=False
                )
                or self.env.company.transfer_account_id
            )
            bank_pm = self.env["pos.payment.method"].create(
                {
                    "name": _("Card"),
                    "journal_id": bank_journal.id,
                    "outstanding_account_id": outstanding_account.id
                    if outstanding_account
                    else False,
                    "company_id": self.env.company.id,
                    "sequence": 1,
                }
            )

        payment_methods |= bank_pm

        pay_later_pm = self.env["pos.payment.method"].search(
            [
                ("journal_id", "=", False),
                ("company_id", "=", self.env.company.id),
                ("active", "=", True),
                ("split_transactions", "=", True),
            ]
        )
        if not pay_later_pm:
            pay_later_pm = self.env["pos.payment.method"].create(
                {
                    "name": _("Customer Account"),
                    "company_id": self.env.company.id,
                    "split_transactions": True,
                    "sequence": 2,
                }
            )

        payment_methods |= pay_later_pm
        dbg.pipeline.debug(
            "journal %s with methods %s (bank=%s pay_later=%s)",
            dbg.rec(journal),
            dbg.rec(payment_methods),
            dbg.rec(bank_pm),
            dbg.rec(pay_later_pm),
        )

        return journal, payment_methods.ids

    @api.model
    def get_pos_kanban_view_state(self):
        has_pos_config = bool(
            self.env["pos.config"].search_count(
                self._check_company_domain(self.env.company),
                limit=1,
            )
        )
        has_chart_template = bool(self.env.company.chart_template)
        main_company = self.env.ref("base.main_company", raise_if_not_found=False)
        return {
            "has_pos_config": has_pos_config,
            "has_chart_template": has_chart_template,
            "is_restaurant_installed": bool(
                self.env["ir.module.module"]
                .sudo()
                .search_count(
                    [("name", "=", "pos_restaurant"), ("state", "=", "installed")],
                    limit=1,
                )
            ),
            "is_main_company": (main_company and self.env.company.id == main_company.id)
            or False,
        }

    @api.model
    def install_pos_restaurant(self):
        pos_restaurant_module = self.env["ir.module.module"].search(
            [("name", "=", "pos_restaurant")]
        )
        pos_restaurant_module.button_immediate_install()
        return {"installed_with_demo": pos_restaurant_module.demo}

    def _get_available_pricelists(self):
        self.check_singleton()
        return (
            self.available_pricelist_ids + self.pricelist_id
            if self.use_pricelist
            else self.pricelist_id
        )

    @api.model
    def _set_default_pos_load_limit(self):
        param_model = self.env["ir.config_parameter"]
        if not param_model.get_param("point_of_sale.limited_product_count"):
            param_model.set_param(
                "point_of_sale.limited_product_count", DEFAULT_LIMIT_LOAD_PRODUCT
            )

        if not param_model.get_param("point_of_sale.limited_customer_count"):
            param_model.set_param(
                "point_of_sale.limited_customer_count", DEFAULT_LIMIT_LOAD_PARTNER
            )

    def _is_quantities_set(self):
        return self.is_closing_entry_by_product

    @api.onchange("epson_printer_ip")
    def _onchange_epson_printer_ip(self):
        for rec in self:
            if rec.epson_printer_ip:
                rec.epson_printer_ip = format_epson_certified_domain(
                    rec.epson_printer_ip
                )
