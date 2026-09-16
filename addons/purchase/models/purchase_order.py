from collections import defaultdict
from urllib.parse import urlencode

from dateutil.relativedelta import relativedelta
from markupsafe import Markup, escape

from odoo import api, fields, models
from odoo.exceptions import AccessDenied, AccessError, UserError, ValidationError
from odoo.fields import Command, Domain
from odoo.libs.datetime import timezone
from odoo.tools import (
    SQL,
    format_amount,
    format_date,
    formatLang,
)
from odoo.tools.translate import _

from odoo.addons.purchase import const


class PurchaseOrder(models.Model):
    _name = "purchase.order"
    _inherit = [
        "mixin.order",
        "mixin.order.amount",
        "mixin.order.invoice",
        "mixin.order.merge",
        "mixin.account.document.import",
    ]
    _description = "Purchase Order"
    _check_company_auto = True
    _order = "priority desc, id desc"

    _price_history_action = "purchase.action_purchase_history"

    _order_type = "purchase"
    _sequence_code = "purchase.order"
    _invoice_move_direction = "in"
    _partner_payment_term_field = "property_supplier_payment_term_id"
    _lock_setting_field = "order_lock_po"
    _auto_lock_group = "purchase.group_auto_done_setting"
    _mark_sent_context_key = "mark_rfq_as_sent"
    _display_name_context_key = "purchase_show_partner_name"
    _portal_url_prefix = "purchase"
    _product_ok_field = "purchase_ok"

    def _get_fields_rec_search_base(self):
        return ["name", "partner_ref"]

    partner_id = fields.Many2one(
        string="Vendor",
        help="You can find a vendor by its Name, TIN, Email or Internal Reference.",
    )
    partner_bill_count = fields.Integer(related="partner_id.supplier_invoice_count")
    dest_address_id = fields.Many2one(
        comodel_name="res.partner",
        string="Dropship Address",
        index=True,
        check_company=True,
        tracking=True,
        help="Put an address if you want to deliver directly from the vendor to the customer. "
        "Otherwise, keep empty to deliver to your own company.",
    )
    user_id = fields.Many2one(
        string="Buyer",
        domain=lambda self: """
            [
                ('all_group_ids', 'in', {}),
                ('share', '=', False),
                ('company_ids', '=', company_id),
            ]
        """.format(
            self.env.ref("purchase.group_purchase_user").ids,
        ),
    )
    journal_id = fields.Many2one(
        domain=[("type", "=", "purchase")],
        help="If set, the PO will invoice in this journal; "
        "otherwise the purchase journal with the lowest sequence is used.",
    )
    state = fields.Selection(selection=const.ORDER_STATE)
    tag_ids = fields.Many2many(
        comodel_name="srm.tag",
        relation="purchase_order_tag_rel",
        column1="order_id",
        column2="tag_id",
        string="Tags",
    )
    date_validity = fields.Date(help="Validity of the RFQ, after which it expires.")
    date_confirmed = fields.Datetime(help="Date when the purchase order was confirmed.")
    date_calendar_start = fields.Datetime(
        compute="_compute_date_calendar_start",
        store=True,
        readonly=True,
    )

    line_ids = fields.One2many(comodel_name="purchase.order.line")
    date_commitment = fields.Datetime(
        string="Expected Arrival",
        compute="_compute_date_commitment",
        store=True,
        index=True,
        readonly=False,
        help="Delivery date promised by vendor. "
        "This date is used to determine expected arrival of products.",
    )
    invoice_ids = fields.Many2many(string="Bills")
    invoice_count = fields.Integer(string="Bill Count")

    origin = fields.Char(
        string="Source",
        help="Reference of the document that generated this purchase order "
        "request (e.g. a sales order)",
    )
    partner_ref = fields.Char(
        string="Vendor Reference",
        help="Reference of the sales order or bid sent by the vendor. "
        "It's used to do the matching when you receive the "
        "products as this reference is usually written on the "
        "delivery order sent by your vendor.",
    )
    acknowledged = fields.Boolean(
        help="It indicates that the vendor has acknowledged the receipt of the purchase order."
    )
    sent = fields.Boolean(help="The RFQ has been sent to the vendor.")
    printed_before = fields.Boolean(help="The RFQ has already been printed.")
    purchase_warning_text = fields.Text(
        string="Purchase Warning",
        compute="_compute_purchase_warning_text",
        depends_context=("uid",),
        help="Internal warning for the partner or the products as set by the user.",
    )
    duplicated_order_ids = fields.Many2many(comodel_name="purchase.order")
    receipt_reminder_email = fields.Boolean(
        compute="_compute_receipt_reminder",
        store=True,
        readonly=False,
    )
    reminder_date_before_receipt = fields.Integer(
        string="Days Before Receipt",
        compute="_compute_receipt_reminder",
        store=True,
        readonly=False,
    )

    def copy(self, default=None):
        ctx = dict(self.env.context)
        ctx.pop("default_product_id", None)
        self = self.with_context(ctx)
        new_orders = super().copy(default=default)
        for line in new_orders.line_ids:
            if line.product_id:
                line.date_is_manual = False
                line.date_commitment = line._get_date_commitment(
                    line.selected_seller_id
                )
        return new_orders

    def _get_confirmed_type_name(self):
        return _("Purchase Order")

    @api.depends("state", "date_order", "date_confirmed")
    def _compute_date_calendar_start(self):
        for order in self:
            order.date_calendar_start = (
                order.date_confirmed if order.state == "done" else order.date_order
            )

    def _get_validity_days(self):
        self.check_singleton()
        return self.company_id.po_quotation_validity_days

    def _get_default_user_from_partner(self):
        self.check_singleton()
        return (
            self.partner_id.user_purchase_id
            or self.commercial_partner_id.user_purchase_id
            or (
                self.env.user.has_group("purchase.group_purchase_user")
                and self.env.user
            )
            or self.env["res.users"]
        )

    @api.depends("state", "partner_id", "partner_ref", "origin")
    def _compute_duplicated_order_ids(self):
        super()._compute_duplicated_order_ids()

    @api.depends("company_id", "partner_id")
    def _compute_currency_id(self):
        for order in self:
            order = order.with_company(order.company_id)
            order.currency_id = (
                order.partner_id.property_purchase_currency_id
                or order.company_id.currency_id
            )

    @api.depends(
        "company_id",
        "partner_id",
        "partner_id.receipt_reminder_email",
        "partner_id.reminder_date_before_receipt",
    )
    def _compute_receipt_reminder(self):
        for order in self:
            partner = order.partner_id.with_company(order.company_id)
            order.receipt_reminder_email = partner.receipt_reminder_email
            order.reminder_date_before_receipt = partner.reminder_date_before_receipt

    @api.depends("state", "line_ids", "line_ids.date_commitment")
    def _compute_date_commitment(self):
        for order in self:
            if order.state == "cancel":
                order.date_commitment = False
                continue

            dates_list = order.line_ids.filtered(
                lambda line: not line.display_type and line.date_commitment,
            ).mapped("date_commitment")
            if dates_list:
                order.date_commitment = min(dates_list)
            else:
                order.date_commitment = False

    @api.depends_context("show_total_amount")
    @api.depends("currency_id", "name", "partner_ref", "amount_total")
    def _compute_display_name(self):
        super()._compute_display_name()

    def _get_display_name_suffix(self):
        suffix = ""
        if self.partner_ref:
            suffix += " (" + self.partner_ref + ")"
        if self.env.context.get("show_total_amount") and self.amount_total:
            suffix += ": " + formatLang(
                self.env,
                self.amount_total,
                currency_obj=self.currency_id,
            )
        return suffix

    def _get_all_documents_group(self):
        return "purchase.group_purchase_user_all"

    def _get_warning_group(self):
        return "purchase.group_warning_purchase"

    def _get_partner_warn_field(self):
        return "purchase_warn_msg"

    def _get_line_warn_field(self):
        return "purchase_line_warn_msg"

    @api.depends(
        "partner_id.name",
        "partner_id.purchase_warn_msg",
        "partner_id.parent_id.name",
        "partner_id.parent_id.purchase_warn_msg",
        "line_ids.purchase_line_warn_msg",
        "line_ids.product_id.name",
    )
    def _compute_purchase_warning_text(self):
        self._compute_warning_text("purchase_warning_text")

    def _get_domain_is_late_with_polarity(self, domain, positive):
        lines_domain = Domain("order_id", "any", domain) & Domain.custom(
            to_sql=lambda model, alias, query: SQL(
                "%s < %s" if positive else "%s >= %s",
                model._field_to_sql(alias, "qty_transferred", query),
                model._field_to_sql(alias, "product_qty", query),
            ),
        )
        return Domain("line_ids", "any", lines_domain)

    def onchange(self, values, field_names, fields_spec):
        result = super().onchange(values, field_names, fields_spec)
        if (
            any(self._is_date_commitment_removed_by(field) for field in field_names)
            and "value" in result
        ):
            for line in result["value"].get("line_ids", []):
                if line[0] == Command.UPDATE and "date_commitment" in line[2]:
                    del line[2]["date_commitment"]
        return result

    @api.onchange("partner_id", "company_id")
    def onchange_partner_id(self):
        self = self.with_company(self.company_id)
        if not self.partner_id:
            self.fiscal_position_id = False
        else:
            self.fiscal_position_id = self.env[
                "account.fiscal.position"
            ]._get_fiscal_position(self.partner_id)
            self.payment_term_id = self.partner_id.property_supplier_payment_term_id.id
            if self.partner_id.user_purchase_id:
                self.user_id = self.partner_id.user_purchase_id
        return {}

    @api.onchange("date_commitment")
    def _onchange_date_commitment(self):
        if self.date_commitment:
            self.line_ids.filtered(
                lambda line: not line.display_type,
            ).date_commitment = self.date_commitment

    @api.onchange("company_id", "fiscal_position_id")
    def _onchange_fiscal_position_id(self):
        self.line_ids._compute_tax_ids()

    def action_bill_matching(self):
        self.check_singleton()
        product_ids = self.line_ids.product_id.ids
        return {
            "name": _("Bill Matching"),
            "type": "ir.actions.act_window",
            "res_model": "purchase.bill.line.match",
            "views": [
                (self.env.ref("purchase.purchase_bill_line_match_list").id, "list"),
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

    def _action_confirm(self):
        self._create_supplier_to_product()

    def action_draft(self):
        self.filtered(lambda order: order.state in ("draft", "cancel")).write(
            {"state": "draft"},
        )

    def action_lock(self):
        for order in self:
            if not order._is_lock_required() and not self.env.user.has_group(
                "purchase.group_order_lock"
            ):
                raise AccessError(
                    _("You are not allowed to lock a purchase order."),
                )
        self.write({"locked": True, "priority": "0"})

    def action_unlock(self):
        if not self.env.user.has_group("purchase.group_order_unlock"):
            raise AccessError(
                _("You are not allowed to unlock a purchase order."),
            )
        return super().action_unlock()

    def _merge_check_selection(self, orders):
        if len(orders) < 2:
            raise UserError(
                _("Please select at least two RFQs to merge."),
            )

    def _get_merge_group_description(self):
        return _("- Vendor\n- Currency\n- Dropship Address")

    def _get_merge_result_name(self):
        return _("Merged RFQs")

    def _merge_finalize(self, target, sources):
        super()._merge_finalize(target, sources)
        target._merge_alternative_po(sources)

    def action_send_rfq(self):
        self.check_singleton()
        return self._action_send_by_email()

    def _get_mail_composer_action_name(self):
        return _("Compose Email")

    def _prepare_mail_composer_context(self):
        return {**self.env.context, **super()._prepare_mail_composer_context()}

    def _prepare_mail_composer_lang_context(self):
        return {
            **super()._prepare_mail_composer_lang_context(),
            "model_description": self.type_name,
        }

    def action_view_invoice(self, invoices=False):
        if not invoices:
            self.invalidate_model(["invoice_ids"])
            invoices = self.invoice_ids

        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "account.action_move_in_invoice_type",
        )

        if len(invoices) > 1:
            action["domain"] = [("id", "in", invoices.ids)]
        elif len(invoices) == 1:
            res = self.env.ref("account.view_move_form", False)
            form_view = [((res and res.id) or False, "form")]
            if "views" in action:
                action["views"] = form_view + [
                    (state, view) for state, view in action["views"] if view != "form"
                ]
            else:
                action["views"] = form_view
            action["res_id"] = invoices.id
        else:
            action = {"type": "ir.actions.act_window_close"}

        context = {
            "default_move_type": "in_invoice",
        }
        if len(self) == 1:
            context.update(
                {
                    "default_partner_id": self.partner_id.id,
                    "default_invoice_payment_term_id": self.payment_term_id.id
                    or self.partner_id.property_supplier_payment_term_id.id
                    or self.env["account.move"]
                    .default_get(["invoice_payment_term_id"])
                    .get("invoice_payment_term_id"),
                    "default_invoice_origin": self.name,
                },
            )
        action["context"] = context
        return action

    def _create_update_date_activity(self, updated_dates):
        note = Markup("<p>%s</p>\n") % _(
            "%s modified receipt dates for the following products:",
            self.partner_id.name,
        )
        for line, date in updated_dates:
            note += Markup("<p> - %s</p>\n") % _(
                "%(product)s from %(original_receipt_date)s to %(new_receipt_date)s",
                product=line.product_id.display_name,
                original_receipt_date=line.date_commitment.date(),
                new_receipt_date=date.date(),
            )
        activity = self.activity_schedule(
            "mail.mail_activity_data_warning",
            summary=_("Date Updated"),
            user_id=self.user_id.id,
        )
        activity.note = note
        return activity

    def _update_notify_recipient_groups(self, groups):
        try:
            customer_portal_group = next(
                group for group in groups if group[0] == "portal_customer"
            )
        except StopIteration:
            pass
        else:
            access_opt = customer_portal_group[2].setdefault("button_access", {})
            if self.env.context.get("is_reminder"):
                access_opt["title"] = _("View")
            else:
                access_opt.update(
                    title=_("View %s", self.type_name),
                    url=self.get_base_url() + self.get_confirm_url(),
                )

    def _get_mail_subtitles(self, render_context):
        subtitles = [render_context["record"].name]
        if self.state == "draft":
            subtitles.append(
                _(
                    "Order\N{NO-BREAK SPACE}due\N{NO-BREAK SPACE}%(date)s",
                    date=format_date(
                        self.env,
                        self.date_order,
                        lang_code=render_context.get("lang"),
                    ),
                ),
            )
        else:
            subtitles.append(
                format_amount(
                    self.env,
                    self.amount_total,
                    self.currency_id,
                    lang_code=render_context.get("lang"),
                ),
            )
        return subtitles

    def _get_state_track_subtype_xmlid(self, init_values):
        if "state" in init_values and self.state == "done":
            return "purchase.mt_rfq_confirmed"
        elif "locked" in init_values and self.locked:
            return "purchase.mt_rfq_done"
        elif "sent" in init_values and self.sent:
            return "purchase.mt_rfq_sent"

        return None

    def _update_update_date_activity(self, updated_dates, activity):
        for line, date in updated_dates:
            activity.note += Markup("<p> - %s</p>\n") % _(
                "%(product)s from %(original_receipt_date)s to %(new_receipt_date)s",
                product=line.product_id.display_name,
                original_receipt_date=line.date_commitment.date(),
                new_receipt_date=date.date(),
            )

    def action_add_from_catalog(self):
        res = super().action_add_from_catalog()
        kanban_view_id = self.env.ref(
            "purchase.view_product_product_kanban_catalog_purchase_only",
        ).id
        res["views"][0] = (kanban_view_id, "kanban")
        res["search_view_id"] = [
            self.env.ref("purchase.view_product_product_search_catalog").id,
            "search",
        ]
        res["context"]["partner_id"] = self.partner_id.id
        return res

    def _prepare_catalog_extra_context(self):
        return {
            **super()._prepare_catalog_extra_context(),
            "precision": self.env["decimal.precision"].get_precision("Product Unit"),
            "product_catalog_currency_id": self.currency_id.id,
            "product_catalog_digits": self.line_ids._fields["price_unit"].get_digits(
                self.env,
            ),
            "search_default_seller_ids": self.partner_id.name,
            "show_sections": bool(self.id),
        }

    def _get_product_catalog_order_data(self, products, **kwargs):
        res = super()._get_product_catalog_order_data(products, **kwargs)
        for product in products:
            res[product.id] |= self._get_product_price_and_data(product)
        return res

    def _get_catalog_editable_states(self):
        return {"draft", "sent"}

    def _get_catalog_removed_line_price(self, product, **kwargs):
        return self._get_product_price_and_data(product)["price"]

    def _catalog_on_line_created(self, line, **kwargs):
        line = super()._catalog_on_line_created(line, **kwargs)
        if line.selected_seller_id:
            seller = line.selected_seller_id
            price = seller.price
            if seller.currency_id != self.currency_id:
                price = seller.currency_id._convert(price, self.currency_id)
            line.price_unit = line.price_unit_auto = price
            line.discount = seller.discount
        return line

    def _get_catalog_line_price(self, line):
        return line.price_unit_discounted_taxexc

    def _get_import_template_label(self):
        return _("Import Template for Requests for Quotation")

    def _get_import_template_path(self):
        return "/purchase/static/xls/requests_for_quotation_import_template.xlsx"

    def _create_downpayments(self, line_vals):
        return self._create_down_payment_lines(line_vals)

    def _get_invoiceable_lines(self, final=False):
        self.check_singleton()
        return self.line_ids

    def _prepare_invoice_line_commands(self, invoiceable_lines, sequence=10):
        commands = []
        pending_section = None
        for line in invoiceable_lines:
            if line.display_type in ("line_section", "line_subsection"):
                pending_section = line
                continue
            if pending_section:
                for line_vals in pending_section._prepare_aml_vals_list():
                    line_vals.update({"sequence": sequence})
                    commands.append(Command.create(line_vals))
                    sequence += 1
                pending_section = None
            for line_vals in line._prepare_aml_vals_list():
                line_vals.update({"sequence": sequence})
                commands.append(Command.create(line_vals))
                sequence += 1
        return commands, sequence

    def _get_invoice_grouping_keys(self):
        return ["company_id", "partner_id", "currency_id"]

    def _create_invoice_moves(self, invoice_vals_list):
        invoices = self.env["account.move"]
        AccountMove = self.env["account.move"].with_context(
            default_move_type=self._get_invoice_move_types()[0],
        )
        for vals in invoice_vals_list:
            invoices |= AccountMove.with_company(vals["company_id"]).create(vals)
        return invoices

    def create_invoice(self, attachment_ids=False):
        invoices = self._create_invoices()

        if attachment_ids:
            attachments = self.env["ir.attachment"].browse(attachment_ids)
            if attachments:
                if len(invoices) != 1:
                    raise ValidationError(
                        _("You can only upload a bill for a single vendor at a time."),
                    )
                invoices.with_context(
                    skip_is_manually_modified=True
                )._extend_with_attachments(
                    invoices._to_files_data(attachments),
                    new=True,
                )
                invoices.message_post(attachment_ids=attachments.ids)
                attachments.write({"res_model": "account.move", "res_id": invoices.id})

        return invoices

    def action_create_invoice_from_file(self, attachment_ids=False):
        invoices = self.create_invoice(attachment_ids=attachment_ids)
        return self.action_view_invoice(invoices)

    def _create_supplier_to_product(self):
        vals_by_company = defaultdict(list)
        seen = set()
        for order in self:
            partner = order.partner_id.parent_id or order.partner_id
            partners = partner | order.partner_id
            for line in order.line_ids:
                if not line.product_id:
                    continue
                tmpl = line.product_id.product_tmpl_id
                key = (partner.id, tmpl.id)
                if key in seen:
                    continue
                seen.add(key)
                sellers = line.product_id.seller_ids
                if (
                    partners & sellers.partner_id
                    or len(sellers) >= const.MAX_SUPPLIERS_PER_PRODUCT
                ):
                    continue
                price = line.price_unit
                if tmpl.uom_id != line.product_uom_id:
                    price = line.product_uom_id._get_price_in_unit(price, tmpl.uom_id)
                supplierinfo = order._prepare_supplierinfo(
                    partner,
                    line,
                    price,
                    line.currency_id,
                )
                if line.selected_seller_id:
                    supplierinfo["product_name"] = line.selected_seller_id.product_name
                    supplierinfo["product_code"] = line.selected_seller_id.product_code
                    supplierinfo["product_uom_id"] = line.product_uom_id.id
                supplierinfo["product_tmpl_id"] = tmpl.id
                vals_by_company[order.company_id].append(supplierinfo)
        for company, vals_list in vals_by_company.items():
            self.env["product.supplierinfo"].sudo().with_company(company).create(
                vals_list
            )

    def get_acknowledge_url(self):
        return self.get_portal_url(query_string="&acknowledge=True")

    def get_confirm_url(self, confirm_type=None):
        if confirm_type in ["reminder", "reception", "decline"]:
            return self.get_acknowledge_url()
        return self.get_portal_url()

    def _prepare_default_create_section_values(self):
        return {"product_qty": 0}

    def get_localized_date_commitment(self, date_commitment=False):
        self.check_singleton()
        date_commitment = date_commitment or self.date_commitment
        if not date_commitment:
            return False

        if isinstance(date_commitment, str):
            date_commitment = fields.Datetime.from_string(date_commitment)
        tz = self.get_timezone()
        return date_commitment.astimezone(tz)

    def _get_mail_template(self):
        self.check_singleton()
        xmlid = (
            "purchase.email_template_edi_purchase_done"
            if self.state == "done"
            else "purchase.email_template_edi_purchase"
        )
        return (
            self.env.ref(xmlid, raise_if_not_found=False) or self.env["mail.template"]
        )

    @api.model
    def _get_orders_to_remind(self):
        return self.search(
            [
                ("partner_id", "!=", False),
                ("state", "=", "done"),
                ("acknowledged", "=", False),
                ("receipt_reminder_email", "=", True),
                ("line_ids.product_id.type", "!=", "service"),
            ],
        )

    def _get_product_price_and_data(self, product):
        self.check_singleton()
        product_infos = {
            "price": product.standard_price,
            "uomDisplayName": product.uom_id.display_name,
        }
        params = {"order_id": self}
        seller = product._select_seller(
            partner_id=self.partner_id,
            quantity=None,
            date=fields.Date.context_today(self, timestamp=self.date_order),
            uom_id=product.uom_id,
            ordered_by="min_qty",
            params=params,
        )
        if seller:
            product_uom_id = (seller.product_id or seller.product_tmpl_id).uom_id
            price = seller.price_discounted
            if seller.currency_id != self.currency_id:
                price = seller.currency_id._convert(price, self.currency_id)
            if seller.product_uom_id != product_uom_id:
                price = product_uom_id._get_price_report(
                    price, seller.product_uom_id
                )
                product_infos.update(
                    uomFactor=seller.product_uom_id.factor / product_uom_id.factor
                )
            product_infos.update(
                price=price,
                min_qty=seller.min_qty,
                uomDisplayName=seller.product_uom_id.display_name,
            )

        return product_infos

    def _get_report_base_filename(self):
        self.check_singleton()
        return f"Purchase Order-{self.name}"

    def get_timezone(self):
        self.check_singleton()
        return timezone(self.user_id.tz or self.company_id.partner_id.tz or "UTC")

    def get_update_url(self):
        update_param = urlencode({"update": "True"})
        return self.get_portal_url(query_string="&%s" % update_param)

    def _merge_alternative_po(self, rfqs):
        pass

    @api.model
    def _get_dashboard_count_domains(self):
        return {
            "draft": [("state", "=", "draft")],
            "sent": [("sent", "=", True), ("state", "=", "draft")],
            "late": [
                ("state", "=", "draft"),
                ("date_order", "<", fields.Datetime.now()),
            ],
            "not_acknowledged": [("state", "=", "done"), ("acknowledged", "=", False)],
            "late_receipt": [("state", "=", "done"), ("is_late", "=", True)],
        }

    @api.model
    def get_dashboard_data(self):
        if not self.env.user._is_internal():
            raise AccessDenied

        self.browse().check_access("read")

        count_domains = self._get_dashboard_count_domains()
        result = {
            scope: {
                **{key: {"all": 0, "priority": 0} for key in count_domains},
                "days_to_order": 0,
            }
            for scope in ("global", "my")
        }
        result["days_to_purchase"] = 0

        def _update(key, dict_to_update, group):
            for priority, user_id, count in group:
                my = user_id == self.env.user
                dict_to_update["global"][key]["all"] += count
                if priority != "0":
                    dict_to_update["global"][key]["priority"] += count
                if not my:
                    continue
                dict_to_update["my"][key]["all"] += count
                if priority != "0":
                    dict_to_update["my"][key]["priority"] += count

        for key, domain in count_domains.items():
            _update(
                key,
                result,
                self._read_group(  # noqa: E8507 - one aggregate per literal count domain
                    domain, ["priority", "user_id"], ["id:count_distinct"]
                ),
            )

        three_months_ago = fields.Datetime.now() - relativedelta(months=3)

        confirmed = self._search(
            [
                ("state", "=", "done"),
                ("date_confirmed", "!=", False),
                ("create_date", ">=", three_months_ago),
            ],
        )
        self.env.cr.execute(
            SQL(
                """
                SELECT
                    AVG(EXTRACT(EPOCH FROM (date_confirmed - create_date))) AS avg_global_seconds,
                    AVG(CASE WHEN user_id = %(uid)s
                        THEN EXTRACT(EPOCH FROM (date_confirmed - create_date))
                        END) AS avg_my_seconds
                FROM purchase_order
                WHERE id IN %(confirmed)s
                """,
                uid=self.env.user.id,
                confirmed=confirmed.subselect(),
            ),
        )
        row = self.env.cr.fetchone()
        avg_global_deliveries_seconds = row[0] or 0
        avg_my_deliveries_seconds = row[1] or 0

        result["global"]["days_to_order"] = round(
            avg_global_deliveries_seconds / 60 / 60 / 24,
            2,
        )
        result["my"]["days_to_order"] = round(
            avg_my_deliveries_seconds / 60 / 60 / 24,
            2,
        )

        result["multiuser"] = (
            any(
                result["global"][key]["all"] != result["my"][key]["all"]
                for key in count_domains
            )
            or result["global"]["days_to_order"] != result["my"]["days_to_order"]
        )

        return result

    def _prepare_confirmation_values(self):
        return {"state": "done", "date_confirmed": fields.Datetime.now()}

    def _prepare_down_payment_line_section_values(self):
        return {
            **super()._prepare_down_payment_line_section_values(),
            "name": _("Down Payments"),
        }

    def _prepare_grouped_data(self, rfq):
        return (rfq.partner_id.id, rfq.currency_id.id, rfq.dest_address_id.id)

    def _prepare_invoice_vals(self):
        values = super()._prepare_invoice_vals()
        partner_bank_id = self.commercial_partner_id.bank_ids.filtered_domain(
            [("company_id", "in", (False, self.company_id.id))],
        )[:1]
        values["partner_bank_id"] = partner_bank_id.id
        return values

    def _prepare_supplierinfo(self, partner, line, price, currency):
        return {
            "partner_id": partner.id,
            "sequence": (
                max(line.product_id.seller_ids.mapped("sequence")) + 1
                if line.product_id.seller_ids
                else 1
            ),
            "min_qty": 1.0,
            "price": price,
            "currency_id": currency.id,
            "discount": line.discount,
            "delay": 0,
        }

    def _send_reminder_mail(self, send_single=False):
        if not self.env.user.has_group("purchase.group_send_reminder"):
            return None

        template = self.env.ref(
            "purchase.email_template_edi_purchase_reminder",
            raise_if_not_found=False,
        )
        if template:
            orders = self if send_single else self._get_orders_to_remind()
            for order in orders:
                date = order.date_commitment
                if date and (
                    send_single
                    or (
                        date - relativedelta(days=order.reminder_date_before_receipt)
                    ).date()
                    == fields.Date.today()
                ):
                    if send_single:
                        return order._send_reminder_open_composer(template.id)
                    else:
                        order.with_context(is_reminder=True).message_post_with_source(
                            template,
                            email_layout_xmlid="mail.mail_notification_layout_with_responsible_signature",
                            subtype_xmlid="mail.mt_comment",
                        )
        return None

    def _send_reminder_open_composer(self, template_id):
        self.check_singleton()
        ctx = dict(self.env.context or {})
        ctx.update(
            {
                "default_model": "purchase.order",
                "default_res_ids": self.ids,
                "default_template_id": template_id,
                "default_composition_mode": "comment",
                "default_email_layout_xmlid": "mail.mail_notification_layout_with_responsible_signature",
                "force_email": True,
                "mark_rfq_as_sent": True,
                "model_description": self.type_name,
            },
        )
        self = self.with_context(lang=self._get_mail_composer_lang(ctx))
        compose_form_id = self._get_mail_compose_form()
        return {
            "name": _("Compose Email"),
            "type": "ir.actions.act_window",
            "res_model": "mail.compose.message",
            "view_mode": "form",
            "views": [(compose_form_id, "form")],
            "view_id": compose_form_id,
            "target": "new",
            "context": ctx,
        }

    def send_reminder_preview(self):
        self.check_singleton()
        if not self.env.user.has_group("purchase.group_send_reminder"):
            return {
                "toast_message": _("You are not allowed to send reminder emails."),
                "toast_type": "warning",
            }

        template = self.env.ref(
            "purchase.email_template_edi_purchase_reminder",
            raise_if_not_found=False,
        )
        if not template:
            return {
                "toast_message": _("The reminder email template is missing."),
                "toast_type": "warning",
            }
        if not self.env.user.email:
            return {
                "toast_message": _(
                    "Set an email address on your user to preview the reminder."
                ),
                "toast_type": "warning",
            }

        template.with_context(is_reminder=True).send_mail(
            self.id,
            force_send=True,
            raise_exception=False,
            email_layout_xmlid="mail.mail_notification_layout_with_responsible_signature",
            email_values={"email_to": self.env.user.email, "recipient_ids": []},
        )
        return {
            "toast_message": escape(
                _("A sample email has been sent to %s.", self.env.user.email),
            ),
        }

    def _is_date_commitment_updatable(self):
        self.check_singleton()
        return self.state != "cancel" and not self.locked

    def _update_order_lines_date_commitment(self, updated_dates):
        self.check_singleton()
        if not self._is_date_commitment_updatable():
            raise UserError(
                _(
                    "The expected arrival date of %(order)s can no longer be updated.",
                    order=self.display_name,
                ),
            )

        activity = self.env["mail.activity"].search(
            [
                ("summary", "=", _("Date Updated")),
                ("res_model", "=", "purchase.order"),
                ("res_id", "=", self.id),
                ("user_id", "=", self.user_id.id),
            ],
            limit=1,
        )
        if activity:
            self._update_update_date_activity(updated_dates, activity)
        else:
            self._create_update_date_activity(updated_dates)

        for line, date in updated_dates:
            line._update_date_commitment(date)

    def _check_confirm_analytic_distribution(self):
        if not self.env.context.get("validate_analytic"):
            return

        orders_with_errors = {}

        for order in self:
            line_errors = []
            for line in order.line_ids:
                if line.display_type:
                    continue
                try:
                    line._check_distribution(
                        product=line.product_id.id,
                        business_domain="purchase_order",
                        company_id=line.company_id.id,
                    )
                except (UserError, ValidationError) as e:
                    line_errors.append(
                        _(
                            "  • Line %(line_num)s (%(product)s): %(error)s",
                            line_num=line.sequence or "?",
                            product=line.product_id.display_name or _("No product"),
                            error=str(e).split("\n")[0],
                        ),
                    )

            if line_errors:
                orders_with_errors[order] = line_errors

        if orders_with_errors:
            error_details = []
            for order, line_errors in orders_with_errors.items():
                error_details.append(
                    _(
                        "%(order)s:\n%(lines)s",
                        order=order.display_name,
                        lines="\n".join(line_errors),
                    ),
                )

            raise UserError(
                _(
                    "Cannot confirm purchase orders with invalid analytic distributions:\n\n%s\n\n"
                    "Please fix the analytic distribution on the highlighted lines.",
                    "\n\n".join(error_details),
                ),
            )

    def _get_cancel_validation_methods(self):
        return [
            *super()._get_cancel_validation_methods(),
            "_check_cancel_except_invoiced",
        ]

    def _check_cancel_except_invoiced(self):
        orders_with_posted_invoices = self.filtered(
            lambda order: order.invoice_ids.filtered(lambda inv: inv.state == "posted"),
        )

        if orders_with_posted_invoices:
            error_details = []
            for order in orders_with_posted_invoices:
                posted_bills = order.invoice_ids.filtered(lambda i: i.state == "posted")
                bill_names = ", ".join(posted_bills.mapped("name"))
                error_details.append(
                    _(
                        "• %(order)s has posted bills: %(bills)s",
                        order=order.display_name,
                        bills=bill_names,
                    ),
                )

            raise UserError(
                _(
                    "Cannot cancel purchase orders with posted vendor bills:\n\n%s\n\n"
                    "Please cancel or reset the bills to draft first.",
                    "\n".join(error_details),
                ),
            )

    def _is_date_commitment_removed_by(self, field_name):
        return field_name == "line_ids"
