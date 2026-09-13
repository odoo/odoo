from collections import defaultdict

from odoo import _, api, fields, models, modules
from odoo.exceptions import ValidationError

from ..tools import debug_log as dbg


class ResCompany(models.Model):
    _inherit = "res.company"
    _check_company_auto = True

    internal_transit_location_id = fields.Many2one(
        comodel_name="stock.location",
        ondelete="restrict",
        check_company=True,
        help="Used for resupply routes between warehouses that belong to this company",
    )
    stock_move_email_validation = fields.Boolean(string="Email Confirmation picking")
    stock_mail_confirmation_template_id = fields.Many2one(
        comodel_name="mail.template",
        string="Email Template confirmation picking",
        default=lambda self: self._default_stock_mail_confirmation_template_id(),
        domain="[('model', '=', 'stock.picking')]",
        help="Email sent to the customer once the order is done.",
    )
    annual_inventory_month = fields.Selection(
        selection=[
            ("1", "January"),
            ("2", "February"),
            ("3", "March"),
            ("4", "April"),
            ("5", "May"),
            ("6", "June"),
            ("7", "July"),
            ("8", "August"),
            ("9", "September"),
            ("10", "October"),
            ("11", "November"),
            ("12", "December"),
        ],
        default="12",
        help="Annual inventory month for products not in a location with a cyclic inventory date. Set to no month if no automatic annual inventory.",
    )
    annual_inventory_day = fields.Integer(
        string="Day of the month",
        default=31,
        help="""Day of the month when the annual inventory should occur. If zero or negative, then the first day of the month will be selected instead.
        If greater than the last day of a month, then the last day of the month will be selected instead.""",
    )
    horizon_days = fields.Integer(
        string="Replenishment Horizon",
        default=365,
        required=True,
        help="""Configure your horizon to trigger reordering rules earlier to get
         a head start on replenishment and avoid delays, or trigger it just-in-time
         ('0 days') to avoid overstocking.""",
    )

    stock_text_confirmation = fields.Boolean()
    stock_confirmation_type = fields.Selection(
        selection=[("sms", "SMS")],
        string="Confirmation Channel",
        default="sms",
        help="Channel used to send the delivery text confirmation to the customer.",
    )

    @api.constrains("horizon_days")
    def _check_horizon_days(self):
        for company in self:
            if company.horizon_days < 0:
                raise ValidationError(
                    _("The replenishment horizon cannot be negative.")
                )

    @dbg.timed
    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        dbg.lifecycle.debug(
            "res.company.create: stock setup for %s", dbg.rec(companies)
        )
        inter_company_location = self.env.ref("stock.stock_location_inter_company")
        if not inter_company_location.active:
            inter_company_location.sudo().write({"active": True})
        companies_sudo = companies.sudo()
        with dbg.timer(self.env, "per-company stock data for %s", dbg.rec(companies)):
            companies_sudo._create_per_company_locations()
            companies_sudo._create_per_company_sequences()
            companies_sudo._create_per_company_picking_types()
            companies_sudo._create_per_company_rules()
            companies_sudo._update_per_company_inter_company_locations(
                inter_company_location
            )
        if modules.module.current_test:
            dbg.logic.debug("res.company.create: test mode, creating warehouses")
            companies_sudo._create_warehouse()
        return companies

    @api.model
    def _get_all_companies(self):
        return self.env["res.company"].with_context(active_test=False).search([])

    @api.model
    def _get_companies_without(self, companies_having):
        return self._get_all_companies() - companies_having

    @api.model
    def _get_companies_with_property(self, model_name, field_name):
        field = self.env["ir.model.fields"]._get(model_name, field_name)
        defaults = self.env["ir.default"].sudo()
        global_default = defaults.search_count(
            [("field_id", "=", field.id), ("company_id", "=", False)], limit=1
        )
        if global_default:
            return self._get_all_companies()
        return defaults.search([("field_id", "=", field.id)]).mapped("company_id")

    def _create_transit_location(self):
        locations = self.env["stock.location"].create(
            [
                {
                    "name": _("Inter-warehouse transit"),
                    "usage": "transit",
                    "company_id": company.id,
                    "active": False,
                }
                for company in self
            ],
        )
        for company, location in zip(self, locations, strict=True):
            dbg.lifecycle.debug(
                "[company:%s] transit location %s", company.id, location.id
            )
            company.internal_transit_location_id = location.id
            company.partner_id.with_company(company)._update_stock_property_locations(
                location
            )
        return locations

    def _create_property_location(self, name, usage, property_field):
        locations = self.env["stock.location"].create(
            [
                {
                    "name": name,
                    "usage": usage,
                    "company_id": company.id,
                }
                for company in self
            ],
        )
        for company, location in zip(self, locations, strict=True):
            self.env["ir.default"].set(
                "product.template",
                property_field,
                location.id,
                company_id=company.id,
            )
        return locations

    def _create_inventory_loss_location(self):
        return self._create_property_location(
            _("Inventory adjustment"), "inventory", "property_stock_inventory"
        )

    def _create_production_location(self):
        return self._create_property_location(
            _("Production"), "production", "property_stock_production"
        )

    def _create_scrap_sequence(self):
        return self.env["ir.sequence"].create(
            [
                {
                    "name": f"{company.name} Sequence scrap",
                    "code": "stock.scrap",
                    "company_id": company.id,
                    "prefix": "SP/",
                    "padding": 5,
                    "number_next": 1,
                    "number_increment": 1,
                }
                for company in self
            ],
        )

    def _create_warehouse(self):
        Warehouse = self.env["stock.warehouse"]
        warehouse_by_company = {}
        for warehouse in Warehouse.with_context(active_test=False).search(
            [("company_id", "in", self.ids)], order="id"
        ):
            warehouse_by_company.setdefault(warehouse.company_id.id, warehouse)
        companies_without = self.filtered(
            lambda company: company.id not in warehouse_by_company
        )
        dbg.lifecycle.debug(
            "_create_warehouse: companies without warehouse %s",
            dbg.rec(companies_without),
        )
        vals_list = []
        taken_names = defaultdict(set)
        taken_codes = defaultdict(set)
        for company in companies_without:
            name = Warehouse._get_free_name(company, taken_names[company.id])
            code = Warehouse._get_free_code(company, taken_codes[company.id])
            taken_names[company.id].add(name)
            taken_codes[company.id].add(code)
            vals_list.append(
                {
                    "name": name,
                    "code": code,
                    "company_id": company.id,
                    "partner_id": company.partner_id.id,
                },
            )
        new_warehouses = Warehouse.create(vals_list)
        for company, warehouse in zip(companies_without, new_warehouses, strict=True):
            warehouse_by_company[company.id] = warehouse
        return self.env["stock.warehouse"].union(
            *(warehouse_by_company[company.id] for company in self)
        )

    @api.model
    def create_missing_warehouse(self):
        if self.env["stock.warehouse"].search_count([], limit=1):
            return
        self.env["res.company"].search([], limit=1)._create_warehouse()

    @api.model
    def create_missing_transit_location(self):
        company_without_transit = self._get_all_companies().filtered(
            lambda company: not company.internal_transit_location_id
        )
        company_without_transit._create_transit_location()

    @api.model
    def create_missing_inventory_loss_location(self):
        having = self._get_companies_with_property(
            "product.template", "property_stock_inventory"
        )
        self._get_companies_without(having)._create_inventory_loss_location()

    @api.model
    def create_missing_production_location(self):
        having = self._get_companies_with_property(
            "product.template", "property_stock_production"
        )
        self._get_companies_without(having)._create_production_location()

    @api.model
    def create_missing_scrap_sequence(self):
        having = (
            self.env["ir.sequence"]
            .search([("code", "=", "stock.scrap")])
            .mapped("company_id")
        )
        self._get_companies_without(having)._create_scrap_sequence()

    @api.model
    def create_missing_mail_template(self):
        template_id = self._default_stock_mail_confirmation_template_id()
        if not template_id:
            return
        self._get_all_companies().filtered(
            lambda company: not company.stock_mail_confirmation_template_id
        ).stock_mail_confirmation_template_id = template_id

    def _create_per_company_locations(self):
        self._create_transit_location()
        self._create_inventory_loss_location()
        self._create_production_location()

    def _create_per_company_sequences(self):
        self._create_scrap_sequence()

    def _create_per_company_picking_types(self):
        pass

    def _create_per_company_rules(self):
        pass

    def _update_per_company_inter_company_locations(self, inter_company_location):
        if not self.env.user.has_group("base.group_multi_company"):
            dbg.logic.debug("inter-company locations skipped: no multi-company group")
            return
        all_companies = self._get_all_companies()
        dbg.performance.debug(
            "_update_per_company_inter_company_locations: %d x %d company pairs",
            len(self),
            len(all_companies),
        )
        for company in self:
            other_companies = all_companies - company
            other_companies.partner_id.with_company(
                company
            )._update_stock_property_locations(inter_company_location)
            for other_company in other_companies:
                company.partner_id.with_company(
                    other_company
                )._update_stock_property_locations(inter_company_location)

    def _default_stock_mail_confirmation_template_id(self):
        template = self.env.ref(
            "stock.mail_template_data_delivery_confirmation", raise_if_not_found=False
        )
        return template.id if template else False

    def _is_text_confirmation_enabled(self, confirmation_type):
        self.check_singleton()
        return bool(
            self.stock_text_confirmation
            and self.stock_confirmation_type == confirmation_type
        )
