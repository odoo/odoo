# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # ------------------
    # Fields declaration
    # ------------------

    l10n_my_tin_validation_state = fields.Selection(
        selection=[
            ('valid', 'Valid'),
            ('invalid', 'Invalid'),
        ],
        string='Tin Validation State',
        help="Technical field, hold the result of TIN validation using MyInvois API.\n"
             "It is non blocking, and will simply help ensure that the customer of an invoice is valid to avoid submission errors.",
        compute='_compute_l10n_my_tin_validation_state',
        readonly=False,
        store=True,
        export_string_translation=False,
    )
    l10n_my_edi_display_tin_warning = fields.Boolean(
        compute='_compute_l10n_my_edi_display_tin_warning',
    )

    l10n_my_identification_type = fields.Selection(
        string="ID Type",
        selection=[
            ('NRIC', 'MyKad/MyTentera/MyPR/MyKAS'),
            ('BRN', 'Business Registration Number'),
            ('PASSPORT', 'Passport'),
            ('ARMY', 'Army'),
        ],
        default="BRN",
        help="The identification type and number used by the MyTax/MyInvois system to identify the user.\nNote: For MyPR and MyKAS to use NRIC scheme",
    )
    l10n_my_identification_number = fields.Char(string="ID Number")
    l10n_my_identification_number_placeholder = fields.Char(compute="_compute_l10n_my_identification_number_placeholder")
    l10n_my_edi_industrial_classification = fields.Many2one(
        comodel_name='l10n_my_edi.industry_classification',
        string="Ind. Classification",
        compute='_compute_l10n_my_edi_industrial_classification',
        store=True,
        readonly=False,
    )
    l10n_my_edi_malaysian_tin = fields.Char(
        string="Malaysian TIN",
        help="The value set in this field will be used as TIN for the customer/supplier.\n"
             "If left empty, the TIN field will be used.",
    )

    # --------------------------------
    # Compute, inverse, search methods
    # --------------------------------

    @api.depends('l10n_my_identification_type', 'l10n_my_identification_number', 'vat', 'l10n_my_edi_malaysian_tin')
    def _compute_l10n_my_tin_validation_state(self):
        """ The three @depends are used for the validation. If they change, we will invalidate it and expect the user to revalidate. """
        self.l10n_my_tin_validation_state = False

    @api.depends_context('company', 'l10n_my_identification_number')
    def _compute_l10n_my_edi_display_tin_warning(self):
        """ We want to display the tin warning for companies registered to use MyInvois. """
        # We need to sudo here, as all users having access to partners may not have the rights to access the proxy users.
        proxy_user = self.env.company.sudo().l10n_my_edi_proxy_user_id
        is_edi_used = proxy_user and proxy_user.proxy_type == 'l10n_my_edi'
        for partner in self:
            # Users with no business number can't be validated using the api
            partner.l10n_my_edi_display_tin_warning = is_edi_used and partner.l10n_my_identification_number

    @api.depends('l10n_my_identification_type')
    def _compute_l10n_my_identification_number_placeholder(self):
        """ Computes a dynamic placeholder that depends on the selected type to help the user inputs their data.
        The placeholders have been taken from the MyInvois doc.
        """
        for partner in self:
            placeholder = 'N/A'
            if partner.l10n_my_identification_type == 'NRIC':
                placeholder = '830503114923'
            elif partner.l10n_my_identification_type == 'BRN':
                placeholder = '202201234565'
            elif partner.l10n_my_identification_type == 'PASSPORT':
                placeholder = 'A00000000'
            elif partner.l10n_my_identification_type == 'ARMY':
                placeholder = '830805134983'
            partner.l10n_my_identification_number_placeholder = placeholder

    def _compute_l10n_my_edi_industrial_classification(self):
        default_classification = self.env.ref('l10n_my_edi.class_00000', raise_if_not_found=False)
        self.filtered(lambda p: not p.l10n_my_edi_industrial_classification).l10n_my_edi_industrial_classification = default_classification

    # --------------
    # Action methods
    # --------------

    def action_verify_tin(self):
        """ Search for a missing TIN, otherwise validate the existing TIN. """
        self.ensure_one()

        # In case of foreign partners, we need to search for a Malaysian TIN, even if the VAT field is filled, cause that can be foreign VAT.
        is_foreign_partner_without_tin = self.country_code and self.country_code != 'MY' and self.vat and not self.l10n_my_edi_malaysian_tin
        if not self._l10n_my_edi_get_tin_for_myinvois() or is_foreign_partner_without_tin:
            return self._search_tin()

        # If a TIN is already set, we will validate it against the identification information.
        return self._validate_tin()

    def _validate_tin(self):
        """ Validate the existing TIN against the provided identification information. """
        self.ensure_one()
        if not self._l10n_my_edi_get_tin_for_myinvois() or not self.l10n_my_identification_type or not self.l10n_my_identification_number:
            raise UserError(self.env._('In order to validate the TIN, you must provide the Identification type and number.'))

        # Sudo to allow a user without access to the proxy user to validate the ID if needed.
        proxy_user = self.env.company.sudo().l10n_my_edi_proxy_user_id
        if not proxy_user:
            raise UserError(self.env._("Please register for the E-Invoicing service in the settings first."))

        response = proxy_user._l10n_my_edi_contact_proxy('api/l10n_my_edi/1/validate_tin', params={
            'identification_values': {
                'tin': self._l10n_my_edi_get_tin_for_myinvois(),
                'id_type': self.l10n_my_identification_type,
                'id_val': self.l10n_my_identification_number,
            },
        })

        if 'error' in response:
            ref = response['error']['reference']
            # No need to rollback, we don't want to be blocking on that.
            if ref == 'document_tin_not_found':
                self._message_log(body=self.env._('The identification number provided does not match the TIN in Myinvois.\
                    \nThis may happen when using generic TIN and will not prevent you from invoicing. Searching for the right TIN using the identification information.'))
                self.l10n_my_tin_validation_state = 'invalid'
                # In case TIN validation fails, we can search for the right TIN using the identification information, as the user may have changed an original TIN.
                self._search_tin()
            else:
                self._message_log(body=self.env._('An unexpected error occurred while validating the TIN. Please try again later.'))
        else:
            if response.get('success'):
                self.l10n_my_tin_validation_state = 'valid'
            else:
                self._message_log(body=self.env._('MyInvois was not able to match the TIN with the provided identification number.\
                    \nSearching for the right TIN using the identification information.'))
                self.l10n_my_tin_validation_state = 'invalid'
                # In case TIN validation fails, we can search for the right TIN using the identification information, as the user may have changed an original TIN.
                self._search_tin()

    def _search_tin(self):
        """ Fetch and store the TIN for the provided identification. """
        self.ensure_one()
        if not self.l10n_my_identification_type or not self.l10n_my_identification_number:
            raise UserError(self.env._('In order to search for the TIN, you must provide the ID Number and Type.'))

        # Sudo to allow a user without access to the proxy user to search the TIN if needed.
        proxy_user = self.env.company.sudo().l10n_my_edi_proxy_user_id
        if not proxy_user:
            raise UserError(self.env._("Please register for the E-Invoicing service in the settings first."))

        response = proxy_user._l10n_my_edi_contact_proxy('api/l10n_my_edi/1/search_tin', params={
            'identification_values': {
                'id_type': self.l10n_my_identification_type,
                'id_val': self.l10n_my_identification_number,
            },
        })

        if response.get('success') and response.get('tin'):
            fetched_tin = response['tin']
            if self.country_code and self.country_code != 'MY':
                # For foreign partners, always set the Malaysian TIN field instead of the `vat` field to avoid issues with standard VAT validation.
                self.l10n_my_edi_malaysian_tin = fetched_tin
                self._message_log(body=self.env._("TIN search successful! Found TIN: %s set to Malaysian TIN", fetched_tin))
            else:
                # For Malaysian partners or partners without a country, set the TIN to the `vat` so it appears on invoices.
                self.vat = fetched_tin
                self._message_log(body=self.env._("TIN search successful! Found TIN: %s set to TIN", fetched_tin))
            self.l10n_my_tin_validation_state = 'valid'
        # TODO: With the help of local server setup with myinvois need to check for proper error handling.
        # As of now for wrong identification information, the IAP does not return `document_not_found` reference which is wrong.
        elif 'error' in response:
            # No need to rollback, we don't want to be blocking on that.
            ref = response['error']['reference']
            if ref == 'multiple_tin_found':
                self._message_log(body=self.env._("For the given ID Number and ID Type, multiple TINs were found.\nPlease check the identification information."))
            elif ref == 'invalid_search_parameters':  # This should not happen, as we check for the parameters before calling the API.
                self._message_log(body=self.env._("Either ID Number or ID Type is missing.\nPlease check the identification information."))
            elif ref == 'tin_not_found':
                self._message_log(body=self.env._("No TIN found for the ID Number and ID Type.\nPlease check the identification information."))
            else:
                self._message_log(body=self.env._("An unexpected error occurred while searching for the TIN.\nPlease try again later. Error: %s, and Reference: %s", response['error'].get('message', ''), ref))
        else:
            self._message_log(body=self.env._("TIN search did not return a valid result."))

    def _l10n_my_edi_get_tin_for_myinvois(self):
        """ Helper to return the VAT number relevant to the situation. """
        self.ensure_one()
        # When l10n_my_edi_malaysian_tin is set, it will be used instead of the VAT.
        # A user may want to keep the correct VAT on a foreign contact while also use myinvois with a malaysia TIN/Generic TIN
        # Using the Tax ID field also causes issue with standard vat validation, which block setting foreign VAT numbers.
        return self.l10n_my_edi_malaysian_tin or self.vat

    def _l10n_my_get_registration_number(self):
        registration_number = super()._l10n_my_get_registration_number()
        if not registration_number and self.l10n_my_identification_type == 'BRN':
            return self.l10n_my_identification_number
        return registration_number

    @api.model
    def _commercial_fields(self):
        return super()._commercial_fields() + ['l10n_my_identification_type', 'l10n_my_identification_number', 'l10n_my_edi_industrial_classification', 'l10n_my_edi_malaysian_tin']

    def _get_frontend_writable_fields(self):
        frontend_writable_fields = super()._get_frontend_writable_fields()
        frontend_writable_fields.update({'l10n_my_identification_type', 'l10n_my_identification_number', 'l10n_my_edi_industrial_classification'})

        return frontend_writable_fields
