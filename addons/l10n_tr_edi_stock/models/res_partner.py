from odoo import _, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_tr_edi_edispatch_customs_zip = fields.Char(
        string="Customs ZIP",
        help="The postal code of the customs office used to ship to the destination country.",
        size=5,
    )
    l10n_tr_edi_edispatch_alias = fields.Char(
        string="e-Dispatch Alias",
        copy=False,
        readonly=True,
        help="The GİB alias (mailbox) of the partner, used when sending e-Dispatches. \n"
        "It is picked among the e-Dispatch aliases the GİB lists for the partner, with the button next to it.",
    )

    def _l10n_tr_edi_verify_other_aliases(self):
        # EXTENDS 'l10n_tr_edi'
        super()._l10n_tr_edi_verify_other_aliases()
        # Only e-Invoice users can register for e-Dispatches. Without an alias, the e-Dispatch goes to the GİB.
        aliases = self._l10n_tr_edi_fetch_aliases('edispatch') if self.l10n_tr_edi_customer_status == 'einvoice' else []
        if self.l10n_tr_edi_edispatch_alias not in aliases:
            self.l10n_tr_edi_edispatch_alias = aliases[0] if aliases else False

    def action_l10n_tr_edi_select_edispatch_alias(self):
        return self._l10n_tr_edi_action_select_alias('edispatch')

    def _l10n_tr_edi_validate_partner_details(self, tax_office_required=False):
        error_messages = {}

        for record in self:
            country_code = record.country_id.code
            msg = []
            required_fields = {
                _("Street"): record.street,
                _("City"): record.city,
                _("State"): record.state_id,
                _("Country"): record.country_id,
            }

            missing_fields = [name for name, value in required_fields.items() if not value]
            if country_code == 'TR' and not record.vat:
                missing_fields.append(_("TCKN/VKN"))

            if country_code == 'TR' and not record.zip:
                missing_fields.append(_("ZIP"))

            if missing_fields:
                msg.append(_("%s is required", ', '.join(missing_fields)))

            if country_code != "TR" and (
                not record.l10n_tr_edi_edispatch_customs_zip
                or len(record.l10n_tr_edi_edispatch_customs_zip) != 5
            ):
                msg.append(_("Customs ZIP of 5 characters must be present"))

            if (
                tax_office_required
                and country_code == 'TR'
                and (tax_office_missing_msg := record._get_tax_office_missing_message())
            ):
                msg.append(tax_office_missing_msg)

            if msg:
                # Instead of using name, display_name is used, since name is not required
                # if contact is of type "Delivery Address".
                error_messages[f"invalid_partner_{record.id}"] = {
                    'message': _("%(name)s's %(errors)s.", name=record.display_name, errors=', '.join(msg)),
                    'action_text': _("View %s", record.display_name),
                    'action': record._get_records_action(name=_("View Partner")),
                    'level': 'danger',
                }
        return error_messages
