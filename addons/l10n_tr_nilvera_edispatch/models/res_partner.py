from odoo import _, api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_tr_nilvera_edispatch_customs_zip = fields.Char(
        string="Customs ZIP",
        size=5,
        compute='_compute_l10n_tr_nilvera_edispatch_customs_zip',
        store=True,
        readonly=False
    )

    @api.depends('country_id')
    def _compute_l10n_tr_nilvera_edispatch_customs_zip(self):
        for partner in self:
            if partner.country_id and partner.country_id.code == 'TR':
                partner.l10n_tr_nilvera_edispatch_customs_zip = False

    def _l10n_tr_nilvera_validate_partner_details(self, delivery_partner_id):
        error_messages = {}

        for record in self:
            country_code = record.country_id.code
            is_delivery_partner = record == delivery_partner_id
            msg = []
            required_fields = {
                _("Street"): record.street,
                _("City"): record.city,
                _("State"): record.state_id,
                _("Country"): record.country_id,
            }

            missing_fields = [name for name, value in required_fields.items() if not value]
            if (
                country_code == "TR" or is_delivery_partner
            ) and not record.zip:
                missing_fields.append(_("ZIP"))
            if (
                country_code != "TR"
                and not record.l10n_tr_nilvera_edispatch_customs_zip
            ):
                missing_fields.append(_("Customs ZIP"))
            if country_code == 'TR' and not record.vat:
                missing_fields.append(_("TCKN/VKN"))

            if missing_fields:
                msg.append(_("%s is required", ', '.join(missing_fields)))

            if (
                (country_code == "TR" or is_delivery_partner)
                and record.zip
                and len(record.zip) != 5
            ):
                msg.append(_("ZIP must be of 5 characters"))

            if (
                country_code != "TR"
                and record.l10n_tr_nilvera_edispatch_customs_zip
                and len(record.l10n_tr_nilvera_edispatch_customs_zip) != 5
            ):
                msg.append(_("Customs ZIP must be of 5 characters"))

            if msg:
                error_messages[f"invalid_{record.name.replace(' ', '_')}"] = {
                    'message': _("%s's %s.", record.name, ', '.join(msg)),
                    'action_text': _("View %s", record.name),
                    'action': record._get_records_action(name=_("View Partner"))
                }
        return error_messages
