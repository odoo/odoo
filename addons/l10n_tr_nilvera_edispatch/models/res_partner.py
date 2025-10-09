from odoo import _, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_tr_nilvera_edispatch_customs_zip = fields.Char(
        string="Customs ZIP",
        help="The postal code of the customs office used to ship to the destination country.",
        size=5,
    )

    def _l10n_tr_nilvera_validate_partner_details(self, tax_office_required=False):
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
                not record.l10n_tr_nilvera_edispatch_customs_zip
                or len(record.l10n_tr_nilvera_edispatch_customs_zip) != 5
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

    def _get_tax_office_missing_message(self):
        """Overridden in l10n_tr_nilvera_einvoice_extended to use the tax office field instead of ref."""
        self.ensure_one()
        return _("Reference field must be set to the tax office name") if not self.ref else None

    def _get_tax_office_for_edispatch(self):
        """Overridden in l10n_tr_nilvera_einvoice_extended to return the tax office field instead of ref."""
        self.ensure_one()
        return self.ref
