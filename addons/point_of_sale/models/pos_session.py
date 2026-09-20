import logging
import math
from collections import defaultdict
from datetime import timedelta
from itertools import batched, starmap

from markupsafe import Markup
from psycopg.errors import LockNotAvailable

from odoo import _, api, fields, models
from odoo.db.schema import create_index
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Command, Domain
from odoo.models import PREFETCH_MAX
from odoo.tools import float_is_zero, frozendict, plaintext2html

from ..tools import debug_log as dbg

_logger = logging.getLogger(__name__)


class PosSession(models.Model):
    _name = "pos.session"
    _order = "id desc"
    _description = "Point of Sale Session"
    _inherit = [
        "mixin.mail.thread",
        "mixin.mail.activity",
        "mixin.pos.bus",
        "mixin.pos.load",
    ]

    POS_SESSION_STATE = [
        ("opening_control", "Opening Control"),
        ("opened", "In Progress"),
        ("closing_control", "Closing Control"),
        ("closed", "Closed & Posted"),
    ]

    CASH_MOVE_STATES = ("opening_control", "opened")
    CASH_MOVE_TYPES = ("in", "out")

    RECEIVABLE_PAYMENT_TYPES = ("cash", "bank")
    PAYMENT_AMOUNT_BUCKETS = (
        "split_receivables_bank",
        "combine_receivables_bank",
        "split_receivables_cash",
        "combine_receivables_cash",
        "split_receivables_pay_later",
        "combine_receivables_pay_later",
        "split_invoice_receivables",
        "combine_invoice_receivables",
    )
    PAYMENT_LINE_BUCKETS = (
        "split_inv_payment_receivable_lines",
        "combine_inv_payment_receivable_lines",
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        related="config_id.company_id",
        string="Company",
        readonly=True,
    )

    config_id = fields.Many2one(
        comodel_name="pos.config",
        string="Point of Sale",
        index=True,
        required=True,
    )
    name = fields.Char(
        string="Session ID",
        default="/",
        readonly=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Opened By",
        default=lambda self: self.env.uid,
        index=True,
        readonly=False,
        required=True,
        ondelete="restrict",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="config_id.currency_id",
        string="Currency",
        readonly=False,
    )
    start_at = fields.Datetime(
        string="Opening Date",
        readonly=True,
    )
    stop_at = fields.Datetime(
        string="Closing Date",
        copy=False,
        readonly=True,
    )

    state = fields.Selection(
        selection=POS_SESSION_STATE,
        string="Status",
        default="opening_control",
        index=True,
        copy=False,
        readonly=True,
        required=True,
    )

    opening_notes = fields.Text()
    closing_notes = fields.Text()
    cash_control = fields.Boolean(
        string="Has Cash Control",
        compute="_compute_cash_control",
    )
    cash_journal_id = fields.Many2one(
        comodel_name="account.journal",
        compute="_compute_cash_journal_id",
        store=True,
    )

    cash_register_balance_end_real = fields.Monetary(
        string="Ending Balance",
        readonly=True,
    )
    cash_register_balance_start = fields.Monetary(
        string="Starting Balance",
        readonly=True,
    )
    cash_register_balance_end = fields.Monetary(
        string="Theoretical Closing Balance",
        compute="_compute_cash_balance",
        readonly=True,
        help="Opening balance summed to all cash transactions.",
    )
    cash_register_difference = fields.Monetary(
        string="Before Closing Difference",
        compute="_compute_cash_balance",
        readonly=True,
        help="Difference between the theoretical closing balance and the real closing balance.",
    )

    cash_real_transaction = fields.Monetary(
        string="Transaction",
        readonly=True,
    )

    order_ids = fields.One2many(
        comodel_name="pos.order",
        inverse_name="session_id",
        string="Orders",
    )
    order_count = fields.Integer(compute="_compute_order_count")
    statement_line_ids = fields.One2many(
        comodel_name="account.bank.statement.line",
        inverse_name="pos_session_id",
        string="Cash Lines",
        readonly=True,
    )
    failed_pickings = fields.Boolean(compute="_compute_pickings")
    picking_count = fields.Integer(compute="_compute_pickings")
    picking_ids = fields.One2many(
        comodel_name="stock.picking",
        inverse_name="pos_session_id",
    )
    rescue = fields.Boolean(
        string="Recovery Session",
        copy=False,
        readonly=True,
        help="Auto-generated session for orphan orders, ignored in constraints",
    )
    move_id = fields.Many2one(
        comodel_name="account.move",
        string="Journal Entry",
        index=True,
    )
    payment_method_ids = fields.Many2many(
        comodel_name="pos.payment.method",
        related="config_id.payment_method_ids",
        string="Payment Methods",
    )
    total_payments_amount = fields.Float(compute="_compute_total_payments_amount")
    is_in_company_currency = fields.Boolean(
        string="Is Using Company Currency",
        compute="_compute_is_in_company_currency",
    )
    update_stock_at_closing = fields.Boolean(
        string="Stock should be updated at closing"
    )
    bank_payment_ids = fields.One2many(
        comodel_name="account.payment",
        inverse_name="pos_session_id",
        string="Bank Payments",
        help="Account payments representing aggregated and bank split payments.",
    )

    def write(self, vals):
        dbg.lifecycle.debug(
            "pos.session.write: %s keys=%s state->%s",
            dbg.rec(self),
            dbg.keys(vals),
            vals.get("state"),
        )
        if vals.get("state") == "closed":
            for record in self:
                record.config_id._notify(
                    (
                        "CLOSING_SESSION",
                        {
                            "device_identifier": self.env.context.get(
                                "device_identifier", False
                            ),
                            "session_id": record.id,
                        },
                    )
                )
        return super().write(vals)

    @api.model
    def _get_field_relations(self, model, field_names):
        model_fields = self.env[model]._fields
        relations = {}

        for name, params in model_fields.items():
            if field_names:
                if name not in field_names:
                    continue
            elif params.manual:
                continue

            if params.comodel_name:
                relations[name] = {
                    "name": name,
                    "model": params.model_name,
                    "compute": bool(params.compute),
                    "related": bool(params.related),
                    "relation": params.comodel_name,
                    "type": params.type,
                }
                if params.type == "many2one" and params.ondelete:
                    relations[name]["ondelete"] = params.ondelete
                if params.type == "one2many" and params.inverse_name:
                    relations[name]["inverse_name"] = params.inverse_name
                if params.type == "many2many":
                    relations[name]["relation_table"] = self._get_relation_table(params)
            else:
                relations[name] = {
                    "name": name,
                    "type": params.type,
                    "compute": bool(params.compute),
                    "related": bool(params.related),
                }

        return relations

    @api.model
    def _get_relation_table(self, field):
        while field is not None and not field.relation:
            field = field.related_field
        return field.relation if field is not None else None

    @api.model
    def _get_model_names_to_load(self, config):
        return [
            "pos.config",
            "pos.preset",
            "resource.calendar.attendance",
            "pos.order",
            "pos.order.line",
            "pos.pack.operation.lot",
            "pos.payment",
            "pos.payment.method",
            "pos.printer",
            "pos.category",
            "pos.bill",
            "res.company",
            "account.tax",
            "account.tax.group",
            "product.template",
            "product.product",
            "product.attribute",
            "product.attribute.custom.value",
            "product.template.attribute.line",
            "product.template.attribute.value",
            "product.template.attribute.exclusion",
            "product.combo",
            "product.combo.item",
            "res.users",
            "res.partner",
            "phone.number",
            "product.uom",
            "decimal.precision",
            "uom.uom",
            "res.country",
            "res.country.state",
            "res.lang",
            "product.category",
            "product.pricelist",
            "product.pricelist.item",
            "account.cash.rounding",
            "account.fiscal.position",
            "stock.picking.type",
            "res.currency",
            "pos.note",
            "product.tag",
            "ir.module.module",
            "account.move",
            "account.account",
        ]

    def _load_pos_data_search_read(self, data, config):
        return self._load_pos_data_read(self, config)

    @api.model
    def _load_pos_data_fields(self, config):
        return [
            "id",
            "name",
            "user_id",
            "config_id",
            "start_at",
            "stop_at",
            "payment_method_ids",
            "state",
            "update_stock_at_closing",
            "cash_register_balance_start",
            "access_token",
        ]

    @dbg.timed
    def load_data(self, models_to_load):
        response = {}
        dbg.pipeline.debug(
            "[session:%s] load_data: models_to_load=%s last_server_date=%s limited=%s",
            self.name,
            models_to_load,
            self.env.context.get("pos_last_server_date"),
            self.env.context.get("pos_limited_loading", True),
        )
        response["pos.session"] = self._load_pos_data_search_read(
            response, self.config_id
        )

        for model in dict.fromkeys(self._get_model_names_to_load(self.config_id)):
            if models_to_load and model not in models_to_load:
                continue

            try:
                with dbg.timer(self.env, "[session:%s] load %s", self.name, model):
                    response[model] = self.env[model]._load_pos_data_search_read(
                        response, self.config_id
                    )
                dbg.pipeline.debug(
                    "[session:%s] loaded %s: %d rows",
                    self.name,
                    model,
                    len(response[model]),
                )
            except AccessError as e:
                response[model] = []
                _logger.info("Could not load model %s due to AccessError: %s", model, e)

        return response

    @dbg.timed
    def load_data_params(self):
        response = {}
        fields = self._load_pos_data_fields(self.config_id)
        response["pos.session"] = {
            "fields": fields,
            "relations": self._get_field_relations("pos.session", fields),
        }

        for model in dict.fromkeys(self._get_model_names_to_load(self.config_id)):
            fields = self.env[model]._load_pos_data_fields(self.config_id)
            response[model] = {
                "fields": fields,
                "relations": self._get_field_relations(model, fields),
            }

        return response

    @dbg.timed
    def filter_local_data(self, models_to_filter):
        response = {}
        for model, ids in models_to_filter.items():
            existing_records = self.env[model].browse(ids).exists()

            non_existent_ids = set(ids) - set(existing_records.ids)
            inactive_ids = set(existing_records._get_inactive_ids(self.config_id))

            response[model] = list(non_existent_ids | inactive_ids)
            dbg.logic.debug(
                "[session:%s] filter_local_data %s: %d asked, %d gone, %d inactive",
                self.name,
                model,
                len(ids),
                len(non_existent_ids),
                len(inactive_ids),
            )
        return response

    def remove_opening_control_session(self):
        self.check_singleton()
        if not self.exists():
            return {
                "status": "success",
            }
        if self.state != "opening_control" or len(self.order_ids) > 0:
            raise UserError(
                _(
                    "You can only cancel a session that is in opening control state and has no orders."
                )
            )
        dbg.lifecycle.debug("[session:%s] opening-control session removed", self.name)
        self.sudo().unlink()
        return {
            "status": "success",
        }

    def get_pos_ui_product_pricelist_item_by_product(
        self, product_tmpl_ids, product_ids, config_id
    ):
        return (
            self.env["pos.config"]
            .browse(config_id)
            .get_pos_ui_product_pricelist_item_by_product(product_tmpl_ids, product_ids)
        )

    @api.depends("currency_id", "company_id.currency_id")
    def _compute_is_in_company_currency(self):
        for session in self:
            session.is_in_company_currency = (
                session.currency_id == session.company_id.currency_id
            )

    @api.depends(
        "state",
        "payment_method_ids.is_cash_count",
        "order_ids.state",
        "order_ids.payment_ids.amount",
        "order_ids.payment_ids.payment_method_id",
        "statement_line_ids.amount",
        "cash_register_balance_start",
        "cash_register_balance_end_real",
        "cash_real_transaction",
    )
    def _compute_cash_balance(self):
        captured_cash_payments_domain = Domain.AND(
            [
                self._get_domain_captured_payments(),
                [("payment_method_id.is_cash_count", "=", True)],
            ]
        )
        result = self.env["pos.payment"]._read_group(
            captured_cash_payments_domain,
            ["session_id", "payment_method_id"],
            ["amount:sum"],
        )
        cash_payment_map = {
            (session.id, payment_method.id): amount
            for session, payment_method, amount in result
        }
        for session in self:
            cash_payment_method = session.payment_method_ids.filtered("is_cash_count")[
                :1
            ]
            if cash_payment_method:
                total_cash_payment = (
                    cash_payment_map.get((session.id, cash_payment_method.id)) or 0.0
                )
                if session.state == "closed":
                    total_cash = session.cash_real_transaction + total_cash_payment
                else:
                    total_cash = (
                        sum(session.statement_line_ids.mapped("amount"))
                        + total_cash_payment
                    )

                session.cash_register_balance_end = (
                    session.cash_register_balance_start + total_cash
                )
                session.cash_register_difference = (
                    session.cash_register_balance_end_real
                    - session.cash_register_balance_end
                )
            else:
                session.cash_register_balance_end = 0.0
                session.cash_register_difference = 0.0

    @api.depends("order_ids.state", "order_ids.payment_ids.amount")
    def _compute_total_payments_amount(self):
        result = self.env["pos.payment"]._read_group(
            self._get_domain_captured_payments(), ["session_id"], ["amount:sum"]
        )
        session_amount_map = {session.id: amount for session, amount in result}
        for session in self:
            session.total_payments_amount = session_amount_map.get(session.id) or 0

    @api.depends("order_ids")
    def _compute_order_count(self):
        orders_data = self.env["pos.order"]._read_group(
            [("session_id", "in", self.ids)], ["session_id"], ["__count"]
        )
        sessions_data = {session.id: count for session, count in orders_data}
        for session in self:
            session.order_count = sessions_data.get(session.id, 0)

    @api.depends("picking_ids", "picking_ids.state")
    def _compute_pickings(self):
        picking_data = self.env["stock.picking"]._read_group(
            [("pos_session_id", "in", self.ids)],
            ["pos_session_id"],
            ["__count"],
        )
        picking_count_map = {session.id: count for session, count in picking_data}
        failed_data = self.env["stock.picking"]._read_group(
            [("pos_session_id", "in", self.ids), ("state", "!=", "done")],
            ["pos_session_id"],
            ["__count"],
        )
        failed_map = {session.id: count for session, count in failed_data}
        for session in self:
            session.picking_count = picking_count_map.get(session.id, 0)
            session.failed_pickings = bool(failed_map.get(session.id))

    def action_stock_picking(self):
        self.check_singleton()
        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "stock.action_picking_tree_ready"
        )
        action["display_name"] = _("Pickings")
        action["context"] = {}
        action["domain"] = [("id", "in", self.picking_ids.ids)]
        return action

    @api.depends("cash_journal_id", "config_id.cash_control")
    def _compute_cash_control(self):
        for session in self:
            if session.cash_journal_id:
                session.cash_control = session.config_id.cash_control
            else:
                session.cash_control = False

    @api.depends("config_id")
    def _compute_cash_journal_id(self):
        # Initialize the drawer when assigning a register. Later payment-method
        # changes refresh open sessions explicitly in pos.config.write, preserving
        # the journal used by closed sessions and their accounting history.
        for session in self:
            cash_journal = session.payment_method_ids.filtered("is_cash_count")[
                :1
            ].journal_id
            session.cash_journal_id = cash_journal

    def init(self):
        super().init()
        self.env.cr.execute(
            """
            SELECT config_id, array_agg(id ORDER BY id)
              FROM pos_session
             WHERE state != 'closed' AND rescue IS NOT TRUE
          GROUP BY config_id
            HAVING count(*) > 1
            """
        )
        if duplicates := self.env.cr.fetchall():
            _logger.error(
                "Cannot enforce one open pos.session per pos.config: these configs "
                "already have several. Close the extra sessions, then upgrade "
                "point_of_sale again to install the index. %s",
                ", ".join(
                    f"config {config_id}: sessions {ids}"
                    for config_id, ids in duplicates
                ),
            )
            return
        create_index(
            self.env.cr,
            indexname="pos_session_open_per_config_uniq",
            tablename=self._table,
            expressions=["config_id"],
            where="state != 'closed' AND rescue IS NOT TRUE",
            unique=True,
            comment="At most one non-rescue open session per point of sale.",
        )

    @api.constrains("config_id")
    def _check_pos_config(self):
        if self.env.context.get("onboarding_creation", False):
            return
        open_per_config = self._read_group(
            [
                ("state", "!=", "closed"),
                ("config_id", "in", self.config_id.ids),
                ("rescue", "=", False),
            ],
            ["config_id"],
            ["__count"],
        )
        if any(count > 1 for _config, count in open_per_config):
            raise ValidationError(
                _("Another session is already opened for this point of sale.")
            )

    @api.constrains("start_at")
    def _check_start_date(self):
        for record in self:
            if not record.start_at:
                continue
            journal = record.config_id.journal_id
            company = journal.company_id
            start_date = record.start_at.date()
            violated_lock_dates = company._get_violated_lock_dates(
                start_date, True, journal
            )
            if violated_lock_dates:
                raise ValidationError(
                    _(
                        "You cannot create a session starting before: %(lock_date_info)s",
                        lock_date_info=self.env["res.company"]._format_lock_dates(
                            violated_lock_dates
                        ),
                    )
                )

    def _check_invoices_are_posted(self):
        unposted_invoices = (
            self._get_closed_orders()
            .sudo()
            .with_company(self.company_id)
            .account_move.filtered(lambda x: x.state != "posted")
        )
        if unposted_invoices:
            raise UserError(
                _(
                    "You cannot close the POS when invoices are not posted.\nInvoices: %s",
                    "\n".join(
                        f"{invoice.name} - {invoice.state}"
                        for invoice in unposted_invoices
                    ),
                )
            )

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [dict(vals) for vals in vals_list]
        default_config_id = self.env.context.get("default_config_id")
        config_ids = [vals.get("config_id") or default_config_id for vals in vals_list]
        if not all(config_ids):
            raise UserError(_("You should assign a Point of Sale to your session."))

        configs = self.env["pos.config"].browse(list(dict.fromkeys(config_ids)))
        config_by_id = {config.id: config for config in configs}
        for vals, config_id in zip(vals_list, config_ids, strict=True):
            pos_config = config_by_id[config_id]
            vals.update(
                {
                    "config_id": config_id,
                    "update_stock_at_closing": (
                        pos_config.company_id.point_of_sale_update_stock_quantities
                        == "closing"
                    ),
                }
            )
            if vals.get("name", "/") == "/":
                vals["name"] = pos_config._get_next_session_name()

        dbg.lifecycle.debug(
            "pos.session.create: %d vals for configs %s, keys=%s",
            len(vals_list),
            config_ids,
            dbg.vals_keys(vals_list),
        )
        # The partial unique index must see pending closes before inserting a new session.
        with dbg.timer(self.env, "flush session uniqueness fields before create"):
            self.flush_model(["config_id", "state", "rescue"])
        if self.env.user.has_group("point_of_sale.group_pos_user"):
            sessions = super(PosSession, self.sudo()).create(vals_list)
        else:
            sessions = super().create(vals_list)
        dbg.lifecycle.debug(
            "pos.session.create: created %s names=%s",
            dbg.rec(sessions),
            dbg.names(sessions, "name"),
        )

        sessions.action_pos_session_open()
        return sessions

    def unlink(self):
        self.statement_line_ids.unlink()
        return super().unlink()

    def action_pos_session_open(self):
        opening = self.filtered(
            lambda session: (
                session.state == "opening_control"
                and session.config_id.cash_control
                and not session.rescue
            )
        )
        if not opening:
            return True
        latest_sessions = self._read_group(
            [
                ("config_id", "in", opening.config_id.ids),
                ("id", "not in", opening.ids),
            ],
            ["config_id"],
            ["id:max"],
        )
        previous_sessions = self.browse(
            [session_id for _, session_id in latest_sessions]
        )
        latest_per_config = {
            session.config_id.id: session for session in previous_sessions
        }
        dbg.logic.debug(
            "Opening %d sessions: selected %d previous sessions",
            len(opening),
            len(previous_sessions),
        )
        for session in opening:
            last_session = latest_per_config.get(session.config_id.id)
            session.cash_register_balance_start = (
                last_session.cash_register_balance_end_real if last_session else 0.0
            )
            dbg.logic.debug(
                "[session:%s] opening balance %s from %s",
                session.name,
                session.cash_register_balance_start,
                dbg.rec(last_session) if last_session else None,
            )
        return True

    def get_session_orders(self):
        return self.env["pos.order"].search(
            [
                ("session_id", "in", self.ids),
                "|",
                ("preset_time", "=", False),
                ("preset_time", "<=", fields.Datetime.now()),
            ]
        )

    def action_pos_session_closing_control(
        self,
        balancing_account=False,
        amount_to_balance=0,
        bank_payment_method_diffs=None,
    ):
        self.check_singleton()
        bank_payment_method_diffs = bank_payment_method_diffs or {}
        if any(order.state == "draft" for order in self.get_session_orders()):
            raise UserError(
                _(
                    "You cannot close the POS while there are still draft orders for the day."
                )
            )
        if self.state == "closed":
            raise UserError(_("This session is already closed."))
        stop_at = self.stop_at or fields.Datetime.now()
        dbg.lifecycle.debug(
            "[session:%s] %s -> closing_control (cash_control=%s rescue=%s"
            " balancing=%s/%s bank_diffs=%s)",
            self.name,
            self.state,
            self.config_id.cash_control,
            self.rescue,
            dbg.rec(balancing_account) if balancing_account else None,
            amount_to_balance,
            bank_payment_method_diffs,
        )
        self.write({"state": "closing_control", "stop_at": stop_at})
        if not self.config_id.cash_control:
            return self.action_pos_session_close(
                balancing_account, amount_to_balance, bank_payment_method_diffs
            )
        if self.rescue and self.config_id.cash_control:
            default_cash_payment_method_id = self.payment_method_ids.filtered(
                "is_cash_count"
            )[:1]
            if not default_cash_payment_method_id:
                raise UserError(
                    _(
                        "This point of sale has cash control enabled but no cash "
                        "payment method, so its cash register cannot be counted."
                    )
                )
            orders = self._get_closed_orders()
            total_cash = (
                sum(
                    orders.payment_ids.filtered(
                        lambda p: p.payment_method_id == default_cash_payment_method_id
                    ).mapped("amount")
                )
                + self.cash_register_balance_start
            )
            self.cash_register_balance_end_real = total_cash
            dbg.logic.debug(
                "[session:%s] rescue session counted cash %s", self.name, total_cash
            )
        return self.action_pos_session_validate(
            balancing_account, amount_to_balance, bank_payment_method_diffs
        )

    def action_pos_session_validate(
        self,
        balancing_account=False,
        amount_to_balance=0,
        bank_payment_method_diffs=None,
    ):
        return self.action_pos_session_close(
            balancing_account, amount_to_balance, bank_payment_method_diffs
        )

    def action_pos_session_close(
        self,
        balancing_account=False,
        amount_to_balance=0,
        bank_payment_method_diffs=None,
    ):
        return self._close_session(
            balancing_account, amount_to_balance, bank_payment_method_diffs
        )

    @dbg.timed
    def _close_session(
        self,
        balancing_account=False,
        amount_to_balance=0,
        bank_payment_method_diffs=None,
    ):
        bank_payment_method_diffs = bank_payment_method_diffs or {}
        record = self.check_singleton()
        self._check_bank_payment_method_diffs(bank_payment_method_diffs)
        self._lock_sessions(_("Another user is currently closing this session."))
        if self.env.user.has_group("point_of_sale.group_pos_user"):
            record = record.sudo()
        if self.state == "closed":
            raise UserError(_("This session is already closed."))
        data = {}
        has_activity = bool(
            record.get_session_orders().filtered(lambda o: o.state != "cancel")
            or record.statement_line_ids
        )
        dbg.pipeline.debug(
            "[session:%s] _close_session: orders=%d statement_lines=%d activity=%s"
            " update_stock_at_closing=%s",
            self.name,
            len(record.order_ids),
            len(record.statement_line_ids),
            has_activity,
            self.update_stock_at_closing,
        )
        if has_activity:
            with self.env.cr.savepoint() as closing_savepoint:
                self.cash_real_transaction = sum(
                    self.sudo().statement_line_ids.mapped("amount")
                )
                self._check_no_draft_orders()
                self._check_invoices_are_posted()
                cash_difference_before_statements = self.cash_register_difference
                dbg.logic.debug(
                    "[session:%s] cash: real_transaction=%s difference=%s",
                    self.name,
                    self.cash_real_transaction,
                    cash_difference_before_statements,
                )
                if self.update_stock_at_closing:
                    with dbg.timer(
                        self.env, "[session:%s] closing pickings", self.name
                    ):
                        self._create_picking_at_end_of_session()
                        self._get_closed_orders().filtered(
                            lambda o: not o.is_total_cost_computed
                        )._update_total_cost_at_session_closing(
                            self.picking_ids.move_ids
                        )
                data = (
                    record.with_company(record.company_id)
                    .with_context(check_move_validity=False, skip_invoice_sync=True)
                    ._create_account_move(
                        balancing_account, amount_to_balance, bank_payment_method_diffs
                    )
                )

                balance = sum(record.move_id.line_ids.mapped("balance"))
                dbg.logic.debug(
                    "[session:%s] closing entry %s: %d lines, balance=%s",
                    self.name,
                    dbg.rec(record.move_id),
                    len(record.move_id.line_ids),
                    balance,
                )
                try:
                    with self.move_id._check_balanced({"records": self.move_id.sudo()}):
                        pass
                except UserError:
                    dbg.logic.debug(
                        "[session:%s] closing entry unbalanced by %s: roll back closing savepoint and"
                        " force-close wizard",
                        self.name,
                        balance,
                    )
                    closing_savepoint.rollback()
                    return self._open_force_close_wizard(
                        balance, bank_payment_method_diffs
                    )

                self.sudo()._post_statement_difference(
                    cash_difference_before_statements
                )
                if record.move_id.line_ids:
                    with dbg.timer(
                        self.env, "[session:%s] post closing entry", self.name
                    ):
                        record.move_id.with_company(self.company_id)._post()
                else:
                    dbg.logic.debug(
                        "[session:%s] empty closing entry %s unlinked",
                        self.name,
                        dbg.rec(record.move_id),
                    )
                    record.move_id.sudo().unlink()
                paid_orders = record.order_ids.filtered(
                    lambda order: order.state == "paid"
                )
                dbg.lifecycle.debug(
                    "[session:%s] orders paid -> done: %s",
                    self.name,
                    dbg.rec(paid_orders),
                )
                paid_orders.write({"state": "done"})
                with dbg.timer(self.env, "[session:%s] reconcile", self.name):
                    self.sudo().with_company(
                        self.company_id
                    )._reconcile_account_move_lines(data)
        else:
            self.sudo()._post_statement_difference(self.cash_register_difference)
            record.with_company(
                record.company_id
            )._create_bank_payment_difference_moves(bank_payment_method_diffs)

        if self.config_id.order_edit_tracking:
            edited_orders = self.get_session_orders().filtered(lambda o: o.is_edited)
            if len(edited_orders) > 0:
                body = _(
                    "Edited order(s) during the session:%s",
                    Markup("<br/><ul>%s</ul>")
                    % Markup().join(
                        Markup("<li>%s</li>") % order._get_html_link()
                        for order in edited_orders
                    ),
                )
                self.message_post(body=body)

        self.picking_ids.move_ids.sudo()._trigger_scheduler()

        dbg.lifecycle.debug("[session:%s] %s -> closed", self.name, self.state)
        self.write({"state": "closed"})
        self.env.flush_all()
        return True

    def _lock_sessions(self, error_message):
        """Serialize closing and cash mutations, keeping locks until transaction end."""
        self.check_access("write")
        try:
            with self.env.cr.savepoint(flush=False):
                self.env.cr.execute(
                    "SELECT id FROM pos_session WHERE id = ANY(%s) ORDER BY id FOR UPDATE NOWAIT",
                    (self.ids,),
                )
        except LockNotAvailable as error:
            dbg.logic.debug("Session mutation refused: %s is locked", dbg.rec(self))
            raise UserError(error_message) from error

    def _check_bank_payment_method_diffs(self, differences):
        """Accept finite amounts only for bank methods belonging to this session."""
        if not differences:
            return
        self.check_singleton()
        bank_methods = self.payment_method_ids.filtered(
            lambda method: method.type == "bank"
        )
        if set(differences) - set(bank_methods.ids):
            raise UserError(
                _(
                    "Closing differences must use bank payment methods configured on this session."
                )
            )
        for amount in differences.values():
            self._check_amount_is_finite(amount)

    @api.model
    def _check_amount_is_finite(self, amount):
        try:
            valid = (
                isinstance(amount, (int, float))
                and not isinstance(amount, bool)
                and math.isfinite(amount)
            )
        except OverflowError:
            valid = False
        if not valid:
            dbg.logic.debug("Session amount rejected: %r", amount)
            raise UserError(_("An amount must be a finite number."))

    def _post_statement_difference(self, amount):
        dbg.logic.debug(
            "[session:%s] statement difference %s (cash_control=%s): %s",
            self.name,
            amount,
            self.config_id.cash_control,
            "posted" if amount and self.config_id.cash_control else "skipped",
        )
        if amount and self.config_id.cash_control:
            st_line_vals = {
                "journal_id": self.cash_journal_id.id,
                "pos_cash_move_type": "difference",
                "amount": amount,
                "date": max(
                    self.statement_line_ids.mapped("date"),
                    default=fields.Date.context_today(self),
                ),
                "pos_session_id": self.id,
            }

            if amount < 0.0:
                if not self.cash_journal_id.loss_account_id:
                    raise UserError(
                        _(
                            "Please go on the %s journal and define a Loss Account. This account will be used to record cash difference.",
                            self.cash_journal_id.name,
                        )
                    )

                st_line_vals["payment_ref"] = _(
                    "Cash difference observed during the counting (Loss) - closing"
                )
                st_line_vals["counterpart_account_id"] = (
                    self.cash_journal_id.loss_account_id.id
                )
            else:
                if not self.cash_journal_id.profit_account_id:
                    raise UserError(
                        _(
                            "Please go on the %s journal and define a Profit Account. This account will be used to record cash difference.",
                            self.cash_journal_id.name,
                        )
                    )

                st_line_vals["payment_ref"] = _(
                    "Cash difference observed during the counting (Profit) - closing"
                )
                st_line_vals["counterpart_account_id"] = (
                    self.cash_journal_id.profit_account_id.id
                )

            created_line = (
                self.env["account.bank.statement.line"]
                .with_context(no_retrieve_partner=True)
                .create(st_line_vals)
            )

            if created_line:
                created_line.move_id.message_post(
                    body=_("Related Session: %(link)s", link=self._get_html_link())
                )

    def _open_force_close_wizard(
        self, amount_to_balance, bank_payment_method_diffs=None
    ):
        default_account = self._get_balancing_account()
        wizard = self.env["pos.close.session.wizard"].create(
            {
                "amount_to_balance": amount_to_balance,
                "account_id": default_account.id,
                "account_readonly": not self.env.user.has_group(
                    "account.group_account_readonly"
                ),
                "message": _(
                    "There is a difference between the amounts to post and the amounts of the orders, it is probably caused by taxes or accounting configurations changes."
                ),
            }
        )
        return {
            "name": _("Force Close Session"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "pos.close.session.wizard",
            "res_id": wizard.id,
            "target": "new",
            "context": {
                **self.env.context,
                "active_ids": self.ids,
                "active_model": "pos.session",
                "bank_payment_method_diffs": bank_payment_method_diffs or {},
            },
        }

    @dbg.timed
    def close_session_from_ui(self, bank_payment_method_diff_pairs=None):
        bank_payment_method_diffs = dict(bank_payment_method_diff_pairs or [])
        self.check_singleton()
        open_order_ids = (
            self.get_session_orders().filtered(lambda o: o.state == "draft").ids
        )
        dbg.pipeline.debug(
            "[session:%s] close_session_from_ui: state=%s open_orders=%s bank_diffs=%s",
            self.name,
            self.state,
            open_order_ids,
            bank_payment_method_diffs,
        )
        check_closing_session = self._resolve_close_refusal(bank_payment_method_diffs)
        if check_closing_session:
            dbg.logic.debug(
                "[session:%s] close refused: %s",
                self.name,
                check_closing_session.get("message"),
            )
            check_closing_session["open_order_ids"] = open_order_ids
            return check_closing_session

        future_orders = self.env["pos.order"].search(
            [
                ("session_id", "=", self.id),
                ("state", "=", "draft"),
                ("preset_time", ">", fields.Datetime.now()),
            ]
        )
        dbg.logic.debug(
            "[session:%s] future draft orders detached: %s",
            self.name,
            dbg.rec(future_orders),
        )
        future_orders.session_id = False

        validate_result = self.action_pos_session_closing_control(
            bank_payment_method_diffs=bank_payment_method_diffs
        )

        if isinstance(validate_result, dict):
            dbg.logic.debug(
                "[session:%s] close redirected to action %r",
                self.name,
                validate_result.get("name"),
            )
            return {
                "open_order_ids": open_order_ids,
                "successful": False,
                "message": validate_result.get("name"),
                "redirect": True,
            }

        if self.env.user.email:
            self.post_close_register_message()
        return {"successful": True}

    def post_close_register_message(self):
        self.message_post(body=_("Closed Register"))

    def update_closing_control_state_session(self, notes):
        self.check_singleton()
        self._lock_sessions(_("Another user is currently updating this session."))
        if self.state == "closed":
            raise UserError(_("This session is already closed."))
        dbg.lifecycle.debug(
            "[session:%s] %s -> closing_control from UI (notes=%s)",
            self.name,
            self.state,
            bool(notes),
        )
        self.write(
            {
                "state": "closing_control",
                "stop_at": fields.Datetime.now(),
                "closing_notes": notes,
            }
        )
        self._post_cash_details_message(
            False,
            self.cash_register_balance_end,
            self.cash_register_difference,
            notes,
        )

    def update_closing_cash_details(self, counted_cash):
        self.check_singleton()
        self._lock_sessions(_("Another user is currently updating this session."))
        check_closing_session = self._resolve_close_refusal()
        if check_closing_session:
            open_order_ids = (
                self.get_session_orders().filtered(lambda o: o.state == "draft").ids
            )
            check_closing_session["open_order_ids"] = open_order_ids
            return check_closing_session

        self._check_amount_is_finite(counted_cash)
        if not self.cash_journal_id:
            raise UserError(_("There is no cash register in this session."))

        dbg.logic.debug(
            "[session:%s] counted cash %s (expected %s)",
            self.name,
            counted_cash,
            self.cash_register_balance_end,
        )
        self.cash_register_balance_end_real = counted_cash

        return {"successful": True}

    def _create_diff_account_move_for_payment_method(self, payment_method, diff_amount):
        self.check_singleton()

        outstanding_account = payment_method.outstanding_account_id
        if not outstanding_account and not self.currency_id.is_zero(diff_amount):
            # Resolve the same defaults as a captured payment without creating a
            # zero-value payment or changing any accounting records.
            payment = (
                self.env["account.payment"]
                .with_context(pos_payment=True)
                .new(
                    {
                        "amount": abs(diff_amount),
                        "payment_type": "outbound" if diff_amount < 0 else "inbound",
                        "currency_id": self.currency_id.id,
                        "journal_id": payment_method.journal_id.id,
                        "company_id": self.company_id.id,
                        "destination_account_id": self._get_receivable_account(
                            payment_method
                        ).id,
                    }
                )
            )
            self._update_payment_outstanding_account(payment, diff_amount)
            outstanding_account = payment.outstanding_account_id
        diff_line_vals = self._prepare_diff_line_vals(
            payment_method.id, diff_amount, outstanding_account
        )
        if not diff_line_vals:
            dbg.logic.debug(
                "[session:%s] no diff move for %s (amount=%s)",
                self.name,
                dbg.rec(payment_method),
                diff_amount,
            )
            return

        source_vals, dest_vals = diff_line_vals
        diff_move = self.env["account.move"].create(
            {
                "journal_id": payment_method.journal_id.id,
                "date": fields.Date.context_today(self),
                "ref": self._get_diff_account_move_ref(payment_method),
                "pos_diff_session_id": self.id,
                "pos_diff_payment_method_id": payment_method.id,
                "line_ids": [Command.create(source_vals), Command.create(dest_vals)],
            }
        )
        diff_move._post()
        dbg.pipeline.debug(
            "[session:%s] diff move %s posted for %s amount=%s",
            self.name,
            dbg.rec(diff_move),
            dbg.rec(payment_method),
            diff_amount,
        )

    def _get_diff_account_move_ref(self, payment_method):
        return _(
            "Closing difference in %(payment_method)s (%(session)s)",
            payment_method=payment_method.name,
            session=self.name,
        )

    def _prepare_diff_line_vals(
        self, payment_method_id, diff_amount, outstanding_account=False
    ):
        payment_method = self.env["pos.payment.method"].browse(payment_method_id)
        diff_compare_to_zero = self.currency_id.compare_amounts(diff_amount, 0)
        source_account = payment_method.outstanding_account_id or outstanding_account
        destination_account = self.env["account.account"]

        if diff_compare_to_zero > 0:
            destination_account = payment_method.journal_id.profit_account_id
        elif diff_compare_to_zero < 0:
            destination_account = payment_method.journal_id.loss_account_id

        if diff_compare_to_zero == 0:
            return False
        if not source_account:
            raise UserError(
                _(
                    "Configure an outstanding account for payment method %s before posting its closing difference.",
                    payment_method.name,
                )
            )
        if not destination_account:
            raise UserError(
                _(
                    "Configure a profit or loss account on journal %s before posting its closing difference.",
                    payment_method.journal_id.name,
                )
            )

        amounts = self._update_amounts(
            {"amount": 0, "amount_converted": 0}, {"amount": diff_amount}, self.stop_at
        )
        source_vals = self._prepare_debit_line_vals(
            {"account_id": source_account.id},
            amounts["amount"],
            amounts["amount_converted"],
        )
        dest_vals = self._prepare_credit_line_vals(
            {"account_id": destination_account.id},
            amounts["amount"],
            amounts["amount_converted"],
        )
        return [source_vals, dest_vals]

    def _resolve_close_refusal(self, bank_payment_method_diffs=None):
        bank_payment_method_diffs = bank_payment_method_diffs or {}
        self._check_bank_payment_method_diffs(bank_payment_method_diffs)
        if any(order.state == "draft" for order in self.get_session_orders()):
            return {
                "successful": False,
                "message": _(
                    "You cannot close the POS while there are still draft orders for the day."
                ),
                "redirect": False,
            }
        if self.state == "closed":
            return {
                "successful": False,
                "type": "alert",
                "title": "Session already closed",
                "message": _(
                    "The session has been already closed by another User. "
                    "All sales completed in the meantime have been saved in a "
                    "Rescue Session, which can be reviewed anytime and posted "
                    "to Accounting from Point of Sale's dashboard."
                ),
                "redirect": True,
            }
        if bank_payment_method_diffs:
            no_loss_account = self.env["account.journal"]
            no_profit_account = self.env["account.journal"]
            for payment_method in self.env["pos.payment.method"].browse(
                bank_payment_method_diffs.keys()
            ):
                journal = payment_method.journal_id
                compare_to_zero = self.currency_id.compare_amounts(
                    bank_payment_method_diffs.get(payment_method.id), 0
                )
                if compare_to_zero == -1 and not journal.loss_account_id:
                    no_loss_account |= journal
                elif compare_to_zero == 1 and not journal.profit_account_id:
                    no_profit_account |= journal
            message = ""
            if no_loss_account:
                message += _(
                    "Need loss account for the following journals to post the lost amount: %s\n",
                    ", ".join(no_loss_account.mapped("name")),
                )
            if no_profit_account:
                message += _(
                    "Need profit account for the following journals to post the gained amount: %s",
                    ", ".join(no_profit_account.mapped("name")),
                )
            if message:
                return {"successful": False, "message": message, "redirect": False}
        return None

    def get_cash_in_out_list(self):
        if not self.env.user.has_group("point_of_sale.group_pos_user"):
            raise AccessError(
                _("You don't have the access rights to get the cash in/out list.")
            )
        cash_in_count = 0
        cash_out_count = 0
        cash_in_out_list = []
        for cash_move in self.sudo().statement_line_ids.sorted("create_date"):
            if cash_move.amount > 0:
                cash_in_count += 1
                name = f"Cash in {cash_in_count}"
            else:
                cash_out_count += 1
                name = f"Cash out {cash_out_count}"
            cash_in_out_list.append(
                {
                    "name": cash_move.payment_ref or name,
                    "amount": cash_move.amount,
                    "id": cash_move.id,
                    "date": cash_move.create_date,
                    "cashier_name": cash_move.partner_id.name,
                }
            )
        return cash_in_out_list

    @dbg.timed
    def get_closing_control_data(self):
        if not self.env.user.has_group("point_of_sale.group_pos_user"):
            raise AccessError(
                _(
                    "You don't have the access rights to get the point of sale closing control data."
                )
            )
        self.check_singleton()
        orders = self._get_closed_orders()
        payments_by_method = orders.payment_ids.grouped("payment_method_id")
        cash_method = self.payment_method_ids.filtered("is_cash_count")[:1]
        cash_payments = payments_by_method.get(cash_method, self.env["pos.payment"])
        cash_payment_amount = sum(cash_payments.mapped("amount"))
        non_cash_methods = self.payment_method_ids - cash_method
        non_cash_details = []
        for method in non_cash_methods:
            payments = payments_by_method.get(method, self.env["pos.payment"])
            non_cash_details.append(
                {
                    "name": method.name,
                    "amount": sum(payments.mapped("amount")),
                    "number": len(payments),
                    "id": method.id,
                    "type": method.type,
                }
            )

        cash_in_out_list = self.get_cash_in_out_list()

        return {
            "orders_details": {
                "quantity": len(orders),
                "amount": sum(orders.mapped("amount_total")),
            },
            "opening_notes": self.opening_notes,
            "default_cash_details": {
                "name": cash_method.name,
                "amount": self.cash_register_balance_start
                + cash_payment_amount
                + sum(self.sudo().statement_line_ids.mapped("amount")),
                "opening": self.cash_register_balance_start,
                "payment_amount": cash_payment_amount,
                "moves": cash_in_out_list,
                "id": cash_method.id,
            }
            if cash_method
            else {},
            "non_cash_payment_methods": non_cash_details,
            "is_manager": self.env.user.has_group("point_of_sale.group_pos_manager"),
            "amount_authorized_diff": self.config_id.amount_authorized_diff
            if self.config_id.set_maximum_difference
            else None,
        }

    def _create_picking_at_end_of_session(self):
        self.check_singleton()
        lines_grouped_by_dest_location = {}
        picking_type = self.config_id.picking_type_id

        if not picking_type or not picking_type.default_location_dest_id:
            session_destination_id = (
                self.env["stock.warehouse"]._get_partner_locations()[0].id
            )
        else:
            session_destination_id = picking_type.default_location_dest_id.id

        skipped = 0
        for order in self._get_closed_orders():
            if order._is_real_time_picking_forced() or order.shipping_date:
                skipped += 1
                continue
            destination_id = (
                order.partner_id.property_stock_customer.id or session_destination_id
            )
            if destination_id in lines_grouped_by_dest_location:
                lines_grouped_by_dest_location[destination_id] |= order.lines
            else:
                lines_grouped_by_dest_location[destination_id] = order.lines

        dbg.pipeline.debug(
            "[session:%s] closing pickings: %d destinations, %d orders skipped"
            " (real-time forced or shipping_date): %s",
            self.name,
            len(lines_grouped_by_dest_location),
            skipped,
            dbg.lazy(
                lambda: {k: len(v) for k, v in lines_grouped_by_dest_location.items()}
            ),
        )
        for location_dest_id, lines in lines_grouped_by_dest_location.items():
            self.env["stock.picking"]._create_picking_from_pos_order_lines(
                location_dest_id,
                lines,
                picking_type,
                pos_session=self,
                origin=self.name,
            )

    def _create_balancing_line(self, data, balancing_account, amount_to_balance):
        if not self.company_id.currency_id.is_zero(amount_to_balance):
            balancing_vals = self._prepare_balancing_line_vals(
                amount_to_balance, self.move_id, balancing_account
            )
            MoveLine = data.get("MoveLine")
            MoveLine.create(balancing_vals)
        return data

    def _prepare_balancing_line_vals(self, imbalance_amount, move, balancing_account):
        partial_vals = {
            "name": _("Difference at closing PoS session"),
            "account_id": balancing_account.id,
            "move_id": move.id,
            "partner_id": False,
        }
        imbalance_amount_session = 0
        if not self.is_in_company_currency:
            imbalance_amount_session = self.company_id.currency_id._convert(
                imbalance_amount,
                self.currency_id,
                self.company_id,
                self.stop_at,
            )
        return self._prepare_credit_line_vals(
            partial_vals, imbalance_amount_session, imbalance_amount
        )

    def _get_balancing_account(self):
        return (
            self.company_id.account_default_pos_receivable_account_id
            or self.env["res.partner"]
            ._fields["property_account_receivable_id"]
            .get_company_dependent_fallback(self.env["res.partner"])
            or self.env["account.account"]
        )

    @dbg.timed
    def _create_account_move(
        self,
        balancing_account=False,
        amount_to_balance=0,
        bank_payment_method_diffs=None,
    ):
        account_move = self.env["account.move"].create(
            {
                "journal_id": self.config_id.journal_id.id,
                "date": fields.Date.context_today(self),
                "ref": self.name,
            }
        )
        self.write({"move_id": account_move.id})
        dbg.pipeline.debug(
            "[session:%s] closing entry %s in journal %s",
            self.name,
            dbg.rec(account_move),
            dbg.rec(self.config_id.journal_id),
        )

        data = {"bank_payment_method_diffs": bank_payment_method_diffs or {}}
        with dbg.timer(self.env, "[session:%s] accumulate amounts", self.name):
            data = self._accumulate_amounts(data)
        with dbg.timer(self.env, "[session:%s] non-reconciliable lines", self.name):
            data = self._create_non_reconciliable_move_lines(data)
        with dbg.timer(self.env, "[session:%s] bank payment moves", self.name):
            data = self._create_bank_payment_moves(data)
        with dbg.timer(self.env, "[session:%s] pay-later receivables", self.name):
            data = self._create_pay_later_receivable_lines(data)
        with dbg.timer(self.env, "[session:%s] cash statement lines", self.name):
            data = self._create_cash_statement_lines_and_cash_move_lines(data)
        with dbg.timer(self.env, "[session:%s] invoice receivables", self.name):
            data = self._create_invoice_receivable_lines(data)
        with dbg.timer(self.env, "[session:%s] stock valuation lines", self.name):
            data = self._create_stock_valuation_lines(data)
        if balancing_account and amount_to_balance:
            dbg.logic.debug(
                "[session:%s] balancing line %s on %s",
                self.name,
                amount_to_balance,
                dbg.rec(balancing_account),
            )
            data = self._create_balancing_line(
                data, balancing_account, amount_to_balance
            )

        return data

    def _accumulate_amounts(self, data):
        AccountTax = self.env["account.tax"]

        def prepare_amounts():
            return {"amount": 0.0, "amount_converted": 0.0}

        def prepare_tax_amounts():
            return {
                "amount": 0.0,
                "amount_converted": 0.0,
                "base_amount_converted": 0.0,
            }

        payment_buckets = {
            name: defaultdict(prepare_amounts) for name in self.PAYMENT_AMOUNT_BUCKETS
        }
        payment_buckets.update(
            {
                name: defaultdict(lambda: self.env["account.move.line"])
                for name in self.PAYMENT_LINE_BUCKETS
            }
        )
        sales = defaultdict(prepare_amounts)
        taxes = defaultdict(prepare_tax_amounts)
        stock_expense = defaultdict(prepare_amounts)
        stock_return = defaultdict(prepare_amounts)
        stock_valuation = defaultdict(prepare_amounts)
        rounding_difference = {"amount": 0.0, "amount_converted": 0.0}
        pos_receivable_account = (
            self.company_id.account_default_pos_receivable_account_id
        )
        closed_orders = self._get_closed_orders()
        for order in closed_orders:
            order_is_invoiced = order.is_invoiced
            self._accumulate_order_payments(
                order, pos_receivable_account, payment_buckets
            )

            if not order_is_invoiced:
                base_lines = order._prepare_tax_base_line_values()
                AccountTax._add_tax_details_in_base_lines(base_lines, order.company_id)
                AccountTax._round_base_lines_tax_details(base_lines, order.company_id)
                AccountTax._add_accounting_data_in_base_lines_tax_details(
                    base_lines, order.company_id, include_caba_tags=True
                )
                tax_results = AccountTax._prepare_tax_lines(
                    base_lines, order.company_id
                )
                total_amount_currency = 0.0
                for base_line, to_update in tax_results["base_lines_to_update"]:
                    sale_vals_dict = self._get_sale_key(base_line)
                    sale_key = frozendict(sale_vals_dict)
                    total_amount_currency += to_update["amount_currency"]
                    sales[sale_key] = self._update_amounts(
                        sales[sale_key],
                        {
                            "amount": to_update["amount_currency"],
                            "amount_converted": to_update["balance"],
                        },
                        order.date_order,
                    )
                    if self.config_id._is_quantities_set():
                        sales[sale_key].setdefault("quantity", 0)
                        sales[sale_key]["quantity"] += base_line["quantity"]

                for tax_line in tax_results["tax_lines_to_add"]:
                    tax_key = (
                        tax_line["account_id"],
                        tax_line["tax_repartition_line_id"],
                        tuple(tax_line["tax_tag_ids"][0][2]),
                    )
                    total_amount_currency += tax_line["amount_currency"]
                    taxes[tax_key] = self._update_amounts(
                        taxes[tax_key],
                        {
                            "amount": tax_line["amount_currency"],
                            "amount_converted": tax_line["balance"],
                            "base_amount_converted": tax_line["tax_base_amount"],
                        },
                        order.date_order,
                    )

                if self.config_id.cash_rounding:
                    diff = order.amount_paid + total_amount_currency
                    rounding_difference = self._update_amounts(
                        rounding_difference, {"amount": diff}, order.date_order
                    )

        self._increase_customer_ranks(closed_orders)

        self._accumulate_stock_amounts(stock_expense, stock_return, stock_valuation)

        dbg.pipeline.debug(
            "[session:%s] accumulated over %d orders: sales=%d taxes=%d"
            " stock_expense=%d stock_return=%d stock_valuation=%d rounding=%s"
            " buckets=%s",
            self.name,
            len(closed_orders),
            len(sales),
            len(taxes),
            len(stock_expense),
            len(stock_return),
            len(stock_valuation),
            rounding_difference,
            dbg.lazy(lambda: {k: len(v) for k, v in payment_buckets.items() if v}),
        )
        MoveLine = self.env["account.move.line"].with_context(
            check_move_validity=False, skip_invoice_sync=True
        )

        data.update(
            {
                "taxes": taxes,
                "sales": sales,
                "stock_expense": stock_expense,
                "stock_return": stock_return,
                "stock_valuation": stock_valuation,
                "rounding_difference": rounding_difference,
                "MoveLine": MoveLine,
                **payment_buckets,
            }
        )
        return data

    def _accumulate_order_payments(self, order, pos_receivable_account, buckets):
        currency_rounding = self.currency_id.rounding
        order_is_invoiced = order.is_invoiced

        def add(bucket_name, key, amount, date):
            bucket = buckets[bucket_name]
            bucket[key] = self._update_amounts(bucket[key], {"amount": amount}, date)

        for payment in order.payment_ids:
            amount = payment.amount
            if float_is_zero(amount, precision_rounding=currency_rounding):
                continue
            date = payment.payment_date
            payment_method = payment.payment_method_id
            payment_type = payment_method.type
            is_split_payment = payment_method.split_transactions
            scope = "split" if is_split_payment else "combine"
            key = payment if is_split_payment else payment_method

            dbg.logic.debug(
                "[session:%s][order:%s] payment %s: type=%s scope=%s amount=%s"
                " invoiced=%s",
                self.name,
                order.uuid,
                payment.id,
                payment_type,
                scope,
                amount,
                order_is_invoiced,
            )
            if payment_type == "pay_later":
                if not order_is_invoiced:
                    add(f"{scope}_receivables_pay_later", key, amount, date)
                continue

            if payment_type in self.RECEIVABLE_PAYMENT_TYPES:
                add(f"{scope}_receivables_{payment_type}", key, amount, date)

            if order_is_invoiced:
                buckets[f"{scope}_inv_payment_receivable_lines"][key] |= (
                    payment.account_move_id.line_ids.filtered(
                        lambda line: line.account_id == pos_receivable_account
                    )
                )
                add(
                    f"{scope}_invoice_receivables",
                    key,
                    payment.amount,
                    order.date_order,
                )

    def _accumulate_stock_amounts(self, stock_expense, stock_return, stock_valuation):
        all_picking_ids = (
            self.order_ids.filtered(
                lambda p: not p.is_invoiced and not p.shipping_date
            ).picking_ids.ids
            + self.picking_ids.filtered(lambda p: not p.pos_order_id).ids
        )
        if not all_picking_ids:
            dbg.logic.debug("[session:%s] no pickings to value", self.name)
            return

        stock_moves = (
            self.env["stock.move"]
            .sudo()
            .search(
                [
                    ("picking_id", "in", all_picking_ids),
                    ("product_id.is_storable", "=", True),
                    ("product_id.valuation", "=", "real_time"),
                ]
            )
        )
        dbg.pipeline.debug(
            "[session:%s] stock valuation over %d pickings: %d real-time moves",
            self.name,
            len(all_picking_ids),
            len(stock_moves),
        )
        accounts_per_product = {}
        for stock_moves_batch in (
            stock_moves.browse(b)
            for b in batched(stock_moves._ids, PREFETCH_MAX, strict=False)
        ):
            for move in stock_moves_batch:
                product_accounts = accounts_per_product.get(move.product_id.id)
                if product_accounts is None:
                    product_accounts = accounts_per_product[move.product_id.id] = (
                        move.product_id._get_product_accounts()
                    )
                exp_key = product_accounts["expense"]
                stock_key = product_accounts["stock_valuation"]
                signed_product_qty = move.product_uom_id._get_quantity_in_unit(
                    move.quantity, move.product_id.uom_id, round=False
                )
                is_in = move._is_in()
                if is_in:
                    signed_product_qty *= -1
                amount = signed_product_qty * move._get_price_unit()
                stock_expense[exp_key] = self._update_amounts(
                    stock_expense[exp_key],
                    {"amount": amount},
                    move.picking_id.date_done,
                    force_company_currency=True,
                )
                counterpart = stock_return if is_in else stock_valuation
                counterpart[stock_key] = self._update_amounts(
                    counterpart[stock_key],
                    {"amount": amount},
                    move.picking_id.date_done,
                    force_company_currency=True,
                )

    def _increase_customer_ranks(self, closed_orders):
        partner_rank_increments = defaultdict(int)
        for order in closed_orders:
            if order.is_invoiced:
                continue
            for partner in order.partner_id | order.partner_id.commercial_partner_id:
                partner_rank_increments[partner.id] += 1

        partners_by_increment = defaultdict(list)
        for partner_id, increment in partner_rank_increments.items():
            partners_by_increment[increment].append(partner_id)
        dbg.logic.debug(
            "[session:%s] customer_rank increments: %s",
            self.name,
            dbg.lazy(lambda: {k: len(v) for k, v in partners_by_increment.items()}),
        )
        for increment, partner_ids in partners_by_increment.items():
            self.env["res.partner"].browse(partner_ids)._increase_rank(
                "customer_rank", increment
            )

    def _create_non_reconciliable_move_lines(self, data):
        taxes = data.get("taxes")
        sales = data.get("sales")
        stock_expense = data.get("stock_expense")
        rounding_difference = data.get("rounding_difference")
        MoveLine = data.get("MoveLine")

        tax_vals = [
            self._prepare_tax_vals(
                key,
                amounts["amount"],
                amounts["amount_converted"],
                amounts["base_amount_converted"],
            )
            for key, amounts in taxes.items()
        ]
        tax_names_no_account = [
            line["name"] for line in tax_vals if not line["account_id"]
        ]
        if tax_names_no_account:
            raise UserError(
                _(
                    "Unable to close and validate the session.\n"
                    "Please set corresponding tax account in each repartition line of the following taxes: \n%s",
                    ", ".join(tax_names_no_account),
                )
            )
        rounding_vals = []
        rounding_line_vals = self._prepare_rounding_difference_vals(
            rounding_difference["amount"], rounding_difference["amount_converted"]
        )
        if rounding_line_vals:
            rounding_vals = [rounding_line_vals]

        MoveLine.create(tax_vals)
        move_line_ids = MoveLine.create(
            list(starmap(self._prepare_sale_vals, sales.items()))
        )
        dbg.pipeline.debug(
            "[session:%s] lines: %d tax, %d sale %s, %d stock expense, rounding=%s",
            self.name,
            len(tax_vals),
            len(move_line_ids),
            dbg.rec(move_line_ids),
            len(stock_expense),
            bool(rounding_vals),
        )
        for key, ml_id in zip(sales.keys(), move_line_ids.ids, strict=False):
            sales[key]["move_line_id"] = ml_id
        MoveLine.create(
            [
                self._prepare_stock_expense_vals(
                    key, amounts["amount"], amounts["amount_converted"]
                )
                for key, amounts in stock_expense.items()
            ]
            + rounding_vals
        )

        return data

    def _create_bank_payment_moves(self, data):
        combine_receivables_bank = data.get("combine_receivables_bank")
        split_receivables_bank = data.get("split_receivables_bank")
        bank_payment_method_diffs = data.get("bank_payment_method_diffs")
        MoveLine = data.get("MoveLine")
        payment_method_to_receivable_lines = {}
        payment_to_receivable_lines = {}
        for payment_method, amounts in combine_receivables_bank.items():
            combine_receivable_line = MoveLine.create(
                self._prepare_combine_receivable_vals(
                    payment_method, amounts["amount"], amounts["amount_converted"]
                )
            )
            payment_receivable_line = self._create_combine_account_payment(
                payment_method,
                amounts,
                diff_amount=bank_payment_method_diffs.get(payment_method.id) or 0,
            )
            payment_method_to_receivable_lines[payment_method] = (
                combine_receivable_line | payment_receivable_line
            )

        for payment, amounts in split_receivables_bank.items():
            split_receivable_line = MoveLine.create(
                self._prepare_split_receivable_vals(
                    payment, amounts["amount"], amounts["amount_converted"]
                )
            )
            payment_receivable_line = self._create_split_account_payment(
                payment, amounts
            )
            payment_to_receivable_lines[payment] = (
                split_receivable_line | payment_receivable_line
            )

        self._create_bank_payment_difference_moves(
            bank_payment_method_diffs, combine_receivables_bank
        )

        dbg.pipeline.debug(
            "[session:%s] bank: %d combined methods, %d split payments, diffs=%s",
            self.name,
            len(payment_method_to_receivable_lines),
            len(payment_to_receivable_lines),
            bank_payment_method_diffs,
        )
        data["payment_method_to_receivable_lines"] = payment_method_to_receivable_lines
        data["payment_to_receivable_lines"] = payment_to_receivable_lines
        return data

    def _create_bank_payment_difference_moves(self, differences, combined_methods=()):
        """Post standalone differences not already included in combined payments."""
        for method in self.payment_method_ids.filtered(
            lambda method: method.type == "bank" and method not in combined_methods
        ):
            self._create_diff_account_move_for_payment_method(
                method, differences.get(method.id, 0)
            )

    def _create_pay_later_receivable_lines(self, data):
        MoveLine = data.get("MoveLine")
        combine_receivables_pay_later = data.get("combine_receivables_pay_later")
        split_receivables_pay_later = data.get("split_receivables_pay_later")
        vals = []
        for payment_method, amounts in combine_receivables_pay_later.items():
            vals.append(
                self._prepare_combine_receivable_vals(
                    payment_method, amounts["amount"], amounts["amount_converted"]
                )
            )
        for payment, amounts in split_receivables_pay_later.items():
            vals.append(
                self._prepare_split_receivable_vals(
                    payment, amounts["amount"], amounts["amount_converted"]
                )
            )
        for val in vals:
            val["no_followup"] = False
        data["pay_later_move_lines"] = MoveLine.create(vals)
        return data

    def _update_payment_outstanding_account(self, payment, payment_amount):
        """Assign the payment direction and resolve its outstanding account."""
        payment_type = (
            "outbound"
            if self.currency_id.compare_amounts(payment_amount, 0) < 0
            else "inbound"
        )
        if payment.payment_type != payment_type:
            payment.write(
                {
                    "payment_type": payment_type,
                    "destination_account_id": payment.destination_account_id.id,
                }
            )
        if (
            not payment.outstanding_account_id
            and self.env["account.move"]._get_invoice_in_payment_state() == "in_payment"
        ):
            payment.outstanding_account_id = payment._get_outstanding_account(
                payment.payment_type
            )

        dbg.logic.debug(
            "[session:%s] payment %s direction=%s outstanding=%s destination=%s",
            self.name,
            dbg.rec(payment),
            payment.payment_type,
            dbg.rec(payment.outstanding_account_id),
            dbg.rec(payment.destination_account_id),
        )

    def _create_combine_account_payment(self, payment_method, amounts, diff_amount):
        outstanding_account = payment_method.outstanding_account_id
        destination_account = self._get_receivable_account(payment_method)

        account_payment = (
            self.env["account.payment"]
            .with_context(pos_payment=True)
            .create(
                {
                    "amount": abs(amounts["amount"]),
                    "currency_id": self.currency_id.id,
                    "journal_id": payment_method.journal_id.id,
                    "force_outstanding_account_id": outstanding_account.id,
                    "destination_account_id": destination_account.id,
                    "memo": _(
                        "Combine %(payment_method)s POS payments from %(session)s",
                        payment_method=payment_method.name,
                        session=self.name,
                    ),
                    "pos_payment_method_id": payment_method.id,
                    "pos_session_id": self.id,
                    "company_id": self.company_id.id,
                }
            )
        )

        self._update_payment_outstanding_account(account_payment, amounts["amount"])
        account_payment.action_post()
        dbg.pipeline.debug(
            "[session:%s] combined account.payment %s for %s amount=%s diff=%s",
            self.name,
            dbg.rec(account_payment),
            dbg.rec(payment_method),
            amounts["amount"],
            diff_amount,
        )

        diff_amount_compare_to_zero = self.currency_id.compare_amounts(diff_amount, 0)
        if diff_amount_compare_to_zero != 0:
            self._apply_diff_on_account_payment_move(
                account_payment, payment_method, diff_amount
            )

        return account_payment.move_id.line_ids.filtered(
            lambda line: line.account_id == self._get_receivable_account(payment_method)
        )

    def _apply_diff_on_account_payment_move(
        self, account_payment, payment_method, diff_amount
    ):
        diff_vals = self._prepare_diff_line_vals(
            payment_method.id, diff_amount, account_payment.outstanding_account_id
        )
        if not diff_vals:
            return
        source_vals, dest_vals = diff_vals
        outstanding_line = account_payment.move_id.line_ids.filtered(
            lambda line: line.account_id.id == source_vals["account_id"]
        )
        new_balance = (
            outstanding_line.balance
            + self._convert_amount_to_company_currency(diff_amount, self.stop_at, False)
        )
        new_amount_currency = (
            outstanding_line.amount_currency
            + self.currency_id._convert(
                diff_amount, outstanding_line.currency_id, self.company_id, self.stop_at
            )
        )
        new_balance_compare_to_zero = self.company_id.currency_id.compare_amounts(
            new_balance, 0
        )
        dbg.logic.debug(
            "[session:%s] diff %s applied on %s: outstanding balance %s -> %s",
            self.name,
            diff_amount,
            dbg.rec(account_payment),
            outstanding_line.balance,
            new_balance,
        )
        account_payment.move_id.action_draft()
        account_payment.move_id.write(
            {
                "line_ids": [
                    Command.create(dest_vals),
                    Command.update(
                        outstanding_line.id,
                        {
                            "amount_currency": new_amount_currency,
                            "debit": (new_balance_compare_to_zero > 0 and new_balance)
                            or 0.0,
                            "credit": (new_balance_compare_to_zero < 0 and -new_balance)
                            or 0.0,
                        },
                    ),
                ]
            }
        )
        account_payment.write(
            {
                "amount": abs(new_amount_currency),
                "payment_type": "outbound" if new_amount_currency < 0 else "inbound",
                # Writing the direction queues every compute that hangs off it,
                # and currency_id hangs off journal_id: left to recompute, a payment
                # of a foreign-currency session falls back to the journal's or the
                # company's currency. Keep what the session created it with.
                "journal_id": account_payment.journal_id.id,
                "currency_id": account_payment.currency_id.id,
                "destination_account_id": account_payment.destination_account_id.id,
            }
        )
        account_payment.move_id.action_post()

    def _create_split_account_payment(self, payment, amounts):
        payment_method = payment.payment_method_id
        if not payment_method.journal_id:
            dbg.logic.debug(
                "[session:%s] split payment %s: method has no journal, skipped",
                self.name,
                dbg.rec(payment),
            )
            return self.env["account.move.line"]
        outstanding_account = payment_method.outstanding_account_id
        accounting_partner = payment.partner_id.commercial_partner_id
        destination_account = accounting_partner.property_account_receivable_id

        account_payment = self.env["account.payment"].create(
            {
                "amount": abs(amounts["amount"]),
                "currency_id": self.currency_id.id,
                "partner_id": accounting_partner.id,
                "journal_id": payment_method.journal_id.id,
                "force_outstanding_account_id": outstanding_account.id,
                "destination_account_id": destination_account.id,
                "memo": _(
                    "%(payment_method)s POS payment of %(partner)s in %(session)s",
                    payment_method=payment_method.name,
                    partner=payment.partner_id.display_name,
                    session=self.name,
                ),
                "pos_payment_method_id": payment_method.id,
                "pos_session_id": self.id,
            }
        )

        self._update_payment_outstanding_account(account_payment, amounts["amount"])
        account_payment.action_post()
        return account_payment.move_id.line_ids.filtered(
            lambda line: (
                line.account_id == accounting_partner.property_account_receivable_id
            )
        )

    def _create_cash_statement_lines_and_cash_move_lines(self, data):
        MoveLine = data.get("MoveLine")
        split_receivables_cash = data.get("split_receivables_cash")
        combine_receivables_cash = data.get("combine_receivables_cash")

        split_cash_statement_line_vals = []
        split_cash_receivable_vals = []
        for payment, amounts in split_receivables_cash.items():
            journal_id = payment.payment_method_id.journal_id
            split_cash_statement_line_vals.append(
                self._prepare_split_statement_line_vals(
                    journal_id, amounts["amount"], payment
                )
            )
            split_cash_receivable_vals.append(
                self._prepare_split_receivable_vals(
                    payment, amounts["amount"], amounts["amount_converted"]
                )
            )
        combine_cash_statement_line_vals = []
        combine_cash_receivable_vals = []
        for payment_method, amounts in combine_receivables_cash.items():
            if not float_is_zero(
                amounts["amount"], precision_rounding=self.currency_id.rounding
            ):
                combine_cash_statement_line_vals.append(
                    self._prepare_combine_statement_line_vals(
                        payment_method.journal_id, amounts["amount"], payment_method
                    )
                )
                combine_cash_receivable_vals.append(
                    self._prepare_combine_receivable_vals(
                        payment_method, amounts["amount"], amounts["amount_converted"]
                    )
                )

        BankStatementLine = self.env["account.bank.statement.line"].with_context(
            no_retrieve_partner=True
        )
        split_cash_statement_lines = (
            BankStatementLine.create(split_cash_statement_line_vals)
            .mapped("move_id.line_ids")
            .filtered(lambda line: line.account_id.account_type == "asset_receivable")
        )
        combine_cash_statement_lines = (
            BankStatementLine.create(combine_cash_statement_line_vals)
            .mapped("move_id.line_ids")
            .filtered(lambda line: line.account_id.account_type == "asset_receivable")
        )
        split_cash_receivable_lines = MoveLine.create(split_cash_receivable_vals)
        combine_cash_receivable_lines = MoveLine.create(combine_cash_receivable_vals)
        dbg.pipeline.debug(
            "[session:%s] cash: %d split / %d combined statement lines, receivable"
            " lines %s / %s",
            self.name,
            len(split_cash_statement_line_vals),
            len(combine_cash_statement_line_vals),
            dbg.rec(split_cash_receivable_lines),
            dbg.rec(combine_cash_receivable_lines),
        )

        data.update(
            {
                "split_cash_statement_lines": split_cash_statement_lines,
                "combine_cash_statement_lines": combine_cash_statement_lines,
                "split_cash_receivable_lines": split_cash_receivable_lines,
                "combine_cash_receivable_lines": combine_cash_receivable_lines,
            }
        )
        return data

    def _create_invoice_receivable_lines(self, data):
        MoveLine = data.get("MoveLine")
        combine_invoice_receivables = data.get("combine_invoice_receivables")
        split_invoice_receivables = data.get("split_invoice_receivables")

        data.update(
            {
                "combine_invoice_receivable_lines": self._create_receivable_lines_per_key(
                    MoveLine, combine_invoice_receivables
                ),
                "split_invoice_receivable_lines": self._create_receivable_lines_per_key(
                    MoveLine, split_invoice_receivables
                ),
            }
        )
        return data

    def _create_receivable_lines_per_key(self, MoveLine, amounts_per_key):
        keys = list(amounts_per_key)
        lines = MoveLine.create(
            [
                self._prepare_invoice_receivable_vals(
                    amounts_per_key[key]["amount"],
                    amounts_per_key[key]["amount_converted"],
                )
                for key in keys
            ]
        )
        return dict(zip(keys, lines, strict=True))

    def _create_stock_valuation_lines(self, data):
        MoveLine = data.get("MoveLine")
        stock_valuation = data.get("stock_valuation")
        stock_return = data.get("stock_return")

        stock_valuation_vals = defaultdict(list)
        stock_valuation_lines = {}
        for stock_moves in [stock_valuation, stock_return]:
            for account, amounts in stock_moves.items():
                stock_valuation_vals[account].append(
                    self._prepare_stock_valuation_vals(
                        account, amounts["amount"], amounts["amount_converted"]
                    )
                )

        for stock_valuation_acc, vals in stock_valuation_vals.items():
            stock_valuation_lines[stock_valuation_acc] = MoveLine.create(vals)

        data.update({"stock_valuation_lines": stock_valuation_lines})
        return data

    def _reconcile_account_move_lines(self, data):
        split_cash_statement_lines = data.get("split_cash_statement_lines")
        combine_cash_statement_lines = data.get("combine_cash_statement_lines")
        split_cash_receivable_lines = data.get("split_cash_receivable_lines")
        combine_cash_receivable_lines = data.get("combine_cash_receivable_lines")
        combine_inv_payment_receivable_lines = data.get(
            "combine_inv_payment_receivable_lines"
        )
        split_inv_payment_receivable_lines = data.get(
            "split_inv_payment_receivable_lines"
        )
        combine_invoice_receivable_lines = data.get("combine_invoice_receivable_lines")
        split_invoice_receivable_lines = data.get("split_invoice_receivable_lines")
        payment_method_to_receivable_lines = data.get(
            "payment_method_to_receivable_lines"
        )
        payment_to_receivable_lines = data.get("payment_to_receivable_lines")

        all_lines = (
            split_cash_statement_lines
            | combine_cash_statement_lines
            | split_cash_receivable_lines
            | combine_cash_receivable_lines
        )
        unposted = all_lines.filtered(lambda line: line.move_id.state != "posted")
        dbg.pipeline.debug(
            "[session:%s] reconcile: %d cash lines, posting %s",
            self.name,
            len(all_lines),
            dbg.rec(unposted.move_id),
        )
        unposted.move_id._post(soft=False)

        accounts = all_lines.mapped("account_id")
        lines_by_account = [
            all_lines.filtered(
                lambda l, account=account: l.account_id == account and not l.reconciled
            )
            for account in accounts
            if account.reconcile
        ]
        dbg.logic.debug(
            "[session:%s] cash reconciliation groups: %s",
            self.name,
            dbg.lazy(lambda: [len(lines) for lines in lines_by_account]),
        )
        for lines in lines_by_account:
            lines.with_context(no_cash_basis=True).reconcile()

        for payment_method, lines in payment_method_to_receivable_lines.items():
            receivable_account = self._get_receivable_account(payment_method)
            if receivable_account.reconcile:
                lines.filtered(lambda line: not line.reconciled).with_context(
                    no_cash_basis=True
                ).reconcile()

        for payment, lines in payment_to_receivable_lines.items():
            if payment.partner_id.property_account_receivable_id.reconcile:
                lines.filtered(lambda line: not line.reconciled).with_context(
                    no_cash_basis=True
                ).reconcile()

        dbg.logic.debug(
            "[session:%s] invoice receivable reconciliation: default account"
            " reconcilable=%s, %d combined, %d split",
            self.name,
            self.company_id.account_default_pos_receivable_account_id.reconcile,
            len(combine_inv_payment_receivable_lines),
            len(split_inv_payment_receivable_lines),
        )
        if self.company_id.account_default_pos_receivable_account_id.reconcile:
            for payment_method in combine_inv_payment_receivable_lines:
                lines = combine_inv_payment_receivable_lines[
                    payment_method
                ] | combine_invoice_receivable_lines.get(
                    payment_method, self.env["account.move.line"]
                )
                lines.filtered(lambda line: not line.reconciled).with_context(
                    no_cash_basis=True
                ).reconcile()

            for payment in split_inv_payment_receivable_lines:
                lines = split_inv_payment_receivable_lines[
                    payment
                ] | split_invoice_receivable_lines.get(
                    payment, self.env["account.move.line"]
                )
                lines.filtered(lambda line: not line.reconciled).with_context(
                    no_cash_basis=True
                ).reconcile()

        return data

    def _prepare_rounding_difference_vals(self, amount, amount_converted):
        if not self.config_id.cash_rounding:
            return None
        sign = self.currency_id.compare_amounts(
            amount, 0.0
        ) or self.company_id.currency_id.compare_amounts(amount_converted, 0.0)
        if not sign:
            return None
        rounding_method = self.config_id.rounding_method
        partial_args = {
            "name": "Rounding line",
            "move_id": self.move_id.id,
        }
        if sign < 0:
            partial_args["account_id"] = rounding_method.loss_account_id.id
            return self._prepare_debit_line_vals(
                partial_args, -amount, -amount_converted
            )
        partial_args["account_id"] = rounding_method.profit_account_id.id
        return self._prepare_credit_line_vals(partial_args, amount, amount_converted)

    def _prepare_split_receivable_vals(self, payment, amount, amount_converted):
        accounting_partner = payment.partner_id.commercial_partner_id
        if not accounting_partner:
            raise UserError(
                _(
                    'You have enabled the "Identify Customer" option for %(payment_method)s payment method,'
                    "but the order %(order)s does not contain a customer.",
                    payment_method=payment.payment_method_id.name,
                    order=payment.pos_order_id.name,
                )
            )
        partial_vals = {
            "account_id": accounting_partner.property_account_receivable_id.id,
            "move_id": self.move_id.id,
            "partner_id": accounting_partner.id,
            "name": "%s - %s" % (self.name, payment.payment_method_id.name),
        }
        return self._prepare_debit_line_vals(partial_vals, amount, amount_converted)

    def _prepare_combine_receivable_vals(
        self, payment_method, amount, amount_converted
    ):
        partial_vals = {
            "account_id": self._get_receivable_account(payment_method).id,
            "move_id": self.move_id.id,
            "name": "%s - %s" % (self.name, payment_method.name),
            "display_type": "payment_term",
        }
        return self._prepare_debit_line_vals(partial_vals, amount, amount_converted)

    def _prepare_invoice_receivable_vals(self, amount, amount_converted):
        partial_vals = {
            "account_id": self.company_id.account_default_pos_receivable_account_id.id,
            "move_id": self.move_id.id,
            "name": _("From invoice payments"),
            "display_type": "payment_term",
        }
        return self._prepare_credit_line_vals(partial_vals, amount, amount_converted)

    def _get_sale_key(self, base_line):
        return {
            "account_id": base_line["account_id"].id,
            "sign": -1 if base_line["is_refund"] else 1,
            "tax_ids": tuple(
                base_line["record"]
                .tax_ids_after_fiscal_position.flatten_taxes_hierarchy()
                .ids
            ),
            "base_tag_ids": tuple(base_line["tax_tag_ids"].ids),
            "product_id": base_line["product_id"].id
            if self.config_id.is_closing_entry_by_product
            else False,
        }

    def _prepare_sale_vals(self, key, sale_vals):
        tax_ids = key["tax_ids"]
        product_id = key["product_id"]
        sign = key["sign"]
        applied_taxes = self.env["account.tax"].browse(tax_ids)
        if product_id:
            product = self.env["product.product"].browse(product_id)
            product_name = product.display_name
            product_uom_id = product.uom_id.id
        else:
            product_name = ""
            product_uom_id = False
        title = _("Sales") if sign == 1 else _("Refund")
        name = _("%s untaxed", title)
        if applied_taxes:
            name = _(
                "%(title)s %(product_name)s with %(taxes)s",
                title=title,
                product_name=product_name,
                taxes=", ".join([tax.name for tax in applied_taxes]),
            )
        return {
            "name": name,
            "account_id": key["account_id"],
            "move_id": self.move_id.id,
            "tax_ids": [(6, 0, tax_ids)],
            "tax_tag_ids": [(6, 0, key["base_tag_ids"])],
            "product_id": product_id,
            "display_type": "product",
            "product_uom_id": product_uom_id,
            "currency_id": self.currency_id.id,
            "amount_currency": sale_vals["amount"],
            "balance": sale_vals["amount_converted"],
            "quantity": sale_vals.get("quantity", 1.00) * key["sign"],
        }

    def _prepare_tax_vals(self, key, amount, amount_converted, base_amount_converted):
        account_id, repartition_line_id, tag_ids = key
        tax_rep = self.env["account.tax.repartition.line"].browse(repartition_line_id)
        tax = tax_rep.tax_id
        return {
            "name": tax.name,
            "account_id": account_id,
            "move_id": self.move_id.id,
            "tax_base_amount": abs(base_amount_converted),
            "tax_repartition_line_id": repartition_line_id,
            "tax_tag_ids": [(6, 0, tag_ids)],
            "display_type": "tax",
            "currency_id": self.currency_id.id,
            "amount_currency": amount,
            "balance": amount_converted,
        }

    def _prepare_stock_expense_vals(self, exp_account, amount, amount_converted):
        partial_args = {"account_id": exp_account.id, "move_id": self.move_id.id}
        return self._prepare_debit_line_vals(
            partial_args, amount, amount_converted, force_company_currency=True
        )

    def _prepare_stock_valuation_vals(
        self, stock_val_account, amount, amount_converted
    ):
        partial_args = {"account_id": stock_val_account.id, "move_id": self.move_id.id}
        return self._prepare_credit_line_vals(
            partial_args, amount, amount_converted, force_company_currency=True
        )

    def _prepare_combine_statement_line_vals(self, journal, amount, payment_method):
        amount_values = self._prepare_statement_line_amount_values(journal, amount)
        return {
            "date": fields.Date.context_today(self),
            "payment_ref": self.name,
            "pos_session_id": self.id,
            "pos_cash_move_type": "payment",
            "journal_id": journal.id,
            "counterpart_account_id": self._get_receivable_account(payment_method).id,
            **amount_values,
        }

    def _prepare_split_statement_line_vals(self, journal, amount, payment):
        accounting_partner = payment.partner_id.commercial_partner_id
        amount_values = self._prepare_statement_line_amount_values(journal, amount)
        return {
            "date": fields.Date.context_today(self, timestamp=payment.payment_date),
            "payment_ref": payment.name,
            "pos_session_id": self.id,
            "pos_cash_move_type": "payment",
            "journal_id": journal.id,
            "counterpart_account_id": accounting_partner.property_account_receivable_id.id,
            "partner_id": accounting_partner.id,
            **amount_values,
        }

    def _prepare_statement_line_amount_values(self, journal, amount):
        journal_currency = journal.currency_id or self.company_id.currency_id
        if journal_currency == self.currency_id:
            return {"amount": amount}
        return {
            "amount": self.currency_id._convert(
                amount, journal_currency, self.company_id, self.stop_at
            ),
            "amount_currency": amount,
            "foreign_currency_id": self.currency_id.id,
        }

    def _update_amounts(
        self,
        old_amounts,
        amounts_to_add,
        date,
        round=True,
        force_company_currency=False,
    ):
        new_amounts = {**old_amounts}

        amount = amounts_to_add.get("amount")
        amount_converted = amounts_to_add.get("amount_converted")
        if amount_converted is None:
            if self.is_in_company_currency or force_company_currency:
                amount_converted = amount
            else:
                amount_converted = self._convert_amount_to_company_currency(
                    amount, date, round
                )

        new_amounts["amount"] += amount
        new_amounts["amount_converted"] += amount_converted

        base_amount_converted = amounts_to_add.get("base_amount_converted")
        if base_amount_converted:
            new_amounts["base_amount_converted"] += base_amount_converted

        return new_amounts

    def _prepare_credit_line_vals(
        self,
        partial_move_line_vals,
        amount,
        amount_converted,
        force_company_currency=False,
    ):
        if self.is_in_company_currency or force_company_currency:
            additional_field = {}
        else:
            additional_field = {
                "amount_currency": -amount,
                "currency_id": self.currency_id.id,
            }
        return {
            "debit": -amount_converted if amount_converted < 0.0 else 0.0,
            "credit": max(0.0, amount_converted),
            **partial_move_line_vals,
            **additional_field,
        }

    def _prepare_debit_line_vals(
        self,
        partial_move_line_vals,
        amount,
        amount_converted,
        force_company_currency=False,
    ):
        if self.is_in_company_currency or force_company_currency:
            additional_field = {}
        else:
            additional_field = {
                "amount_currency": amount,
                "currency_id": self.currency_id.id,
            }
        return {
            "debit": max(0.0, amount_converted),
            "credit": -amount_converted if amount_converted < 0.0 else 0.0,
            **partial_move_line_vals,
            **additional_field,
        }

    def _convert_amount_to_company_currency(self, amount, date, round):
        return self.currency_id._convert(
            amount, self.company_id.currency_id, self.company_id, date, round=round
        )

    def action_view_cash_register(self):
        return {
            "name": _("Cash register"),
            "type": "ir.actions.act_window",
            "res_model": "account.bank.statement.line",
            "view_mode": "list,kanban",
            "domain": [("id", "in", self.statement_line_ids.ids)],
        }

    def action_view_journal_items(self):
        self.check_singleton()
        all_related_moves = self._get_related_account_moves()
        return {
            "name": _("Journal Items"),
            "type": "ir.actions.act_window",
            "res_model": "account.move.line",
            "view_mode": "list",
            "view_id": self.env.ref("account.view_account_move_line_list").id,
            "domain": [("id", "in", all_related_moves.mapped("line_ids").ids)],
            "context": {
                "journal_type": "general",
                "search_default_group_by_move": 1,
                "group_by": "move_id",
                "search_default_posted": 1,
            },
        }

    def _get_other_related_moves(self):
        moves = self.env["account.move"].search(
            [("pos_diff_session_id", "in", self.ids)]
        )
        legacy_methods = self.payment_method_ids.filtered(
            lambda pm: pm.type == "bank" and pm.split_transactions
        )
        if legacy_methods:
            moves |= self.env["account.move"].search(
                [
                    ("pos_diff_session_id", "=", False),
                    ("journal_id", "in", legacy_methods.journal_id.ids),
                    (
                        "ref",
                        "in",
                        [self._get_diff_account_move_ref(pm) for pm in legacy_methods],
                    ),
                ]
            )
        return moves

    def _get_related_account_moves(self):
        pickings = self.picking_ids | self._get_closed_orders().mapped("picking_ids")
        invoices = self.mapped("order_ids.account_move")
        invoice_payments = self.mapped("order_ids.payment_ids.account_move_id")
        stock_account_moves = pickings.move_ids.account_move_id
        cash_moves = self.statement_line_ids.mapped("move_id")
        bank_payment_moves = self.bank_payment_ids.mapped("move_id")
        other_related_moves = self._get_other_related_moves()
        return (
            invoices
            | invoice_payments
            | self.move_id
            | stock_account_moves
            | cash_moves
            | bank_payment_moves
            | other_related_moves
        )

    def _get_receivable_account(self, payment_method):
        return (
            payment_method.receivable_account_id
            or self.company_id.account_default_pos_receivable_account_id
        )

    def action_show_payments_list(self):
        return {
            "name": _("Payments"),
            "type": "ir.actions.act_window",
            "res_model": "pos.payment",
            "view_mode": "list,form",
            "domain": self._get_domain_captured_payments(),
            "context": {"search_default_group_by_payment_method": 1},
        }

    def _get_domain_captured_payments(self):
        return [
            ("session_id", "in", self.ids),
            ("pos_order_id.state", "in", ["paid", "done"]),
        ]

    def action_open_frontend(self):
        if not self.ids:
            return {}
        return self.config_id.open_ui()

    def _set_opening_control_data(self, cashbox_value: float, notes: str):
        self._check_amount_is_finite(cashbox_value)
        dbg.lifecycle.debug(
            "[session:%s] %s -> opened (cashbox=%s expected=%s)",
            self.name,
            self.state,
            cashbox_value,
            self.cash_register_balance_start,
        )
        self.state = "opened"
        self.start_at = fields.Datetime.now()
        cash_payment_method_ids = self.config_id.payment_method_ids.filtered(
            lambda pm: pm.is_cash_count
        )
        if notes:
            self.opening_notes = notes
        if cash_payment_method_ids:
            difference = cashbox_value - self.cash_register_balance_start
            self._post_cash_details_message(
                True, self.cash_register_balance_start, difference, notes
            )
            self.cash_register_balance_start = cashbox_value
        elif notes:
            message = _("Opening control message: ")
            message += notes
            self.message_post(body=plaintext2html(message))

    def set_opening_control(self, cashbox_value: float, notes: str):
        self.check_singleton()
        self._lock_sessions(_("Another user is currently updating this session."))
        if self.state != "opening_control":
            dbg.logic.debug(
                "[session:%s] set_opening_control ignored in state %s",
                self.name,
                self.state,
            )
            return

        self._set_opening_control_data(cashbox_value, notes)

    def _post_cash_details_message(self, opening, expected, difference, notes):
        expected_formatted = self.currency_id.format(expected)
        difference_formatted = self.currency_id.format(difference)
        counted_formatted = self.currency_id.format(expected + difference)

        if opening:
            message = _("Opening cash difference: %s \n", difference_formatted)
            message += _("Opening cash expected: %s \n", expected_formatted)
            message += _("Opening cash counted: %s \n", counted_formatted)
        else:
            message = _("Closing difference: %s \n", difference_formatted)
            message += _("Closing expected: %s \n", expected_formatted)
            message += _("Closing counted: %s \n", counted_formatted)

        if notes:
            message += (
                _("Opening control message: ")
                if opening
                else _("Closing control message: ")
            )
            message += notes
        if message:
            self.message_post(
                body=plaintext2html(message),
                email_from=self.env.user.email or "admin@example.com",
            )

    def action_view_order(self):
        return {
            "name": _("Orders"),
            "res_model": "pos.order",
            "view_mode": "list,form",
            "views": [
                (
                    self.env.ref("point_of_sale.view_pos_order_tree_no_session_id").id,
                    "list",
                ),
                (self.env.ref("point_of_sale.view_pos_pos_form").id, "form"),
            ],
            "type": "ir.actions.act_window",
            "domain": [("session_id", "in", self.ids)],
        }

    @api.model
    def _alert_old_sessions(self):
        sessions = self.sudo().search(
            [
                ("start_at", "<=", (fields.Datetime.now() - timedelta(days=7))),
                ("state", "!=", "closed"),
            ]
        )
        already_alerted = self.browse(
            res_id
            for [res_id] in self.env["mail.activity"]._read_group(
                [
                    ("res_model", "=", "pos.session"),
                    ("res_id", "in", sessions.ids),
                    (
                        "activity_type_id",
                        "=",
                        self.env.ref("point_of_sale.mail_activity_old_session").id,
                    ),
                ],
                ["res_id"],
            )
        )
        dbg.lifecycle.debug(
            "cron _alert_old_sessions: %s open >7d, %s already alerted",
            dbg.rec(sessions),
            dbg.rec(already_alerted),
        )
        for session in sessions - already_alerted:
            session.activity_schedule(
                "point_of_sale.mail_activity_old_session",
                user_id=session.user_id.id,
                note=_(
                    "Your PoS Session is open since %(date)s, we advise you to close it and to create a new one.",
                    date=session.start_at,
                ),
            )

    def _check_no_draft_orders(self):
        draft_orders = self.get_session_orders().filtered(
            lambda order: order.state == "draft"
        )
        if draft_orders:
            raise UserError(
                _(
                    "There are still orders in draft state in the session. "
                    "Pay or cancel the following orders to validate the session:\n%s",
                    ", ".join(draft_orders.mapped("name")),
                )
            )
        return True

    def _get_cash_move_label(self, _type):
        return _("Cash In") if _type == "in" else _("Cash Out")

    def _prepare_account_bank_statement_line_vals(
        self, sign, amount, reason, partner_id, extras
    ):
        self.check_singleton()
        return {
            "pos_session_id": self.id,
            "pos_cash_move_type": "manual",
            "journal_id": self.cash_journal_id.id,
            "amount": sign * amount,
            "date": fields.Date.context_today(self),
            "payment_ref": " - ".join(
                part
                for part in (
                    self.name,
                    self._get_cash_move_label(extras["_type"]),
                    reason,
                )
                if part
            ),
            "partner_id": partner_id,
        }

    def try_cash_in_out(self, _type, amount, reason, partner_id, extras):
        if _type not in self.CASH_MOVE_TYPES:
            raise UserError(_("Unknown cash movement type %(type)s.", type=_type))
        self._check_amount_is_finite(amount)
        sign = 1 if _type == "in" else -1
        amount = abs(amount)
        self._lock_sessions(_("Another user is currently updating this session."))

        if no_journal := self.filtered(lambda session: not session.cash_journal_id):
            raise UserError(
                _(
                    "There is no cash payment method for %(sessions)s.",
                    sessions=", ".join(no_journal.mapped("name")),
                )
            )
        sessions = self
        if closed := sessions.filtered(lambda s: s.state not in self.CASH_MOVE_STATES):
            raise UserError(
                _(
                    "You cannot register a cash movement on a session that is no"
                    " longer open: %(sessions)s",
                    sessions=", ".join(closed.mapped("name")),
                )
            )
        if zero_for := sessions.filtered(
            lambda session: not session.currency_id.compare_amounts(amount, 0.0)
        ):
            raise UserError(
                _(
                    "A cash movement must have a non-zero amount, and %(amount)s"
                    " rounds to zero in %(sessions)s.",
                    amount=amount,
                    sessions=", ".join(zero_for.mapped("name")),
                )
            )

        vals_list = [
            session._prepare_account_bank_statement_line_vals(
                sign, amount, reason, partner_id, {**extras, "_type": _type}
            )
            for session in sessions
        ]
        dbg.lifecycle.debug(
            "[session:%s] cash %s %s reason=%r partner=%s",
            dbg.names(sessions, "name"),
            _type,
            amount,
            reason,
            partner_id,
        )

        self.env["account.bank.statement.line"].with_context(
            no_retrieve_partner=True
        ).create(vals_list)

    def remove_cash_in_out(self, absl_id, partner_id):
        self.check_singleton()
        if not self.env.user.has_group("account.group_account_basic"):
            raise AccessError(
                _("You don't have the access rights to delete a cash in/out.")
            )
        self._lock_sessions(_("Another user is currently updating this session."))
        if self.state not in self.CASH_MOVE_STATES:
            raise UserError(
                _(
                    "You cannot delete a cash movement after closing control has started."
                )
            )
        absl = self.env["account.bank.statement.line"].browse(absl_id)
        if absl not in self.statement_line_ids:
            raise AccessError(
                _("You cannot delete a cash move that is not linked to this session.")
            )
        action = ": ".join(
            part for part in (absl.partner_id.name, str(absl.amount)) if part
        )
        dbg.lifecycle.debug(
            "[session:%s] cash move %s removed (%s)", self.name, absl_id, action
        )
        absl.unlink()
        self.log_partner_message(partner_id, action, "CASH_IN_OUT_UNLINK")

    def log_partner_message(self, partner_id, action, message_type):
        if message_type == "ACTION_CANCELLED":
            body = _("Action cancelled (%(ACTION)s)", ACTION=action)
        elif message_type == "CASH_DRAWER_ACTION":
            body = _("Cash drawer opened (%(ACTION)s)", ACTION=action)
        elif message_type == "CASH_IN_OUT_UNLINK":
            body = _("Cash move deleted: %s", action)
        else:
            raise UserError(_("Unknown message type %(type)s.", type=message_type))

        self.message_post(body=body, author_id=partner_id)

    def _get_closed_orders(self):
        return self.order_ids.filtered(lambda o: o.state not in ["draft", "cancel"])


class StockScheduler(models.AbstractModel):
    _inherit = "stock.scheduler"

    @api.model
    def _get_tasks(self):
        return [*super()._get_tasks(), "_alert_old_pos_sessions"]

    @api.model
    def _alert_old_pos_sessions(self, use_new_cursor=False, company_id=False):
        self.env["pos.session"]._alert_old_sessions()
