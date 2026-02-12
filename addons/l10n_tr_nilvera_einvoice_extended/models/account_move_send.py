from odoo import _, models


class AccountMoveSend(models.AbstractModel):
    _inherit = "account.move.send"

    # -------------------------------------------------------------------------
    # ALERTS
    # -------------------------------------------------------------------------

    def _get_alerts(self, moves, moves_data):
        # EXTENDS 'account'
        alerts = super()._get_alerts(moves, moves_data)
        export_nilvera_moves = moves.filtered(lambda m: m.country_code == "TR" and m.l10n_tr_is_export_invoice and 'tr_nilvera' in moves_data[m]['extra_edis'])

        # Warning alert if a line has no product and is missing CTSP Number
        if non_eligible_tr_lines := export_nilvera_moves.invoice_line_ids.filtered(
            lambda line: not (line.product_id or line.l10n_tr_ctsp_number),
        ):
            alerts["l10n_tr_non_eligible_products"] = {
                "message": _(
                    "The following products are missing a CTSP Number:\n%(products)s\n",
                    products="\n".join(f"- {line.display_name}" for line in non_eligible_tr_lines),
                ),
                "level": "warning",
                "action_text": _("View Product(s)"),
                "action": non_eligible_tr_lines._get_records_action(
                    name=_("Check Products"),
                ),
            }
        return alerts

    def _get_l10n_tr_tax_partner_tax_office_alert(self, moves):
        # OVERRIDES l10n_tr_nilvera_einvoice.
        if tr_einvoice_partners_missing_ref := moves.partner_id.filtered(
            lambda p: p.l10n_tr_nilvera_customer_status == "einvoice" and not p.l10n_tr_tax_office_id,
        ):
            return {
                "message": _("The Tax Office is not set on the following TR Partner(s)."),
                "action_text": _("View Partner(s)"),
                "action": tr_einvoice_partners_missing_ref._get_records_action(
                    name=_("Check reference on Partner(s)"),
                ),
                "level": "danger",
            }
        return {}

    def _get_l10n_tr_tax_company_tax_office_alert(self, moves):
        # OVERRIDES l10n_tr_nilvera_einvoice.
        if tr_companies_missing_tax_office := moves.company_id.filtered(
            lambda c: (not c.l10n_tr_tax_office_id and c.country_code == "TR"),
        ):
            return {
                "message": _("The Tax Office is not set on the following TR Company(s)."),
                "action_text": _("View Company(s)"),
                "action": tr_companies_missing_tax_office._get_records_action(
                    name=_(" TR Company(s)"),
                ),
                "level": "danger",
            }
        return {}

    def _get_l10n_tr_tax_partner_address_alert(self, moves):
        # EXTENDS l10n_tr_nilvera_einvoice.
        return super()._get_l10n_tr_tax_partner_address_alert(moves.filtered(lambda move: not move.l10n_tr_is_export_invoice))
