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

        # Warning alert if product is missing GIBP Number
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

        # Danger alert if partner is missing required tax office
        if tr_einvoice_partners_missing_ref := moves.partner_id.filtered(
            lambda p: p.l10n_tr_nilvera_customer_status == "einvoice"
            and not p.l10n_tr_tax_office_id
        ):
            alerts["critical_partner_data_missing"] = {
                "message": _(
                    "The following TR Partner(s) missing the Tax Office Field."
                ),
                "action_text": _("View Partner(s)"),
                "action": tr_einvoice_partners_missing_ref._get_records_action(
                    name=_("Check reference on Partner(s)")
                ),
                "level": "danger",
            }

        # Danger alert if company is missing required tax office
        if tr_companies_missing_tax_office := tr_moves.filtered(
            lambda m: (not m.company_id.partner_id.l10n_tr_tax_office_id)
        ).company_id:
            alerts["tr_companies_missing_required_fields"] = {
                "message": _(
                    "The following TR Company(s) missing to the Tax Office Field."
                ),
                "action_text": _("View Company(s)"),
                "action": tr_companies_missing_tax_office._get_records_action(
                    name=_(" TR Company(s)")
                ),
                "level": "danger",
            }

        return alerts
