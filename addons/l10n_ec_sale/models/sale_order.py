from odoo import fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    l10n_ec_sri_payment_id = fields.Many2one(
        comodel_name="l10n_ec.sri.payment",
        string="Payment Method (SRI)",
        default=lambda self: self.env["l10n_ec.sri.payment"].sudo().search([], limit=1),
        help="Ecuador: Payment Methods Defined by the SRI.",
    )

    def _prepare_invoice_vals(self):
        res = super()._prepare_invoice_vals()
        if self.country_code == "EC":
            _debug.logic(
                "sri_payment_on_invoice",
                order=self,
                method=self.l10n_ec_sri_payment_id,
            )
            res["l10n_ec_sri_payment_id"] = self.l10n_ec_sri_payment_id.id
        return res

    def _create_invoices(self, grouped=False, final=False, date=None):
        """Create invoice(s) for the given Sales Order(s).

        :param bool grouped: if True, invoices are grouped by SO id.
            If False, invoices are grouped by keys returned by :meth:`_get_invoice_grouping_keys`
        :param bool final: if True, refunds will be generated if necessary
        :param date: unused parameter
        :returns: created invoices
        :rtype: `account.move` recordset
        :raises: UserError if one of the orders has no invoiceable lines.
        """
        moves = super()._create_invoices(grouped=grouped, final=final, date=date)
        for move in moves:
            if move.transaction_ids:
                sri_payment_methods = move.transaction_ids.mapped(
                    "payment_method_id.l10n_ec_sri_payment_id"
                )
                _debug.logic(
                    "sri_payment_from_transactions",
                    move=move,
                    methods=sri_payment_methods,
                )
                if len(sri_payment_methods) == 1:
                    move.l10n_ec_sri_payment_id = sri_payment_methods
        return moves
