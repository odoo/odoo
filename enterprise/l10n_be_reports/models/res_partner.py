# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from stdnum.be import vat

from odoo import _, Command, fields, models
from odoo.exceptions import AccessError, RedirectWarning


class ResPartner(models.Model):
    _inherit = 'res.partner'

    citizen_identification = fields.Char(
        string="Citizen Identification",
        help="This code corresponds to the personal identification number for the tax authorities.")
    form_file = fields.Binary(readonly=True, help="Technical field to store all forms file.")
    forms_281_50 = fields.One2many(
        comodel_name='l10n_be.form.281.50',
        string='281.50 forms',
        inverse_name='partner_id',
        copy=False,
        help="List of 281.50 forms for this partner"
    )

    def write(self, vals):
        tag_281_50 = self.env.ref('l10n_be_reports.res_partner_tag_281_50', raise_if_not_found=False)
        if (
            tag_281_50
            and any(cmd[0] == Command.UNLINK and cmd[1] == tag_281_50.id for cmd in vals.get('category_id') or [])
            and tag_281_50 in self.category_id  # only raise when removing the tag, adding is allowed for everyone
            and not self.env.user.has_group('account.group_account_user')
        ):
            group_name = self.env.ref('account.group_account_user').name
            raise AccessError(_("Only users with the access group '%s' can unset the 281.50 category on partners.", group_name))
        return super().write(vals)

    def _formated_address(self):
        self.ensure_one()
        return f"{self.street}{(', ' + self.street2) if self.street2 else ''}"

    def _check_partner_281_50_required_values(self, check_phone_number=False):
        """ This function verifies that some fields on partners are set.
            Partner's fields:
            - Street
            - Zip
            - Citizen id or VAT number
            - Country
        """
        partner_missing_data = self._get_partner_missing_data(check_phone_number=check_phone_number)
        if partner_missing_data:
            additional_context = {'required_fields': (['phone'] if check_phone_number else [])}
            redirect_warning_message = _(
                "Some partners are not correctly configured. "
                "Please be sure that the following pieces of information are set: "
                "street, zip code, country%s and vat or citizen identification.",
                (', phone' if check_phone_number else '')
            )
            raise RedirectWarning(redirect_warning_message, partner_missing_data._open_partner_with_missing_data(), _("Open list"), additional_context)

    def _get_partner_missing_data(self, check_phone_number=False):
        partner_missing_data = self.env['res.partner']
        for partner in self:
            partner = partner.commercial_partner_id
            if not all([partner.street, partner.zip, partner.country_id, (partner.citizen_identification or partner.vat)]):
                partner_missing_data |= partner
            if check_phone_number and not partner.phone:
                partner_missing_data |= partner
        return partner_missing_data

    def _open_partner_with_missing_data(self):
        required_field_view_list = self.env.ref('l10n_be_reports.view_partner_281_50_required_fields')
        required_field_view_form = self.env.ref('l10n_be_reports.res_partner_view_form_281_50_required_field')
        return {
            'type': 'ir.actions.act_window',
            'name': _("Missing partner data"),
            'res_model': 'res.partner',
            'views': [(required_field_view_list.id, 'list'), (required_field_view_form.id, 'form')],
            'domain': [('id', 'in', self.ids)],
        }

    def _get_lang_code(self):
        return {
            'nl': '1',
            'fr': '2',
            'de': '3',
        }.get((self.lang or "")[:2], '2')

    def _get_bce_number(self):
        self.ensure_one()
        return vat.compact(self.vat or '')
