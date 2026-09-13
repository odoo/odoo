import json
from itertools import groupby

from odoo import api, fields, models
from odoo.api import SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.http import request
from odoo.tools import (
    float_is_zero,
    format_amount,
    format_list,
    is_html_empty,
)
from odoo.tools.mail import html_keep_url
from odoo.tools.misc import str2bool
from odoo.tools.translate import _

from odoo.addons.payment import utils as payment_utils
from odoo.addons.sale import const


class SaleOrder(models.Model):
    _name = "sale.order"
    _inherit = [
        "mixin.order",
        "mixin.order.amount",
        "mixin.order.invoice",
        "mixin.order.merge",
        "mixin.account.document.import",
        "mixin.utm",
    ]
    _description = "Sale Order"
    _check_company_auto = True
    _order = "date_order desc, id desc"

    _price_history_action = "sale.action_sale_history"

    _order_type = "sale"
    _sequence_code = "sale.order"
    _invoice_move_direction = "out"
    _partner_payment_term_field = "property_payment_term_id"
    _lock_setting_field = "order_lock_so"
    _auto_lock_group = "sale.group_auto_done_setting"
    _mark_sent_context_key = "mark_so_as_sent"
    _display_name_context_key = "sale_show_partner_name"
    _portal_url_prefix = "orders"
    _product_ok_field = "sale_ok"

    terms_type = fields.Selection(related="company_id.terms_type")
    country_code = fields.Char(
        related="company_id.account_fiscal_country_id.code",
        string="Country code",
    )
    partner_id = fields.Many2one(string="Customer")
    partner_invoice_id = fields.Many2one(
        comodel_name="res.partner",
        string="Invoice Address",
        compute="_compute_partner_invoice_id",
        precompute=True,
        store=True,
        index="btree_not_null",
        readonly=False,
        required=True,
        check_company=True,
    )
    partner_shipping_id = fields.Many2one(
        comodel_name="res.partner",
        string="Delivery Address",
        compute="_compute_partner_shipping_id",
        precompute=True,
        store=True,
        index="btree_not_null",
        readonly=False,
        required=True,
        check_company=True,
    )
    allow_external_delivery_address = fields.Boolean(
        default=False,
        tracking=True,
        help="Allow selecting a delivery address that does not belong to the "
        "customer's company (e.g. drop-shipping to a third party). When "
        "disabled, the delivery address is limited to the customer's own contacts.",
    )
    partner_invoice_domain = fields.Binary(
        compute="_compute_partner_address_domains",
        help="Dynamic domain limiting invoice address selection.",
    )
    partner_shipping_domain = fields.Binary(
        compute="_compute_partner_address_domains",
        help="Dynamic domain limiting delivery address selection.",
    )
    pricelist_id = fields.Many2one(
        comodel_name="product.pricelist",
        compute="_compute_pricelist_id",
        precompute=True,
        store=True,
        readonly=False,
        domain="[('company_id', 'in', [False, company_id])]",
        check_company=True,
        tracking=1,
        help="If you change the pricelist, only newly added lines will be affected.",
    )
    user_id = fields.Many2one(
        string="Salesperson",
        domain=lambda self: """
            [
                ('all_group_ids', 'in', {}),
                ('share', '=', False),
                ('company_ids', '=', company_id)
            ]
        """.format(
            self.env.ref("sales_team.group_sale_salesman").ids,
        ),
    )
    team_id = fields.Many2one(
        comodel_name="crm.team",
        string="Sales Team",
        compute="_compute_team_id",
        precompute=True,
        change_default=True,
        store=True,
        index=True,
        readonly=False,
        domain="[('company_id', 'in', [False, company_id])]",
        ondelete="set null",
        check_company=True,
        tracking=True,
    )
    journal_id = fields.Many2one(
        domain=[("type", "=", "sale")],
        help="If set, the SO will invoice in this journal; "
        "otherwise the sales journal with the lowest sequence is used.",
    )
    state = fields.Selection(
        selection=const.ORDER_STATE,
        group_expand=True,
    )
    create_date = fields.Datetime(
        string="Creation Date",
        index=True,
        readonly=True,
    )
    date_validity = fields.Date(
        help="Validity of the order, after that you will not able to sign & pay the quotation."
    )
    date_confirmed = fields.Datetime(help="Date when the sales order was confirmed.")
    date_commitment = fields.Datetime(
        string="Delivery Date",
        help="This is the delivery date promised to the customer. "
        "If set, the delivery order will be scheduled based on "
        "this date rather than product lead times.",
    )
    date_planned = fields.Datetime(
        string="Expected Date",
        compute="_compute_date_planned",
        store=False,
        help="Delivery date you can promise to the customer, computed from the minimum lead time of the order lines.",
    )

    require_signature = fields.Boolean(
        string="Online signature",
        compute="_compute_require_signature",
        precompute=True,
        store=True,
        readonly=False,
        help="Request a online signature from the customer to confirm the order.",
    )
    signature = fields.Image(
        attachment=True,
        max_width=1024,
        max_height=1024,
        copy=False,
    )
    signed_by = fields.Char(copy=False)
    signed_on = fields.Datetime(copy=False)

    require_payment = fields.Boolean(
        string="Online payment",
        compute="_compute_require_payment",
        precompute=True,
        store=True,
        readonly=False,
        help="Request a online payment from the customer to confirm the order.",
    )
    prepayment_percent = fields.Float(
        string="Prepayment percentage",
        compute="_compute_prepayment_percent",
        precompute=True,
        store=True,
        readonly=False,
        help="The percentage of the amount needed that must be paid by the customer to confirm the order.",
    )
    preferred_payment_channel_id = fields.Many2one(
        comodel_name="account.payment.channel",
        string="Payment Method",
        compute="_compute_preferred_payment_channel_id",
        precompute=True,
        store=True,
        readonly=False,
        domain="[('payment_type', '=', 'inbound'), ('company_id', '=', company_id)]",
        check_company=True,
    )

    line_ids = fields.One2many(
        comodel_name="sale.order.line",
        bypass_search_access=True,
    )
    amount_untaxed = fields.Monetary(tracking=5)
    amount_tax = fields.Monetary(tracking=4)
    amount_total = fields.Monetary(tracking=4)
    has_upsell_opportunity = fields.Boolean(
        string="Has Upselling Opportunity",
        compute="_compute_has_upsell_opportunity",
        store=True,
        help="Set when a line invoiced on ordered quantities has delivered more than "
        "was ordered: the excess is not billable until the order is increased.",
    )

    transaction_ids = fields.Many2many(
        comodel_name="payment.transaction",
        relation="sale_order_transaction_rel",
        column1="sale_order_id",
        column2="transaction_id",
        string="Transactions",
        copy=False,
        readonly=True,
        groups="account.group_account_invoice",
    )
    authorized_transaction_ids = fields.Many2many(
        comodel_name="payment.transaction",
        string="Authorized Transactions",
        compute="_compute_authorized_transactions",
        compute_sudo=True,
        copy=False,
        groups="account.group_account_invoice",
    )
    has_authorized_transaction_ids = fields.Boolean(
        string="Has Authorized Transactions",
        compute="_compute_authorized_transactions",
        compute_sudo=True,
    )
    amount_paid = fields.Float(
        string="Payment Transactions Amount",
        compute="_compute_amount_paid",
        compute_sudo=True,
        help="Sum of transactions made in through the online payment form that are in the state"
        " 'done' or 'authorized' and linked to this order.",
    )

    campaign_id = fields.Many2one(ondelete="set null")
    medium_id = fields.Many2one(ondelete="set null")
    source_id = fields.Many2one(ondelete="set null")

    origin = fields.Char(
        help="Reference of the document that generated this sales order request"
    )
    client_order_ref = fields.Char(
        string="Customer Reference",
        copy=False,
    )
    partner_invoice_count = fields.Integer(related="partner_id.customer_invoice_count")
    reference = fields.Char(
        string="Payment Ref.",
        copy=False,
        help="The payment communication of this sale order.",
    )
    notes = fields.Html(
        compute="_compute_notes",
        precompute=True,
        store=True,
        readonly=False,
    )
    sent = fields.Boolean(help="The quotation has been sent to the customer.")
    printed_before = fields.Boolean(help="The quotation has already been printed.")
    pending_email_template_id = fields.Many2one(
        comodel_name="mail.template",
        readonly=True,
        ondelete="set null",
    )
    tag_ids = fields.Many2many(
        comodel_name="crm.tag",
        relation="sale_order_tag_rel",
        column1="order_id",
        column2="tag_id",
        string="Tags",
    )
    duplicated_order_ids = fields.Many2many(comodel_name="sale.order")
    sale_warning_text = fields.Text(
        string="Sale Warning",
        compute="_compute_sale_warning_text",
        depends_context=("uid",),
        help="Internal warning for the partner or the products as set by the user.",
    )
    acknowledged = fields.Boolean(
        help="It indicates that the customer has acknowledged the receipt of the sales order."
    )
    has_active_pricelist = fields.Boolean(compute="_compute_has_active_pricelist")
    show_update_fpos = fields.Boolean(
        string="Has Fiscal Position Changed",
        store=False,
        help="True if the fiscal position was changed",
    )
    show_update_pricelist = fields.Boolean(
        string="Has Pricelist Changed",
        store=False,
        help="True if the pricelist was changed",
    )

    _date_order_id_idx = models.Index("(date_order desc, id desc)")

    _date_order_conditional_required = models.Constraint(
        """CHECK(
            (state = 'done' AND date_order IS NOT NULL)
            OR state != 'done'
        )""",
        "A confirmed sales order requires a confirmation date.",
    )

    @api.constrains("prepayment_percent")
    def _check_prepayment_percent(self):
        for order in self:
            if order.require_payment and not (0 < order.prepayment_percent <= 1.0):
                raise ValidationError(
                    _(
                        "Prepayment percentage must be greater than 0% and at most 100%."
                    ),
                )

    def _compute_field_value(self, field, validate=True):
        if field.name != "has_upsell_opportunity" or self.env.context.get(
            "mail_activity_automation_skip",
        ):
            return super()._compute_field_value(field, validate=validate)

        filtered_self = self.filtered(
            lambda so: (
                so.ids
                and (so.user_id or so.partner_id.user_id)
                and not so._origin.has_upsell_opportunity
            ),
        )
        super()._compute_field_value(field, validate=validate)

        upselling_orders = filtered_self.filtered(
            lambda so: so.has_upsell_opportunity,
        )
        upselling_orders._create_upsell_activity()
        return None

    @api.depends("company_id")
    def _compute_has_active_pricelist(self):
        company_ids = set(self.mapped("company_id.id"))

        Pricelist = self.env["product.pricelist"]
        companies_with_pricelist = set()

        has_global_pricelist = bool(
            Pricelist.search(
                [("company_id", "=", False), ("active", "=", True)], limit=1
            )
        )

        if company_ids:
            pricelist_data = Pricelist._read_group(
                domain=[("company_id", "in", list(company_ids)), ("active", "=", True)],
                groupby=["company_id"],
            )
            companies_with_pricelist = {
                data[0].id for data in pricelist_data if data[0]
            }

        for order in self:
            order.has_active_pricelist = (
                has_global_pricelist or order.company_id.id in companies_with_pricelist
            )

    @api.depends("company_id")
    def _compute_require_payment(self):
        for order in self:
            order.require_payment = order.company_id.portal_confirmation_pay

    @api.depends("company_id", "require_payment")
    def _compute_prepayment_percent(self):
        for order in self:
            order.prepayment_percent = order.company_id.prepayment_percent

    @api.depends_context("sale_show_partner_name")
    @api.depends("partner_id")
    def _compute_display_name(self):
        return super()._compute_display_name()

    @api.depends("company_id")
    def _compute_require_signature(self):
        for order in self:
            order.require_signature = order.company_id.portal_confirmation_sign

    @api.depends("partner_id")
    def _compute_notes(self):
        use_invoice_terms = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("account.use_invoice_terms")
        )
        if not use_invoice_terms:
            return
        for order in self:
            company = order.company_id
            order_company = order.with_company(company)
            if order_company.terms_type == "html" and company.invoice_terms_html:
                baseurl = html_keep_url(order_company._get_note_url() + "/terms")
                order.notes = _("Terms & Conditions: %s", baseurl)
            elif not is_html_empty(company.invoice_terms):
                order_ctx = order_company
                if order.partner_id.lang:
                    order_ctx = order_company.with_context(lang=order.partner_id.lang)
                order.notes = order_ctx.env.company.invoice_terms

    @api.depends("partner_id")
    def _compute_partner_invoice_id(self):
        for order in self:
            order.partner_invoice_id = (
                order.partner_id.address_get(["invoice"])["invoice"]
                if order.partner_id
                else False
            )

    @api.depends("partner_id")
    def _compute_partner_shipping_id(self):
        for order in self:
            order.partner_shipping_id = (
                order.partner_id.address_get(["delivery"])["delivery"]
                if order.partner_id
                else False
            )

    @api.depends(
        "commercial_partner_id", "company_id", "allow_external_delivery_address"
    )
    def _compute_partner_address_domains(self):
        for order in self:
            company_ids = [False, order.company_id.id] if order.company_id else [False]
            company_term = ("company_id", "in", company_ids)
            if order.commercial_partner_id:
                in_entity = [
                    ("id", "child_of", order.commercial_partner_id.id),
                    company_term,
                ]
            else:
                in_entity = [company_term]
            order.partner_invoice_domain = in_entity
            order.partner_shipping_domain = (
                [company_term] if order.allow_external_delivery_address else in_entity
            )

    @api.depends("partner_id")
    def _compute_payment_term_id(self):
        for order in self:
            order = order.with_company(order.company_id)
            order.payment_term_id = order.partner_id.property_payment_term_id

    @api.depends("user_id")
    def _compute_team_id(self):
        cached_teams = {}
        for order in self:
            default_team_id = order._default_team_id()
            user_id = order.user_id.id
            company_id = order.company_id.id
            key = (default_team_id, user_id, company_id)
            if key not in cached_teams:
                cached_teams[key] = (
                    self.env["crm.team"]
                    .with_context(
                        default_team_id=default_team_id,
                        allowed_company_ids=[company_id],
                    )
                    ._get_default_team_id(
                        user_id=user_id,
                        domain=self.env["crm.team"]._check_company_domain(company_id),
                    )
                )
            order.team_id = cached_teams[key]

    @api.depends("partner_id", "company_id")
    def _compute_preferred_payment_channel_id(self):
        for order in self:
            order = order.with_company(order.company_id)
            order.preferred_payment_channel_id = (
                order.partner_id.property_inbound_payment_channel_id
            )

    @api.depends("company_id", "partner_id")
    def _compute_pricelist_id(self):
        for order in self:
            if order.state != "draft":
                continue
            if not order.partner_id:
                order.pricelist_id = False
                continue
            order = order.with_company(order.company_id)
            order.pricelist_id = order.partner_id.property_product_pricelist

    @api.depends("partner_id", "client_order_ref", "origin")
    def _compute_duplicated_order_ids(self):
        return super()._compute_duplicated_order_ids()

    @api.depends("company_id", "pricelist_id")
    def _compute_currency_id(self):
        for order in self:
            order.currency_id = (
                order.pricelist_id.currency_id or order.company_id.currency_id
            )

    @api.depends("company_id", "partner_id", "partner_shipping_id")
    def _compute_fiscal_position_id(self):
        cache = {}
        for order in self:
            if not order.partner_id:
                order.fiscal_position_id = False
                continue
            fpos_id_before = order.fiscal_position_id.id
            key = (
                order.company_id.id,
                order.partner_id.id,
                order.partner_shipping_id.id,
            )
            if key not in cache:
                cache[key] = (
                    self.env["account.fiscal.position"]
                    .with_company(order.company_id)
                    ._get_fiscal_position(order.partner_id, order.partner_shipping_id)
                    .id
                )
            if fpos_id_before != cache[key] and order.line_ids:
                order.show_update_fpos = True
            order.fiscal_position_id = cache[key]

    @api.depends(
        "state",
        "date_order",
        "line_ids.customer_lead",
        "line_ids.display_type",
        "line_ids.product_id.type",
    )
    def _compute_date_planned(self):
        for order in self:
            if order.state == "cancel":
                order.date_planned = False
                continue
            scheduled_lines = order.line_ids.filtered(
                lambda line: (
                    line.product_id.type == "consu"
                    and not line.display_type
                    and not line._is_delivery()
                ),
            )
            if scheduled_lines:
                order.date_planned = order._get_date_planned(
                    [line._get_date_planned() for line in scheduled_lines],
                )
            else:
                order.date_planned = False

    @api.depends(
        "partner_id.name",
        "partner_id.sale_warn_msg",
        "partner_id.parent_id.name",
        "partner_id.parent_id.sale_warn_msg",
        "line_ids.sale_line_warn_msg",
        "line_ids.product_id.name",
    )
    def _compute_sale_warning_text(self):
        self._compute_warning_text("sale_warning_text")

    @api.depends(
        "line_ids.product_id",
        "line_ids.product_id.invoice_policy",
        "line_ids.product_qty",
        "line_ids.qty_transferred",
        "line_ids.display_type",
    )
    def _compute_has_upsell_opportunity(self):
        for order in self:
            order.has_upsell_opportunity = any(
                line._is_upsell_opportunity()
                for line in order.line_ids.filtered(lambda l: not l.display_type)
            )

    @api.depends("transaction_ids", "transaction_ids.state")
    def _compute_authorized_transactions(self):
        for trans in self:
            trans.authorized_transaction_ids = trans.transaction_ids.filtered(
                lambda t: t.state == "authorized",
            )
            trans.has_authorized_transaction_ids = bool(
                trans.authorized_transaction_ids,
            )

    @api.depends("transaction_ids", "transaction_ids.state", "transaction_ids.amount")
    def _compute_amount_paid(self):
        for order in self:
            order.amount_paid = sum(
                tx.amount
                for tx in order.transaction_ids
                if tx.state in ("authorized", "done")
            )

    @api.onchange("company_id")
    def _onchange_company_id(self):
        for order in self:
            if not order.company_id:
                raise ValidationError(
                    _(
                        "The company is required, please select one before making any other changes to the sale order.",
                    ),
                )

    @api.onchange("company_id")
    def _onchange_company_id_warning(self):
        self.show_update_pricelist = True

        if not self._origin.id or self._origin.company_id == self.company_id:
            return None

        if self.line_ids and self.state == "draft":
            return {
                "warning": {
                    "title": _("Warning for the change of your quotation's company"),
                    "message": _(
                        "Changing the company of an existing quotation might need some "
                        "manual adjustments in the details of the lines. You might "
                        "consider updating the prices.",
                    ),
                },
            }
        return None

    @api.onchange("date_commitment", "date_planned")
    def _onchange_date_commitment(self):
        if (
            self.date_commitment
            and self.date_planned
            and self.date_commitment < self.date_planned
        ):
            return {
                "warning": {
                    "title": _("Requested date is too soon."),
                    "message": _(
                        "The delivery date is sooner than the expected date."
                        " You may be unable to honor the delivery date.",
                    ),
                },
            }
        return None

    @api.onchange("prepayment_percent")
    def _onchange_prepayment_percent(self):
        if not self.prepayment_percent:
            self.require_payment = False

    @api.onchange("line_ids")
    def _onchange_line_ids(self):
        for line in self.line_ids:
            if line.display_type == "line_subsection" and not line.parent_id:
                line.display_type = "line_section"
            combo_item_lines = line._get_lines_linked().filtered("combo_item_id")
            if line.product_template_id.type != "combo":
                if combo_item_lines:
                    self.line_ids = [
                        Command.delete(linked_line.id)
                        for linked_line in combo_item_lines
                    ]
            elif line.selected_combo_items:
                selected_combo_items = json.loads(line.selected_combo_items)
                if selected_combo_items and len(selected_combo_items) != len(
                    line.product_template_id.sudo().combo_ids,
                ):
                    raise ValidationError(
                        _(
                            "The number of selected combo items must match the number of available combo choices.",
                        ),
                    )

                delete_commands = [
                    Command.delete(linked_line.id) for linked_line in combo_item_lines
                ]
                create_commands = [
                    Command.create(
                        {
                            "product_id": combo_item["product_id"],
                            "product_qty": line.product_qty,
                            "combo_item_id": combo_item["combo_item_id"],
                            "product_no_variant_attribute_value_ids": [
                                Command.set(
                                    combo_item["no_variant_attribute_value_ids"],
                                ),
                            ],
                            "product_custom_attribute_value_ids": [Command.clear()]
                            + [
                                Command.create(attribute_value)
                                for attribute_value in combo_item[
                                    "product_custom_attribute_values"
                                ]
                            ],
                            "sequence": line.sequence + item_index + 1,
                            "linked_line_id": line.id if line._origin else False,
                            "linked_virtual_id": (
                                line.virtual_id if not line._origin else False
                            ),
                        },
                    )
                    for item_index, combo_item in enumerate(selected_combo_items)
                ]
                update_commands = [
                    Command.update(
                        order_line.id,
                        {"sequence": order_line.sequence + len(selected_combo_items)},
                    )
                    for order_line in self.line_ids
                    if order_line.sequence > line.sequence
                ]

                line.selected_combo_items = False
                self.line_ids = delete_commands + create_commands + update_commands
            elif (
                combo_item_lines
                and combo_item_lines.combo_item_id.combo_id
                == line.product_template_id.combo_ids
            ):
                combo_item_lines.update(
                    {
                        "product_qty": line.product_qty,
                        "discount": line.discount,
                    },
                )

    @api.onchange("fiscal_position_id")
    def _onchange_fpos_id_show_update_fpos(self):
        if self.line_ids and (
            not self.fiscal_position_id
            or (
                self.fiscal_position_id
                and self._origin.fiscal_position_id != self.fiscal_position_id
            )
        ):
            self.show_update_fpos = True

    @api.onchange("pricelist_id")
    def _onchange_pricelist_id_show_update_prices(self):
        self.show_update_pricelist = bool(
            self.line_ids and self._origin.pricelist_id != self.pricelist_id
        )

    def _default_team_id(self):
        return self.env.context.get("default_team_id", False) or self.team_id.id

    def action_invoice_matching(self):
        self.check_singleton()
        product_ids = self.line_ids.product_id.ids
        return {
            "name": _("Invoice Matching"),
            "type": "ir.actions.act_window",
            "res_model": "sale.invoice.line.match",
            "views": [
                (self.env.ref("sale.sale_invoice_line_match_list").id, "list"),
            ],
            "domain": [
                ("company_id", "in", self.env.company.ids),
                (
                    "partner_id",
                    "in",
                    (self.partner_id | self.partner_id.commercial_partner_id).ids,
                ),
                "|",
                ("order_id", "=", self.id),
                "&",
                ("order_id", "=", False),
                ("product_id", "in", product_ids),
            ],
        }

    def action_confirm(self):
        res = super().action_confirm()

        if self.env.context.get("send_email"):
            self._send_mail_order_confirmation()

        return res

    def action_draft(self):
        orders = self.filtered(lambda s: s.state in ["cancel", "draft"])
        return orders.write(
            {
                "state": "draft",
                "signature": False,
                "signed_by": False,
                "signed_on": False,
            },
        )

    def _confirm_order(self):
        self.with_context(send_email=True).action_confirm()

    @api.readonly
    def action_preview_sale_order(self):
        self.check_singleton()
        return {
            "type": "ir.actions.act_url",
            "target": "self",
            "url": self.get_portal_url(),
        }

    def action_quotation_sent(self):
        if any(order.state != "draft" for order in self):
            raise UserError(_("Only draft orders can be marked as sent directly."))

        self.write({"sent": True})

    def action_send_quotation(self):
        action = self._action_send_by_email()
        if (
            self.env.context.get("check_document_layout")
            and not self.env.context.get("discard_logo_check")
            and self.env.is_admin()
            and not self.env.company.external_report_layout_id
        ):
            layout_action = self.env[
                "ir.actions.report"
            ]._prepare_layout_configurator_action(
                action,
            )
            action.pop("close_on_report_download", None)
            layout_action["context"]["dialog_size"] = "extra-large"
            return layout_action
        return action

    def action_update_prices(self):
        self.check_singleton()
        self._recompute_prices()
        if self.pricelist_id:
            message = _(
                "Product prices have been recomputed according to pricelist %s.",
                self.pricelist_id._get_html_link(),
            )
        else:
            message = _("Product prices have been recomputed.")
        self.message_post(body=message)

    def action_update_taxes(self):
        self.check_singleton()
        self._recompute_taxes()
        if self.partner_id:
            self.message_post(
                body=_(
                    "Product taxes have been recomputed according to fiscal position %s.",
                    (
                        self.fiscal_position_id._get_html_link()
                        if self.fiscal_position_id
                        else ""
                    ),
                ),
            )

    @api.readonly
    def action_view_discount_wizard(self):
        self.check_singleton()
        return {
            "name": _("Discount"),
            "type": "ir.actions.act_window",
            "res_model": "sale.order.discount",
            "view_mode": "form",
            "target": "new",
        }

    def _merge_check_selection(self, quotations):
        if len(quotations) < 2:
            raise UserError(
                _("Please select at least two quotations to merge."),
            )

    def _prepare_grouped_data(self, quotation):
        return (
            quotation.partner_id.id,
            quotation.currency_id.id,
            quotation.partner_shipping_id.id,
        )

    def _get_merge_group_description(self):
        return _("- Customer\n- Currency\n- Delivery address")

    def _merge_update_metadata_refs(self, target, sources):
        all_refs = [target.client_order_ref] + list(sources.mapped("client_order_ref"))
        target.client_order_ref = ", ".join(filter(None, all_refs))

    def _get_merge_result_name(self):
        return _("Merged Quotations")

    def _create_upsell_activity(self):
        self.activity_unlink(["mail.mail_activity_data_todo"])
        for order in self:
            order_ref = order._get_html_link()
            customer_ref = order.partner_id._get_html_link()
            order.activity_schedule(
                "mail.mail_activity_data_todo",
                user_id=order.user_id.id or order.partner_id.user_id.id,
                note=_(
                    "Upsell %(order)s for customer %(customer)s",
                    order=order_ref,
                    customer=customer_ref,
                ),
            )

    def _discard_tracking(self):
        self.check_singleton()
        return (
            self.state == "draft"
            and request
            and request.env.context.get("catalog_skip_tracking")
        )

    def _get_mark_as_sent_context(self):
        return {**super()._get_mark_as_sent_context(), "tracking_disable": True}

    def _get_mail_subtitles(self, render_context):
        lang_code = render_context.get("lang")
        record = render_context["record"]
        subtitles = [
            (
                f"{record.name} - {record.partner_id.name}"
                if record.partner_id.name
                else record.name
            ),
        ]
        if self.amount_total:
            subtitles.append(
                format_amount(
                    self.env,
                    self.amount_total,
                    self.currency_id,
                    lang_code=lang_code,
                ),
            )

        return subtitles

    @api.model
    def get_empty_list_help(self, help_message):
        self = self.with_context(
            empty_list_help_document_name=_("sale order"),
        )
        return super().get_empty_list_help(help_message)

    def _get_validity_days(self):
        self.check_singleton()
        return self.company_id.quotation_validity_days

    def _get_confirmed_type_name(self):
        return _("Sale Order")

    def _get_display_name_suffix(self):
        if not self.env.context.get("sale_show_partner_name"):
            return ""
        return f" - {self.partner_id.name}" if self.partner_id.name else ""

    def _get_default_user_from_partner(self):
        self.check_singleton()
        return (
            self.partner_id.user_id
            or self.partner_id.commercial_partner_id.user_id
            or (
                self.env.user.has_group("sales_team.group_sale_salesman")
                and self.env.user
            )
            or self.env["res.users"]
        )

    def _get_all_documents_group(self):
        return "sales_team.group_sale_salesman_all_leads"

    def _get_warning_group(self):
        return "sale.group_warning_sale"

    def _get_partner_warn_field(self):
        return "sale_warn_msg"

    def _get_line_warn_field(self):
        return "sale_line_warn_msg"

    def _get_additional_base_lines(self):
        return self._add_base_lines_for_early_payment_discount()

    def _get_outstanding_invoice_state(self, states):
        self.check_singleton()
        if "no" in states:
            invoiceable_lines = self.line_ids.filtered_domain(
                self._get_domain_rollup_lines() + [("invoice_state", "=", "to do")],
            )
            auxiliary_lines = invoiceable_lines.filtered(
                lambda sol: not sol._can_be_invoiced_alone(),
            )
            if invoiceable_lines and invoiceable_lines == auxiliary_lines:
                return "no"
        return "to do"

    def _get_confirmation_context(self):
        context = self.env.context.copy()
        context.pop("default_name", None)
        context.pop("default_user_id", None)
        return context

    def _update_notify_recipient_groups(self, groups):
        if self.env.context.get("proforma"):
            for group in [
                g
                for g in groups
                if g[0] in ("portal_customer", "portal", "follower", "customer")
            ]:
                group[2]["has_button_access"] = False
            return

        try:
            customer_portal_group = next(
                group for group in groups if group[0] == "portal_customer"
            )
        except StopIteration:
            pass
        else:
            access_opt = customer_portal_group[2].setdefault("button_access", {})
            is_tx_pending = self.get_portal_last_transaction().state == "pending"
            if self._has_to_be_signed():
                if self._has_to_be_paid():
                    access_opt["title"] = (
                        _("View Quotation")
                        if is_tx_pending
                        else _("Sign & Pay Quotation")
                    )
                else:
                    access_opt["title"] = _("Accept & Sign Quotation")
            elif self._has_to_be_paid() and not is_tx_pending:
                access_opt["title"] = _("Accept & Pay Quotation")
            elif self.state == "draft":
                access_opt["title"] = _("View Quotation")

    def _get_phone_number_fields(self):
        return []

    def _track_finalize(self):
        if (
            len(self) == 1
            and self.env.cache.contains(self, self._fields["state"])
            and self._discard_tracking()
        ):
            tracking = self.env.cr.precommit.data.get(f"mail.tracking.{self._name}")
            if tracking is not None:
                tracking.pop(self.id, None)
            writer_uids = self.env.cr.precommit.data.get(
                f"mail.tracking.uid.{self._name}",
            )
            if writer_uids is not None:
                writer_uids.pop(self.id, None)
            self.env.flush_all()
            return None
        return super()._track_finalize()

    def _get_state_track_subtype_xmlid(self, init_values):
        if "state" in init_values and self.state == "done":
            return "sale.mt_order_confirmed"
        elif "sent" in init_values and self.sent:
            return "sale.mt_order_sent"
        return None

    def _get_model_description(self, model_name):
        if not self:
            return super()._get_model_description(model_name)
        return self.type_name

    def _get_invoice_action_context(self):
        context = super()._get_invoice_action_context()
        context["default_partner_shipping_id"] = self.partner_shipping_id.id
        return context

    def _get_invoicing_order(self):
        order = self
        if order.partner_invoice_id.lang:
            order = order.with_context(lang=order.partner_invoice_id.lang)
        return super(SaleOrder, order)._get_invoicing_order()

    def _get_invoice_line_sequence_start(self):
        return 0

    def _get_invoiceable_lines(self, final=False):
        return self._get_order_lines_invoiceable(final)

    def _prepare_invoice_line_commands(self, invoiceable_lines, sequence=10):
        if all(line.display_type for line in invoiceable_lines):
            return [], sequence

        commands = []
        down_payment_section_added = False
        for line in invoiceable_lines:
            if not down_payment_section_added and line.is_downpayment:
                commands.append(
                    Command.create(
                        self._prepare_down_payment_section_line(sequence=sequence),
                    ),
                )
                down_payment_section_added = True
                sequence += 1

            optional_values = {"sequence": sequence}

            if line.is_downpayment:
                optional_values["quantity"] = -1.0
                optional_values["extra_tax_data"] = self.env[
                    "account.tax"
                ]._reverse_quantity_base_line_extra_tax_data(line.extra_tax_data)

            commands.extend(
                Command.create(vals)
                for vals in line._prepare_aml_vals_list(**optional_values)
            )
            sequence += 1
        return commands, sequence

    def _group_invoice_vals(self, invoice_vals_list):
        new_invoice_vals_list = []
        invoice_grouping_keys = self._get_invoice_grouping_keys()
        invoice_vals_list = sorted(
            invoice_vals_list,
            key=lambda x: [
                x.get(grouping_key) for grouping_key in invoice_grouping_keys
            ],
        )
        for _grouping_keys, invoices in groupby(
            invoice_vals_list,
            key=lambda x: [
                x.get(grouping_key) for grouping_key in invoice_grouping_keys
            ],
        ):
            origins = set()
            payment_refs = set()
            refs = set()
            ref_invoice_vals = None
            for invoice_vals in invoices:
                if not ref_invoice_vals:
                    ref_invoice_vals = invoice_vals
                else:
                    ref_invoice_vals["invoice_line_ids"] += invoice_vals[
                        "invoice_line_ids"
                    ]
                origins.add(invoice_vals["invoice_origin"])
                payment_refs.add(invoice_vals["payment_reference"])
                refs.add(invoice_vals["ref"])
            ref_invoice_vals.update(
                {
                    "ref": ", ".join(refs)[:2000],
                    "invoice_origin": ", ".join(origins),
                    "payment_reference": (len(payment_refs) == 1 and payment_refs.pop())
                    or False,
                },
            )
            new_invoice_vals_list.append(ref_invoice_vals)
        return new_invoice_vals_list

    def _post_group_invoice_vals(self, invoice_vals_list):
        invoice_vals_list = super()._post_group_invoice_vals(invoice_vals_list)
        if len(invoice_vals_list) < len(self):
            SaleOrderLine = self.env["sale.order.line"]
            for invoice in invoice_vals_list:
                for sequence, line in enumerate(invoice["invoice_line_ids"], start=1):
                    line[2]["sequence"] = SaleOrderLine._get_invoice_line_sequence(
                        new=sequence,
                        old=line[2]["sequence"],
                    )
        return invoice_vals_list

    def _switch_negative_moves(self, moves, final):
        if final and (
            moves_to_switch := moves.sudo().filtered(lambda m: m.amount_total < 0)
        ):
            with self.env.protecting([moves._fields["team_id"]], moves_to_switch):
                moves_to_switch.action_switch_move_type()
                self.invoice_ids._set_reversed_entry(moves_to_switch)

    def _post_create_invoices(self, moves):
        for move in moves:
            move.message_post_with_source(
                "mail.message_origin_link",
                render_values={
                    "self": move,
                    "origin": move.line_ids.sale_line_ids.order_id,
                },
                subtype_xmlid="mail.mt_note",
            )
        return super()._post_create_invoices(moves)

    def _get_invoice_grouping_keys(self):
        return [
            "company_id",
            "partner_id",
            "partner_shipping_id",
            "currency_id",
            "fiscal_position_id",
        ]

    def _get_order_lines_invoiceable(self, final=False):
        down_payment_line_ids = []
        invoiceable_line_ids = []
        section_line_ids = []
        subsection_line_ids = []
        precision = self.env["decimal.precision"].get_precision("Product Unit")

        for line in self.line_ids:
            if line.display_type == "line_section":
                section_line_ids = [line.id]
                subsection_line_ids = []
                continue
            if line.display_type == "line_subsection":
                subsection_line_ids = [line.id]
                continue
            if line.display_type != "line_note" and float_is_zero(
                line.qty_to_invoice,
                precision_digits=precision,
            ):
                continue
            if (
                line.qty_to_invoice > 0
                or (line.qty_to_invoice < 0 and final)
                or line.display_type == "line_note"
            ):
                if line.is_downpayment:
                    down_payment_line_ids.append(line.id)
                    continue
                if subsection_line_ids:
                    if line.display_type:
                        subsection_line_ids.append(line.id)
                        continue
                    invoiceable_line_ids.extend(section_line_ids + subsection_line_ids)
                    subsection_line_ids = []
                    section_line_ids = []
                elif section_line_ids:
                    if line.display_type:
                        section_line_ids.append(line.id)
                        continue
                    invoiceable_line_ids.extend(section_line_ids)
                    section_line_ids = []
                    subsection_line_ids = []
                invoiceable_line_ids.append(line.id)

        return self.env["sale.order.line"].browse(
            invoiceable_line_ids + down_payment_line_ids,
        )

    def _get_order_lines_price_updatable(self):
        return self.line_ids.filtered(lambda line: not line.display_type)

    def _get_nothing_to_invoice_error_message(self):
        return _(
            "Cannot create an invoice. No items are available to invoice.\n\n"
            "To resolve this issue, please ensure that:\n"
            "   \u2022 The products have been delivered before attempting to invoice them.\n"
            "   \u2022 The invoicing policy of the product is configured correctly.\n\n"
            "If you want to invoice based on ordered quantities instead:\n"
            "   \u2022 For consumable or storable products, open the product, go to the 'General Information' tab and change the 'Invoicing Policy' from 'Delivered Quantities' to 'Ordered Quantities'.\n"
            "   \u2022 For services (and other products), change the 'Invoicing Policy' to 'Prepaid/Fixed Price'.\n",
        )

    def _get_invoice_partner(self):
        self.check_singleton()
        return self.partner_invoice_id

    def _prepare_invoice_vals(self):
        values = super()._prepare_invoice_vals()
        txs_to_be_linked = self.sudo().transaction_ids.filtered(
            lambda tx: (
                tx.state in ("pending", "authorized")
                or (tx.state == "done" and not tx.payment_id.is_invoice_reconciled)
            ),
        )
        values.update(
            {
                "team_id": self.team_id.id,
                "partner_shipping_id": self.partner_shipping_id.id,
                "allow_external_delivery_address": self.allow_external_delivery_address,
                "campaign_id": self.campaign_id.id,
                "medium_id": self.medium_id.id,
                "source_id": self.source_id.id,
                "user_id": self.user_id.id,
                "ref": self.client_order_ref or self.name,
                "preferred_payment_channel_id": self.preferred_payment_channel_id.id,
                "payment_reference": self.reference,
                "transaction_ids": [Command.set(txs_to_be_linked.ids)],
            },
        )
        return values

    def _force_lines_to_invoice_policy_order(self):
        for line in self.line_ids:
            if line.state == "done":
                line.qty_to_invoice = line.product_qty - line.qty_invoiced

    def _get_default_payment_link_values(self):
        self.check_singleton()

        prepayment_amount = self._get_prepayment_required_amount()
        remaining_balance = self.amount_total - self.amount_paid
        if self.state == "draft" and self.require_payment:
            suggested_amount = prepayment_amount
        else:
            suggested_amount = remaining_balance
        return {
            "currency_id": self.currency_id.id,
            "partner_id": self.partner_invoice_id.id,
            "amount": suggested_amount,
            "amount_max": remaining_balance,
            "amount_paid": self.amount_paid,
            "prepayment_amount": prepayment_amount,
        }

    def _get_order_lines_to_report(self):
        down_payment_lines = self.line_ids.filtered(
            lambda line: (
                line.is_downpayment
                and not line.display_type
                and not line._get_downpayment_state()
            ),
        )

        def show_line(line):
            if line.is_downpayment:
                return (
                    line.display_type and down_payment_lines
                ) or line in down_payment_lines
            return line.display_type == "line_section" or not (
                line.parent_id.collapse_composition
                or line.parent_id.parent_id.collapse_composition
            )

        return self.line_ids.filtered(show_line)

    def get_portal_last_transaction(self):
        self.check_singleton()
        return self.sudo().transaction_ids._get_last()

    def payment_action_capture(self):
        self.check_singleton()
        payment_utils.check_rights_on_recordset(self)

        return self.sudo().transaction_ids.action_capture()

    def payment_action_void(self):
        payment_utils.check_rights_on_recordset(self)

        self.sudo().authorized_transaction_ids.action_void()

    def _has_to_be_paid(self):
        self.check_singleton()
        return (
            self.state == "draft"
            and not self.is_expired
            and self.require_payment
            and self.amount_total > 0
            and not self._is_confirmation_amount_reached()
        )

    def _has_to_be_signed(self):
        self.check_singleton()
        return (
            self.state == "draft"
            and not self.is_expired
            and self.require_signature
            and not self.signature
        )

    def _get_name_portal_content_view(self):
        self.check_singleton()
        return "sale.sale_order_portal_content"

    def _get_name_tax_totals_view(self):
        return "sale.document_tax_totals"

    def _get_portal_return_action(self):
        self.check_singleton()
        return self.env.ref("sale.action_quotations_with_onboarding")

    def _get_catalog_product_data(self, products, **kwargs):
        pricelist = self.pricelist_id._get_products_price(
            quantity=1.0,
            products=products,
            currency=self.currency_id,
            date=self.date_order,
            **kwargs,
        )
        has_warning_group = self.env.user.has_group("sale.group_warning_sale")
        catalog_data = {}
        for product in products:
            product_data = {"price": pricelist.get(product.id)}
            if product.sale_line_warn_msg and has_warning_group:
                product_data["warning"] = product.sale_line_warn_msg
            catalog_data[product.id] = product_data
        return catalog_data

    def _update_catalog_context(self):
        request.update_context(catalog_skip_tracking=True)

    def _get_catalog_removed_line_price(self, product, **kwargs):
        return self.pricelist_id._get_product_price(
            product=product,
            quantity=1.0,
            currency=self.currency_id,
            date=self.date_order,
            **kwargs,
        )

    def _get_catalog_line_price(self, line):
        return line._get_price_discounted()

    def _filter_product_documents(self, documents):
        return documents.filtered(
            lambda document: (
                document.attached_on_sale == "quotation"
                or (self.state == "done" and document.attached_on_sale == "sale_order")
            ),
        )

    def _get_lang(self):
        if not self:
            return self.env.lang
        self.check_singleton()

        if self.partner_id.lang and not self.partner_id.is_public:
            return self.partner_id.lang

        return self.env.lang

    def _get_import_template_label(self):
        return _("Import Template for Quotations")

    def _get_import_template_path(self):
        return "/sale/static/xls/quotations_import_template.xlsx"

    def _get_product_documents(self):
        self.check_singleton()

        documents = (
            self.line_ids.product_id.product_document_ids
            | self.line_ids.product_template_id.product_document_ids
        )
        return self._filter_product_documents(documents).sorted()

    def _add_base_lines_for_early_payment_discount(self):
        self.check_singleton()
        epd_lines = []
        if (
            self.payment_term_id.early_discount
            and self.payment_term_id.early_pay_discount_computation == "mixed"
            and self.payment_term_id.discount_percentage
        ):
            percentage = self.payment_term_id.discount_percentage
            currency = self.currency_id or self.company_id.currency_id
            for line in self.line_ids.filtered(lambda x: not x.display_type):
                line_amount_after_discount = (line.price_subtotal / 100) * percentage
                epd_lines.append(
                    self.env["account.tax"]._prepare_base_line_for_taxes_computation(
                        record=self,
                        price_unit=-line_amount_after_discount,
                        quantity=1.0,
                        currency_id=currency,
                        sign=1,
                        special_mode="total_excluded",
                        special_type="early_payment",
                        tax_ids=line.tax_ids.flatten_taxes_hierarchy().filtered(
                            lambda tax: tax.amount_type != "fixed",
                        ),
                    ),
                )
                epd_lines.append(
                    self.env["account.tax"]._prepare_base_line_for_taxes_computation(
                        record=self,
                        price_unit=line_amount_after_discount,
                        quantity=1.0,
                        currency_id=currency,
                        sign=1,
                        special_mode="total_excluded",
                        special_type="early_payment",
                    ),
                )
        return epd_lines

    def _create_down_payment_lines_from_base_lines(self, down_payment_base_lines):
        self.check_singleton()
        return self._create_down_payment_lines(
            [
                self._prepare_down_payment_line_values_from_base_line(base_line)
                for base_line in down_payment_base_lines
            ],
        )

    def _create_down_payment_section_line_if_needed(self):
        self.check_singleton()
        return self._get_down_payment_section_line()

    @api.model
    def _cron_send_pending_emails(self):
        pending_email_orders = self.search(
            [("pending_email_template_id", "!=", False)],
            limit=200,
            order="date_order ASC",
        )
        self.env["ir.cron"]._commit_progress(remaining=len(pending_email_orders))
        for order in pending_email_orders:
            order._send_mail_order_notification(
                order.pending_email_template_id,
                allow_deferred_sending=False,
            )
            order.pending_email_template_id = None
            remaining_time = self.env["ir.cron"]._commit_progress(processed=1)
            if not remaining_time:
                break

    def _generate_downpayment_invoices(self):
        generated_invoices = self.env["account.move"]

        for order in self:
            downpayment_wizard = order.env["sale.advance.payment.inv"].create(
                {
                    "sale_order_ids": order,
                    "advance_payment_method": "fixed",
                    "fixed_amount": order.amount_paid,
                },
            )
            generated_invoices |= downpayment_wizard._create_invoices(order)

        return generated_invoices

    def _get_confirmation_template(self):
        self.check_singleton()
        default_confirmation_template_id = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("sale.default_confirmation_template")
        )
        default_confirmation_template = (
            default_confirmation_template_id
            and self.env["mail.template"]
            .browse(int(default_confirmation_template_id))
            .exists()
        )
        if default_confirmation_template:
            return default_confirmation_template
        else:
            return self.env.ref(
                "sale.mail_template_sale_confirmation",
                raise_if_not_found=False,
            )

    def _get_date_planned(self, date_planneds):
        self.check_singleton()
        return min(date_planneds)

    def _get_duplicate_ref_field(self):
        return "client_order_ref"

    def _get_mail_composer_context(self):
        return {
            **super()._get_mail_composer_context(),
            "proforma": self.env.context.get("proforma", False),
        }

    def _get_mail_template(self):
        self.check_singleton()
        if self.env.context.get("proforma"):
            return self.env.ref(
                "sale.email_template_proforma",
                raise_if_not_found=False,
            )
        elif self.state != "done":
            return self.env.ref(
                "sale.email_template_edi_sale",
                raise_if_not_found=False,
            )
        else:
            return self._get_confirmation_template()

    @api.model
    def _get_note_url(self):
        return self.env.company.get_base_url()

    def _get_prepayment_required_amount(self):
        self.check_singleton()

        if not self.require_payment:
            return 0
        else:
            return self.currency_id.round(self.amount_total * self.prepayment_percent)

    def _get_priced_lines(self):
        return self.line_ids.filtered(lambda x: not x.display_type)

    def _prepare_analytic_account_data(self, prefix=None):
        self.check_singleton()
        name = self.name
        if prefix:
            name = prefix + ": " + self.name
        project_plan, _other_plans = self.env["account.analytic.plan"]._get_all_plans()
        return {
            "name": name,
            "code": self.client_order_ref,
            "company_id": self.company_id.id,
            "plan_id": project_plan.id,
            "partner_id": self.partner_id.id,
        }

    def _prepare_confirmation_values(self):
        return {
            "state": "done",
            "date_order": fields.Datetime.now(),
            "date_confirmed": fields.Datetime.now(),
        }

    def _prepare_down_payment_section_line(self, **optional_values):
        self.check_singleton()
        lang = self._get_lang()
        self_lang = self.with_context(lang=lang) if lang != self.env.lang else self
        return {
            "display_type": "line_section",
            "name": self_lang.env._("Down Payments"),
            "product_id": False,
            "product_uom_id": False,
            "quantity": 0,
            "discount": 0,
            "price_unit": 0,
            "account_id": False,
            **optional_values,
        }

    def _prepare_down_payment_line_values_from_base_line(self, base_line):
        self.check_singleton()
        extra_tax_data = self.env["account.tax"]._export_base_line_extra_tax_data(
            base_line,
        )
        return {
            "order_id": self.id,
            "is_downpayment": True,
            "product_qty": 0.0,
            "price_unit": base_line["price_unit"],
            "tax_ids": [Command.set(base_line["tax_ids"].ids)],
            "analytic_distribution": base_line["analytic_distribution"],
            "extra_tax_data": extra_tax_data,
        }

    def _recompute_prices(self):
        lines_to_recompute = self._get_order_lines_price_updatable()
        lines_to_recompute.invalidate_recordset(["pricelist_item_id"])
        lines_to_recompute.discount = 0.0
        lines_to_recompute.with_context(
            force_price_recomputation=True,
        )._compute_price_and_discount()
        self.show_update_pricelist = False

    def _recompute_taxes(self):
        lines_to_recompute = self.line_ids.filtered(lambda line: not line.display_type)
        lines_to_recompute._compute_tax_ids()
        self.show_update_fpos = False

    def _send_mail_order_confirmation(self):
        for order in self:
            mail_template = order._get_confirmation_template()
            order._send_mail_order_notification(mail_template)

    def _send_mail_order_notification(self, mail_template, allow_deferred_sending=True):
        self.check_singleton()

        if not mail_template:
            return

        if self.env.su:
            self = self.with_user(SUPERUSER_ID)

        async_send = str2bool(
            self.env["ir.config_parameter"].sudo().get_param("sale.async_emails"),
        )
        cron = self.env.ref("sale.send_pending_emails_cron", raise_if_not_found=False)
        cron_enabled = cron and cron.sudo().active
        if async_send and cron_enabled and allow_deferred_sending:
            self.pending_email_template_id = mail_template
            cron._trigger()
        else:
            self.with_context(force_send=True).message_post_with_source(
                mail_template,
                email_layout_xmlid="mail.mail_notification_layout_with_responsible_signature",
                subtype_xmlid="mail.mt_comment",
            )

    def _send_mail_order_payment_succeeded(self):
        mail_template = self.env.ref(
            "sale.mail_template_sale_payment_executed",
            raise_if_not_found=False,
        )
        for order in self:
            order._send_mail_order_notification(mail_template)

    def _is_confirmation_amount_reached(self):
        self.check_singleton()
        amount_comparison = self.currency_id.compare_amounts(
            self._get_prepayment_required_amount(),
            self.amount_paid,
        )
        return amount_comparison <= 0

    def _is_readonly(self):
        self.check_singleton()
        return self.state == "cancel" or self.locked

    def _is_paid(self):
        self.check_singleton()
        return (
            self.currency_id.compare_amounts(self.amount_paid, self.amount_total) >= 0
        )

    def _can_be_edited_on_portal(self):
        self.check_singleton()
        return self.state == "draft"

    def _get_lock_setting_user(self):
        self.check_singleton()
        return self.create_uid

    def _check_confirm_state(self):
        orders_wrong_state = self.filtered(lambda order: order.state != "draft")
        if orders_wrong_state:
            confirmed_orders = orders_wrong_state.filtered(
                lambda o: o.state == "done",
            )
            cancelled_orders = orders_wrong_state.filtered(
                lambda o: o.state == "cancel",
            )

            error_parts = []
            if confirmed_orders:
                error_parts.append(
                    _(
                        "• Already confirmed: %s",
                        format_list(self.env, confirmed_orders.mapped("display_name")),
                    ),
                )
            if cancelled_orders:
                error_parts.append(
                    _(
                        "• Cancelled: %s",
                        format_list(self.env, cancelled_orders.mapped("display_name")),
                    ),
                )

            raise UserError(
                _(
                    "Cannot confirm sale orders that are not in Quotation (draft) state:\n\n%s\n\n"
                    "Only orders in 'Quotation' state can be confirmed.",
                    "\n".join(error_parts),
                ),
            )

    def _check_confirm_analytic_distribution(self):
        self.line_ids._check_analytic_distribution()

    def _get_fields_state_frozen(self):
        return {
            "done": {"pricelist_id"},
        }
