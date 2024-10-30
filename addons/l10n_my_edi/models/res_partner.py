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
    l10n_my_identification_number_placeholder = fields.Char(compute="_compute_l10n_my_identification_number_placeholder")

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
        proxy_user = self.env.company.l10n_my_edi_proxy_user_id
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
                placeholder = '830503-11-4923'
            elif partner.l10n_my_identification_type == 'BRN':
                placeholder = '202201234565'
            elif partner.l10n_my_identification_type == 'PASSPORT':
                placeholder = 'A00000000'
            elif partner.l10n_my_identification_type == 'ARMY':
                placeholder = '830805-13-4983'
            partner.l10n_my_identification_number_placeholder = placeholder

    # --------------
    # Action methods
    # --------------

    def action_validate_tin(self):
        """ Calling this action will reach our EDI proxy in order to validate the TIN against the provided identification information. """
        self.ensure_one()
        if not self.vat or not self.l10n_my_identification_type or not self.l10n_my_identification_number:
            raise UserError(_('In order to validate the TIN, you must provide the Identification type and number.'))

        proxy_user = self.env.company.l10n_my_edi_proxy_user_id
        if not proxy_user:
            raise UserError(_("Please register for the E-Invoicing service in the settings first."))

        response = proxy_user._l10n_my_edi_contact_proxy('api/l10n_my_edi/1/validate_tin', params={
            'identification_values': {
                'tin': self.vat,
                'id_type': self.l10n_my_identification_type,
                'id_val': self.l10n_my_identification_number,
            }
        })

        if 'error' in response:
            ref = response['error']['reference']
            # No need to rollback, we don't want to be blocking on that.
            if ref == 'document_tin_not_found':
                self._message_log(body=_('MyInvois was not able to match the TIN with the provided identification number.'))
                self.l10n_my_tin_validation_state = 'invalid'
            else:
                self._message_log(body=_('An unexpected error occurred while validating the TIN. Please try again later.'))
        else:
            self.l10n_my_tin_validation_state = 'valid' if response.get('success') else 'invalid'
