from odoo import _, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_tr_nilvera_edispatch_customs_zip = fields.Char(
        string="Customs ZIP",
        help="The postal code of the customs office used to ship to the destination country.",
        size=5,
    )

    def _l10n_tr_nilvera_validate_partner_details(self, is_delivery_partner=False):
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

            if (country_code == 'TR' or is_delivery_partner) and not record.zip:
                missing_fields.append(_("ZIP"))

            if missing_fields:
                msg.append(_("%s is required", ', '.join(missing_fields)))

            if country_code != "TR" and (
                not record.l10n_tr_nilvera_edispatch_customs_zip
                or len(record.l10n_tr_nilvera_edispatch_customs_zip) != 5
            ):
                msg.append(_("Customs ZIP of 5 characters must be present"))

            if msg:
                error_messages[f"invalid_{record.name.replace(' ', '_')}"] = {
                    'message': _("%s's %s.", record.name, ', '.join(msg)),
                    'action_text': _("View %s", record.name),
                    'action': record._get_records_action(name=_("View Partner"))
                }
        return error_messages
