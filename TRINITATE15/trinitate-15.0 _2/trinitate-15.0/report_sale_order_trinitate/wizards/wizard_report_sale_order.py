# Copyright 2022, Jarsa Sistemas, S.A. de C.V.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class WizardReportSaleOorder(models.TransientModel):
    _name = "wizard.report.sale.order"
    _description = "Wizard to allow to change date to picking and related account move."

    date_from = fields.Date(string="From", required=True, default=fields.Date.context_today)
    date_to = fields.Date(string="To", required=True, default=fields.Date.context_today)
    operating_unit_ids = fields.Many2many(
        comodel_name="operating.unit",
    )
    user_id = fields.Many2one(
        "res.users",
        default=lambda self: self.env.user,
    )
    see_all_ou = fields.Boolean(
        related="user_id.see_all_ou",
    )

    @api.onchange("see_all_ou")
    def _onchange_operating_unit_id(self):
        if not self.see_all_ou:
            return {
                "domain": {
                    "operating_unit_ids": [("id", "=", self.user_id.default_operating_unit_id.id)],
                }
            }

    def open_table(self):
        self.env["report_sale_order"].search([]).unlink()
        self._cr.execute(
            """
        SELECT
            so.id AS order_id,
            sol.id AS sale_line_id,
            am.id AS account_move_id,
            aml.id AS account_move_line_id,
            so.operating_unit_id,
            (CASE
                WHEN sol.product_uom_qty <= sol.qty_invoiced
                THEN 'Total Charged' ELSE 'partial' end ) AS partial
        FROM account_move_line AS aml
        INNER JOIN account_move AS am on am.id = aml.move_id
        INNER JOIN sale_order_line_invoice_rel AS solinr on solinr.invoice_line_id = aml.id
        INNER JOIN sale_order_line AS sol on sol.id = solinr.order_line_id
        INNER JOIN sale_order AS so on so.id = sol.order_id
        WHERE
            aml.date BETWEEN %(date_from)s AND %(date_to)s AND
            so.operating_unit_id IN %(operating_unit_ids)s
            AND aml.parent_state = 'posted' AND aml.account_id = 32
        """,
            {
                "operating_unit_ids": tuple(self.operating_unit_ids.ids),
                "date_from": self.date_from,
                "date_to": self.date_to,
            },
        )
        result = self._cr.dictfetchall()
        if not result:
            raise UserError(_("No records found"))

        self.env["report_sale_order"].sudo().create(result)

        action = {
            "type": "ir.actions.act_window",
            "name": _("Report Sale "),
            "res_model": "report_sale_order",
            "view_mode": "tree",
            "context": {
                "default_search_group_by_user": 1,
            },
        }
        return action
