from odoo import _, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_tr_nilvera_edespatch_customs_zip = fields.Char("Customs ZIP", size=5)
    company_country_code = fields.Char(compute='_compute_company_country_code')

    def _compute_company_country_code(self):
        self.company_country_code = self.env.company.country_code

    def _l10n_tr_nilvera_validate_partner_details(self, delivery_partner_id):
        error_messages = {}
        for record in self:
            required_fields = {
                _("Street"): record.street,
                _("City"): record.city,
                _("State"): record.state_id,
                _("ZIP"): record.zip,
                _("Country"): record.country_id,
            }
            missing_fields = [name for name, value in required_fields.items() if not value]
            if (
                record.country_id.code != "TR"
                and record.id == delivery_partner_id
                and not record.l10n_tr_nilvera_edespatch_customs_zip
            ):
                missing_fields.append(_("Customs ZIP"))
            if record.country_id.code == 'TR' and not record.vat:
                missing_fields.append(_("TCKN/VKN"))
            msg = []
            if missing_fields:
                msg.append(_("%s is required", ', '.join(missing_fields)))
            if record.zip and len(record.zip) != 5:
                msg.append(_("ZIP must be of 5 characters."))
            if msg:
                error_messages[f"invalid_{record.name.replace(' ', '_')}"] = {
                    'message': _("%s's %s", record.name, ', '.join(msg)),
                    'action_text': _("View %s", record.name),
                    'action': record._get_records_action(name=_("View Partner"))
                }
        return error_messages
