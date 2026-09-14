from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, formatLang

_debug = DebugLog(__name__)


class MixinOrderDocumentMatch(models.AbstractModel):
    _name = "mixin.order.document.match"
    _description = "Orders & Invoices Union"

    _order_table = ""
    _move_types = ()
    _order_reference_column = "partner_ref"

    company_id = fields.Many2one(
        comodel_name="res.company",
        readonly=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        readonly=True,
    )
    move_id = fields.Many2one(
        comodel_name="account.move",
        string="Invoice",
        readonly=True,
    )
    order_id = fields.Many2one(
        comodel_name="mixin.order",
        readonly=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        readonly=True,
    )
    date = fields.Date(readonly=True)
    amount = fields.Float(readonly=True)
    name = fields.Char(
        string="Reference",
        readonly=True,
    )
    reference = fields.Char(
        string="Source",
        readonly=True,
    )

    @api.depends("currency_id", "reference", "amount", "order_id")
    def _compute_display_name(self):
        for doc in self:
            name = doc.name or ""
            if doc.reference:
                name += " - " + doc.reference
            amount = doc.amount
            if doc.order_id and doc.order_id.invoice_state == "no":
                amount = 0.0
            name += ": " + formatLang(self.env, amount, currency_obj=doc.currency_id)
            doc.display_name = name

    @property
    def _table_query(self):
        queries = [
            self._query_moves(),
            self._query_orders(),
            *self._get_additional_queries(),
        ]

        result = queries[0]
        for query in queries[1:]:
            result = SQL("%s UNION ALL %s", result, query)

        return result

    @api.model
    def _get_additional_queries(self):
        return []

    @api.model
    def _query_moves(self):
        return SQL(
            """
            SELECT
                %s
            FROM
                %s
            WHERE
                %s
            """,
            self._select_moves(),
            self._from_moves(),
            self._where_moves(),
        )

    @api.model
    def _select_moves(self):
        return SQL(
            """
            am.id,
            am.name,
            am.ref AS reference,
            am.partner_id,
            am.date AS date,
            am.amount_untaxed AS amount,
            am.currency_id,
            am.company_id,
            am.id AS move_id,
            NULL::INTEGER AS order_id
            """,
        )

    @api.model
    def _from_moves(self):
        return SQL("account_move am")

    @api.model
    def _get_move_types(self):
        if not self._move_types:
            _debug.logic("move_types_undeclared", model=self._name)
            raise NotImplementedError(f"{self._name} must declare _move_types")
        return self._move_types

    @api.model
    def _where_moves(self):
        return SQL(
            """
            am.move_type IN %(move_types)s
            AND am.state = 'posted'
            """,
            move_types=tuple(self._get_move_types()),
        )

    @api.model
    def _query_orders(self):
        return SQL(
            """
            SELECT
                %s
            FROM
                %s
            WHERE
                %s
            """,
            self._select_orders(),
            self._from_orders(),
            self._where_orders(),
        )

    @api.model
    def _select_orders(self):
        return SQL(
            """
            -o.id AS id,
            o.name,
            o.%(reference)s AS reference,
            o.partner_id,
            o.date_order::DATE AS date,
            o.amount_untaxed AS amount,
            o.currency_id,
            o.company_id,
            NULL::INTEGER AS move_id,
            o.id AS order_id
            """,
            reference=SQL.identifier(self._order_reference_column),
        )

    @api.model
    def _get_order_table(self):
        if not self._order_table:
            _debug.logic("order_table_undeclared", model=self._name)
            raise NotImplementedError(f"{self._name} must declare _order_table")
        return self._order_table

    @api.model
    def _from_orders(self):
        return SQL("%s o", SQL.identifier(self._get_order_table()))

    @api.model
    def _where_orders(self):
        return SQL(
            """
            o.state = 'done'
            AND o.invoice_state IN ('to do', 'no', 'partial')
            """,
        )
