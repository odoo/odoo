import re
import unicodedata

from reportlab.graphics.barcode.qrencoder import QRECI, QR8bitByte

from odoo import api, models
from odoo.tools.barcode import createBarcodeDrawing
from odoo.tools.image import image_data_uri

from odoo.addons.account.tools import (
    is_valid_structured_reference_iso,
    is_valid_structured_reference_si,
    sanitize_structured_reference,
)


# https://www.zbs-giz.si/wp-content/uploads/2021/10/EN_Tehnicni_standard_UPN_QR.pdf
UPN_QR_ENCODING = 'iso-8859-2'
UPN_QR_ECI = 4
UPN_QR_VERSION = 15
UPN_QR_BORDER = 4  # White margin, in modules, around the code
UPN_QR_SIZE = 850  # In pixels: 77 modules + the margin, at 10 pixels per module (600 DPI once printed)

UPN_QR_MAX_TEXT = 33  # Names, streets and cities
UPN_QR_MAX_PURPOSE = 42
UPN_QR_MAX_AMOUNT = 999_999_999.99
UPN_QR_NO_REFERENCE = 'SI99'

# Common characters outside ISO 8859-2, replaced by the closest text it can hold.
UPN_QR_CHARACTER_REPLACEMENTS = str.maketrans({
    '€': 'EUR',
    '‐': '-', '‑': '-', '‒': '-', '–': '-', '—': '-', '―': '-',
    '‘': "'", '’': "'", '‚': "'", '‛': "'",
    '“': '"', '”': '"', '„': '"', '‟': '"',
    '…': '...',
})


def _upn_qr_clean_text(text, max_length=UPN_QR_MAX_TEXT):
    """ Make a text fit a UPN QR field: one line, ISO 8859-2 characters only,
    cut to the maximum length, without leading or trailing spaces.
    """
    text = ' '.join((text or '').split()).translate(UPN_QR_CHARACTER_REPLACEMENTS)
    return ''.join(map(_upn_qr_clean_character, text))[:max_length].strip()


def _upn_qr_clean_character(character):
    try:
        character.encode(UPN_QR_ENCODING)
        return character
    except UnicodeEncodeError:
        # Drop the accent when the base letter exists (å -> a), else give up.
        return unicodedata.normalize('NFKD', character).encode('ascii', 'ignore').decode() or '?'


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    def _l10n_si_get_upn_qr_reference(self, structured_communication):
        """ The recipient's reference written in the UPN QR code: the payment reference
        without spaces when it is a valid SI01 or RF reference, else the SI99 model
        that stands for "no reference".
        """
        reference = sanitize_structured_reference(structured_communication or '').upper()
        is_valid_si = is_valid_structured_reference_si(reference) and len(reference) <= 26
        is_valid_rf = re.fullmatch(r'RF\d{2}[0-9A-Z]{1,21}', reference) and is_valid_structured_reference_iso(reference)
        if is_valid_si or is_valid_rf:
            return reference
        return UPN_QR_NO_REFERENCE

    def _l10n_si_get_upn_qr_name_and_address(self, name, partner):
        """ The name, street and city lines of a payer or recipient. Missing data
        gives empty lines: the code is still generated (deliberate deviation from
        the standard, which requires the payer's address).
        """
        return [
            _upn_qr_clean_text(name),
            _upn_qr_clean_text(' '.join(filter(None, [partner.street, partner.street2]))),
            _upn_qr_clean_text(' '.join(filter(None, [partner.zip, partner.city]))),
        ]

    def _get_qr_vals(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        # EXTENDS account
        if qr_method == 'si_upn_qr':
            context = self.env.context
            payment_deadline = context.get('l10n_si_upn_qr_payment_deadline')
            reference = self._l10n_si_get_upn_qr_reference(structured_communication)
            # A free-text reference can't go in the reference field: it becomes the payment purpose.
            purpose = (reference != UPN_QR_NO_REFERENCE and context.get('l10n_si_upn_qr_payment_purpose')) or free_communication

            fields_1_to_19 = [
                'UPNQR',                                                            # 1. Leading style
                '',                                                                 # 2. Payer's IBAN
                '',                                                                 # 3. Deposit
                '',                                                                 # 4. Withdrawal
                '',                                                                 # 5. Payer's reference
                *self._l10n_si_get_upn_qr_name_and_address(                         # 6-8. Payer's name, street, city
                    debtor_partner.commercial_partner_id.name, debtor_partner,
                ),
                f'{round(currency.round(amount) * 100):011d}',                      # 9. Amount, in cents
                '',                                                                 # 10. Payment date
                '',                                                                 # 11. Urgent
                context.get('l10n_si_upn_qr_purpose_code') or 'GDSV',               # 12. Purpose code
                _upn_qr_clean_text(purpose, UPN_QR_MAX_PURPOSE),                    # 13. Payment purpose
                payment_deadline.strftime('%d.%m.%Y') if payment_deadline else '',  # 14. Payment deadline
                self.sanitized_account_number,                                      # 15. Recipient's IBAN
                reference,                                                          # 16. Recipient's reference
                *self._l10n_si_get_upn_qr_name_and_address(                         # 17-19. Recipient's name, street, city
                    self.holder_name or self.partner_id.name, self.partner_id,
                ),
            ]
            # 20. Length of fields 1 to 19, line feeds included.
            # Every character takes one byte, as the fields only hold ISO 8859-2
            # characters so the number of characters is equal to the number of bytes.
            checksum = f'{sum(len(field) + 1 for field in fields_1_to_19):03d}'
            return [*fields_1_to_19, checksum]
        return super()._get_qr_vals(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)

    def _get_qr_code_generation_params(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        # EXTENDS account
        if qr_method == 'si_upn_qr':
            vals = self._get_qr_vals(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)
            # The image is drawn by _l10n_si_render_upn_qr, not by the generic barcode report.
            return {
                'barcode_type': 'QR',
                # Every field ends with a line feed, the checksum included.
                'value': ''.join(f'{field}\n' for field in vals),
            }
        return super()._get_qr_code_generation_params(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)

    def _get_qr_code_base64(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        # EXTENDS account
        if qr_method == 'si_upn_qr':
            params = self._get_qr_code_generation_params(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)
            return self._l10n_si_render_upn_qr(params['value'])
        return super()._get_qr_code_base64(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)

    def _l10n_si_render_upn_qr(self, content):
        """ Draw the UPN QR code. The generic barcode report can't declare the
        ISO 8859-2 character set (ECI 4) nor force the version, both required here.

        :return: the PNG image, as a data URI
        """
        barcode = createBarcodeDrawing(
            'QR',
            value=[QRECI(UPN_QR_ECI), QR8bitByte(content.encode(UPN_QR_ENCODING))],
            qrVersion=UPN_QR_VERSION,
            barLevel='M',
            barBorder=UPN_QR_BORDER,
            width=UPN_QR_SIZE,
            height=UPN_QR_SIZE,
        )
        return image_data_uri(barcode.asString('png'))

    def _get_error_messages_for_qr(self, qr_method, debtor_partner, currency):
        # EXTENDS account
        if qr_method == 'si_upn_qr':
            error_messages = []
            if currency.name != 'EUR':
                error_messages.append(self.env._("The currency must be EUR to generate a UPN QR code."))
            if not debtor_partner or debtor_partner.country_code != 'SI':
                error_messages.append(self.env._("The customer must be located in Slovenia to generate a UPN QR code."))
            if self.account_type != 'iban' or not (self.sanitized_account_number or '').startswith('SI'):
                error_messages.append(self.env._("The bank account must be a Slovenian IBAN to generate a UPN QR code."))
            return '\r\n'.join(error_messages) or None
        return super()._get_error_messages_for_qr(qr_method, debtor_partner, currency)

    def _check_for_qr_code_errors(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        # EXTENDS account
        if qr_method == 'si_upn_qr':
            if not self.holder_name and not self.partner_id.name:
                return self.env._("The account receiving the payment must have an account holder name or partner name set.")
            if amount > UPN_QR_MAX_AMOUNT:
                return self.env._("A UPN QR code can't hold an amount of one billion or more.")
        return super()._check_for_qr_code_errors(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)

    @api.model
    def _get_available_qr_methods(self):
        # EXTENDS account
        rslt = super()._get_available_qr_methods()
        # Slovenian banking applications are made for UPN QR, so it comes before
        # the SEPA QR code for the payments it applies to.
        rslt.append(('si_upn_qr', self.env._("UPN QR"), 15))
        return rslt
