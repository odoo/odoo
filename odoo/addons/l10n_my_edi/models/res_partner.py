# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
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

    # --------------------------------
    # Compute, inverse, search methods
    # --------------------------------

    @api.depends('l10n_my_identification_type', 'l10n_my_identification_number', 'vat')
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

    # --------------
    # Action methods
    # --------------

    def action_validate_tin(self):
        """ Calling this action will reach our EDI proxy in order to validate the TIN against the provided identification information. """
        self.ensure_one()
        if not self._l10n_my_edi_get_tin_for_myinvois() or not self.l10n_my_identification_type or not self.l10n_my_identification_number:
            raise UserError(_('In order to validate the TIN, you must provide the Identification type and number.'))

        # Sudo to allow a user without access to the proxy user to validate the ID if needed.
        proxy_user = self.env.company.sudo().l10n_my_edi_proxy_user_id
        if not proxy_user:
            raise UserError(_("Please register for the E-Invoicing service in the settings first."))

        response = proxy_user._l10n_my_edi_contact_proxy('api/l10n_my_edi/1/validate_tin', params={
            'identification_values': {
                'tin': self._l10n_my_edi_get_tin_for_myinvois(),
                'id_type': self.l10n_my_identification_type,
                'id_val': self.l10n_my_identification_number,
            }
        })

        if 'error' in response:
            ref = response['error']['reference']
            # No need to rollback, we don't want to be blocking on that.
            if ref == 'document_tin_not_found':
                self._message_log(body=_('MyInvois was not able to match the TIN with the provided identification number.\nThis may happen when using generic TIN and will not prevent you from invoicing.'))
                self.l10n_my_tin_validation_state = 'invalid'
            else:
                self._message_log(body=_('An unexpected error occurred while validating the TIN. Please try again later.'))
        else:
            self.l10n_my_tin_validation_state = 'valid' if response.get('success') else 'invalid'

    def _l10n_my_edi_get_tin_for_myinvois(self):
        """ Helper to return the VAT number relevant to the situation. """
        self.ensure_one()
        return self.vat

    @api.model
    def _commercial_fields(self):
        return super()._commercial_fields() + ['l10n_my_identification_type', 'l10n_my_identification_number']
