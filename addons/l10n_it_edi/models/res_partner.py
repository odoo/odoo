# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from stdnum.it import codicefiscale, iva

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    l10n_it_pec_email = fields.Char(string="PEC e-mail")
    l10n_it_codice_fiscale = fields.Char(string="Codice Fiscale", size=16)
    l10n_it_pa_index = fields.Char(
        string="Destination Code",
        size=7,
        help="Must contain the 6-character (or 7) code, present in the PA Index "
             "in the information relative to the electronic invoicing service, "
             "associated with the office which, within the addressee administration, deals "
             "with receiving (and processing) the invoice.",
    )

    _sql_constraints = [
        ('l10n_it_codice_fiscale',
            "CHECK(l10n_it_codice_fiscale IS NULL OR l10n_it_codice_fiscale = '' OR LENGTH(l10n_it_codice_fiscale) >= 11)",
            "Codice fiscale must have between 11 and 16 characters."),

        ('l10n_it_pa_index',
            "CHECK(l10n_it_pa_index IS NULL OR l10n_it_pa_index = '' OR LENGTH(l10n_it_pa_index) >= 6)",
            "Destination Code must have between 6 and 7 characters."),
    ]

    def _l10n_it_edi_is_public_administration(self):
        """ Returns True if the destination of the FatturaPA belongs to the Public Administration. """
        self.ensure_one()
        return self.country_id.code == 'IT' and len(self.l10n_it_pa_index or '') == 6

    def _l10n_it_edi_get_values(self):
        """ Generates all partner values needed by l10n_it_edi XML export.

            VAT number:
            If there is a VAT number and the partner is not in EU, then the exported value is 'OO99999999999'
            If there is a VAT number and the partner is in EU, then remove the country prefix
            If there is no VAT and the partner is not in Italy, then the exported value is '0000000'
            If there is no VAT and the partner is in Italy, the VAT is not set and Codice Fiscale will be relevant in the XML.
            If there is no VAT and no Codice Fiscale, the invoice is not even exported, so this case is not handled.

            Country:
            First, try and deduct the country from the VAT number.
            If not, take the country directly from the partner.
            If there's a codice fiscale, the country is 'IT'.

            PA Index:
            If the partner is in Italy, then the l10n_it_pa_index is used, and '0000000' if missing.
            If the partner is not in Italy, the default 'XXXXXXX' is used.

            Codice Fiscale:
            If the Tax Code is equal to the Italian VAT, it may mistakenly have the country prefix,
            so we try and remove it if we can

            Zip(code):
            Non-italian countries are not mapped by the Tax Agency, so it's fixed at '00000'
        """
        if not self or len(self) > 1:
            return {}

        europe = self.env.ref('base.europe', raise_if_not_found=False)
        in_eu = not europe or not self.country_id or self.country_id in europe.country_ids
        is_sm = self.country_id and self.country_id.code == "SM"

        # VAT number and country code
        normalized_vat = self.vat
        normalized_country = self.country_code
        has_vat = self.vat and not self.vat in ['/', 'NA']
        if has_vat:
            normalized_vat = self.vat.replace(' ', '')
            if in_eu:
                # If there is no country-code prefix, it's domestic to Italy
                if normalized_vat[:2].isdecimal():
                    if not normalized_country:
                        normalized_country = 'IT'
                # If the partner is from the EU, the country-code prefix of the VAT must be taken away
                else:
                    if not normalized_country:
                        normalized_country = normalized_vat[:2].upper()
                    normalized_vat = normalized_vat[2:]
            # If customer is from San Marino
            elif is_sm:
                normalized_vat = normalized_vat if normalized_vat[:2].isdecimal() else normalized_vat[2:]
            # The Tax Agency arbitrarily decided that non-EU VAT are not interesting,
            # so this default code is used instead
            # Detect the country code from the partner country instead
            else:
                normalized_vat = 'OO99999999999'

        # If it has a codice fiscale (and no country), it's an Italian partner
        if not normalized_country and self.l10n_it_codice_fiscale:
            normalized_country = 'IT'
        elif not has_vat and self.country_id and self.country_id.code != 'IT':
            normalized_vat = '0000000'

        if normalized_country == 'IT':
            pa_index = (self.l10n_it_pa_index or '0000000').upper()
            zipcode = self.zip
            state_code = self.state_id and self.state_id.code
        else:
            # San Marino is externally integrated with the SdI.
            # The country as a whole has a single fixed Destination Code.
            # https://www.agenziaentrate.gov.it/portale/documents/20143/3788702/Modifiche+ProvvedimentonSanMarino+0248717-2021.pdf/429b5571-17b9-0cce-7f62-f79cf53086d7
            pa_index = '2R4GTO8' if is_sm else 'XXXXXXX'
            zipcode = '00000'
            state_code = False

        return {
            'codice_fiscale': self._l10n_it_edi_normalized_codice_fiscale(),
            'vat': normalized_vat,
            'country_code': normalized_country,
            'state_code': state_code,
            'pa_index': pa_index,
            'zip': zipcode,
            'in_eu': in_eu,
            'is_company': self.is_company,
            'first_name': ' '.join(self.name.split()[:1]),
            'last_name': ' '.join(self.name.split()[1:]),
        }

    def _l10n_it_edi_normalized_codice_fiscale(self, l10n_it_codice_fiscale=None):
        """ Normalize the Italian Tax Code for export.
            If the Tax Code is equal to the Italian VAT, it may mistakenly have the country prefix,
            so we try and remove it if we can
        """
        if l10n_it_codice_fiscale is None:
            self.ensure_one()
            l10n_it_codice_fiscale = self.l10n_it_codice_fiscale
        if l10n_it_codice_fiscale and re.match(r'^IT[0-9]{11}$', l10n_it_codice_fiscale):
            return l10n_it_codice_fiscale[2:13]
        return l10n_it_codice_fiscale

    @api.onchange('vat', 'country_id')
    def _l10n_it_onchange_vat(self):
        if not self.l10n_it_codice_fiscale and self.vat and (self.country_id.code == "IT" or self.vat.startswith("IT")):
            self.l10n_it_codice_fiscale = self._l10n_it_edi_normalized_codice_fiscale(self.vat)
        elif self.country_id.code not in [False, "IT"]:
            self.l10n_it_codice_fiscale = False

    @api.constrains('l10n_it_codice_fiscale')
    def validate_codice_fiscale(self):
        for record in self:
            if record.l10n_it_codice_fiscale and (not codicefiscale.is_valid(record.l10n_it_codice_fiscale) and not iva.is_valid(record.l10n_it_codice_fiscale)):
                raise UserError(_("Invalid Codice Fiscale '%s': should be like 'MRTMTT91D08F205J' for physical person and '12345670546' for businesses.", record.l10n_it_codice_fiscale))

    def _l10n_it_edi_export_check(self, checks=None):
        checks = checks or ['partner_vat_codice_fiscale_missing', 'partner_address_missing']
        fields_to_check = {
            'partner_vat_missing': {
                'fields': [('vat',)],
                'message': _("Partner(s) should have a VAT number."),
            },
            'partner_vat_codice_fiscale_missing': {
                'fields': [('vat', 'l10n_it_codice_fiscale')],
                'message': _("Partner(s) should have a VAT number or Codice Fiscale."),
            },
            'partner_country_missing': {
                'fields': [('country_id',)],
                'message': _("Partner(s) should have a Country when used for simplified invoices."),
            },
            'partner_address_missing': {
                'fields': [('street', 'street2'), ('zip',), ('city',), ('country_id',)],
                'message': _("Partner(s) should have a complete address, verify their Street, City, Zipcode and Country."),
            },
        }
        selected_checks = {k: v for k, v in fields_to_check.items() if k in checks}
        single_views = [(False, 'form')]
        list_view = (self.env.ref('l10n_it_edi.res_partner_tree_l10n_it', raise_if_not_found=False))
        multi_views = [(list_view.id if list_view else False, 'list'), (False, 'form')]
        errors = {}
        for key, check in selected_checks.items():
            for fields_tuple in check['fields']:
                if invalid_records := self.filtered(lambda record: not any(record[field] for field in fields_tuple)):
                    views = single_views if len(invalid_records) == 1 else multi_views
                    errors[key] = {
                        'message': check['message'],
                        'action_text': _("View Partner(s)"),
                        'action': invalid_records._get_records_action(name=_("Check Partner(s)"), views=views),
                    }
        return errors

    def _deduce_country_code(self):
        if self.l10n_it_codice_fiscale:
            return 'IT'
        return super()._deduce_country_code()

    def _peppol_eas_endpoint_depends(self):
        # extends account_edi_ubl_cii
        return super()._peppol_eas_endpoint_depends() + ['l10n_it_codice_fiscale']
