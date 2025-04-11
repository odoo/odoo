import re

from odoo import _, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # E-Invoice Validation
    def _l10n_in_edi_strict_error_validation(self):
        """
        This method is used to check the strict validation of the partner data
        as per government API json schema (https://einv-apisandbox.nic.in/version1.03/generate-irn.html#requestSampleJSON)
        In case of any error, it will return the error message
        Note - We stimulate as error message from API, so that user can understand the error
        Also restrict unwanted request to government servers and avoid getting black listed
        """
        message = []
        if not re.match("^.{3,100}$", self.street or ""):
            message.append(_("- Street required min 3 and max 100 characters"))
        if not re.match("^.{3,100}$", self.city or ""):
            message.append(_("- City required min 3 and max 100 characters"))
        if self.country_id.code == "IN" and not re.match("^.{3,50}$", self.state_id.name or ""):
            message.append(_("- State required min 3 and max 50 characters"))
        if self.country_id.code == "IN" and not re.match("^([1-9][0-9]{5})$", self.zip or ""):
            message.append(_("- ZIP code required 6 digits ranging from 100000 to 999999"))
        if message:
            message.insert(0, self.display_name)
        return message

    def _l10n_in_check_einvoice_validation(self):
        checks = {
            'partner_address_missing': {
                'message': _(
                    "Partners should have a complete address, verify their Street, City, State, "
                    "Country and Zip code."
                ),
                'validation': lambda record: any(
                    not record[field] for field in (
                        'street', 'zip', 'city', 'state_id', 'country_id',
                    )
                ),
            },
            'partner_email_check': {
                'message': _(
                    "Email won’t be sent to e-invoice: invalid or longer than 100 characters."
                ),
                'validation': lambda record: (
                    record.email and (
                        not re.match(
                            r"^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$", record.email
                        ) or not re.match(r"^.{6,100}$", record.email)
                    )
                ),
            },
            'partner_phone_check': {
                'message': _(
                    "Phone number won’t be sent to e-invoice: must be 10–12 digits."
                ),
                'validation': lambda record: (
                    record.phone and not re.match(
                        r"^[0-9]{10,12}$",
                        self.env['account.move']._l10n_in_extract_digits(record.phone)
                    )
                ),
            },
            'partner_street2_check': {
                'message': _(
                    "Street2 won’t be sent to e-invoice: must be 3–100 characters."
                ),
                'validation': lambda record: (
                    record.street2 and not re.match(r"^.{3,100}$", record.street2)
                ),
            },
        }
        return {
            f"l10n_in_edi_{key}": {
                'message': check['message'],
                'action_text': (
                    _("View Partners") if len(invalid_records) > 1
                    else _("View %s", invalid_records.name)
                ),
                'action': invalid_records._get_records_action(name=_("Check Partner Data")),
            }
            for key, check in checks.items()
            if (invalid_records := self.filtered(check['validation']))
        }
