# Copyright 2014-2018 Tecnativa - Pedro M. Baeza
# Copyright 2020 Tecnativa - Manuel Calero
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from psycopg2.extensions import AsIs

from odoo import api, fields, models, tools


class InvoiceCommissionAnalysisReport(models.Model):
    _name = "invoice.commission.analysis.report"
    _description = "Invoice Commission Analysis Report"
    _auto = False
    _rec_name = "commission_id"

    @api.model
    def _get_selection_invoice_state(self):
        return self.env["account.move"].fields_get(allfields=["state"])["state"][
            "selection"
        ]

    invoice_state = fields.Selection(
        selection="_get_selection_invoice_state", string="Invoice Status", readonly=True
    )
    date_invoice = fields.Date("Invoice Date", readonly=True)
    company_id = fields.Many2one("res.company", "Company", readonly=True)
    partner_id = fields.Many2one("res.partner", "Partner", readonly=True)
    agent_id = fields.Many2one("res.partner", "Agent", readonly=True)
    categ_id = fields.Many2one("product.category", "Category of Product", readonly=True)
    product_id = fields.Many2one("product.product", "Product", readonly=True)
    uom_id = fields.Many2one("uom.uom", "Unit of Measure", readonly=True)
    quantity = fields.Float("# of Qty", readonly=True)
    price_unit = fields.Float("Unit Price", readonly=True)
    price_subtotal = fields.Float("Subtotal", readonly=True)
    balance = fields.Float(
        readonly=True,
    )
    percentage = fields.Integer("Percentage of commission", readonly=True)
    amount = fields.Float(readonly=True)
    invoice_line_id = fields.Many2one("account.move.line", readonly=True)
    settled = fields.Boolean(readonly=True)
    commission_id = fields.Many2one("commission", "Commission", readonly=True)

    def _select(self):
        select_str = """
            SELECT MIN(aila.id) AS id,
            ai.partner_id AS partner_id,
            ai.state AS invoice_state,
            ai.date AS date_invoice,
            ail.company_id AS company_id,
            rp.id AS agent_id,
            pt.categ_id AS categ_id,
            ail.product_id AS product_id,
            pt.uom_id AS uom_id,
            SUM(ail.quantity) AS quantity,
            AVG(ail.price_unit) AS price_unit,
            SUM(ail.price_subtotal) AS price_subtotal,
            SUM(ail.balance) AS balance,
            AVG(c.fix_qty) AS percentage,
            SUM(aila.amount) AS amount,
            ail.id AS invoice_line_id,
            aila.settled AS settled,
            aila.commission_id AS commission_id
        """
        return select_str

    def _from(self):
        from_str = """
            account_invoice_line_agent aila
            LEFT JOIN account_move_line ail ON ail.id = aila.object_id
            INNER JOIN account_move ai ON ai.id = ail.move_id
            LEFT JOIN commission c ON c.id = aila.commission_id
            LEFT JOIN product_product pp ON pp.id = ail.product_id
            INNER JOIN product_template pt ON pp.product_tmpl_id = pt.id
            LEFT JOIN res_partner rp ON aila.agent_id = rp.id
        """
        return from_str

    def _group_by(self):
        group_by_str = """
            GROUP BY ai.partner_id,
            ai.state,
            ai.date,
            ail.company_id,
            rp.id,
            pt.categ_id,
            ail.product_id,
            pt.uom_id,
            ail.id,
            aila.settled,
            aila.commission_id
        """
        return group_by_str

    @api.model
    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute(
            "CREATE or REPLACE VIEW %s AS ( %s FROM ( %s ) %s )",
            (
                AsIs(self._table),
                AsIs(self._select()),
                AsIs(self._from()),
                AsIs(self._group_by()),
            ),
        )
