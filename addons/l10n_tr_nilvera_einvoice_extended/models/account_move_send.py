from odoo import _, api, models


class AccountMoveSend(models.AbstractModel):
    _inherit = "account.move.send"

    @api.model
    def _get_l10n_tr_moves(self, moves):
        return moves.filtered(lambda m: m.country_code == "TR")

    @api.model
    def _get_l10n_tr_move_non_eligible_tr_products(self, products):
        return products.filtered(
            lambda p: not p.l10n_tr_gibp_number and "TR" in p.fiscal_country_codes
        )

    # -------------------------------------------------------------------------
    # ALERTS
    # -------------------------------------------------------------------------

    def _get_alerts(self, moves, moves_data):
        # EXTENDS 'account'
        alerts = super()._get_alerts(moves, moves_data)
        tr_moves = self._get_l10n_tr_moves(moves)
        if non_eligible_tr_products := self._get_l10n_tr_move_non_eligible_tr_products(
            tr_moves.invoice_line_ids.product_id
        ):
            alerts["l10n_tr_non_eligible_products"] = {
                "message": _(
                    "The following products are missing GIBP Number:\n%(products)s\n",
                    products="\n".join(
                        f"- {product.display_name}"
                        for product in non_eligible_tr_products
                    ),
                ),
                "level": "warning",
                "action_text": _("View Product(s)"),
                "action": non_eligible_tr_products._get_records_action(
                    name=_("Check Products")
                ),
            }
        return alerts
