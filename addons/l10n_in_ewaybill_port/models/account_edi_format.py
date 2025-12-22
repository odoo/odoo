from odoo import _, models


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    def _check_move_configuration(self, move):
        """Add validation errors if required shipping port details are missing."""

        error_message = super()._check_move_configuration(move)
        if (
            self.code == 'in_ewaybill_1_03'
            and move.l10n_in_gst_treatment == 'overseas'
        ):
            port = move.l10n_in_ewaybill_port_partner_id
            if not port:
                error_message.append(_('- Please configure the shipping port for overseas transactions.'))
                return error_message  # Skip further checks if port is missing

            if not port.state_id:
                error_message.append(_('- Please configure the state for the shipping port.'))
            if not port.zip:
                error_message.append(_('- Please configure the PIN Code for the shipping port.'))

        return error_message

    def _l10n_in_edi_ewaybill_generate_json(self, invoices):
        """Update shipping port address into E-Way Bill JSON if applicable."""

        json_payload = super()._l10n_in_edi_ewaybill_generate_json(invoices)
        if invoices.l10n_in_ewaybill_port_partner_id:
            port = invoices.l10n_in_ewaybill_port_partner_id
            port_state = port.state_id
            port_state_code = int(port_state.l10n_in_tin) if port_state.l10n_in_tin else ''
            port_pincode = int(self._l10n_in_edi_extract_digits(port.zip)) if port.zip else ''

            if invoices.is_outbound():
                # For outbound overseas: use port address as dispatch origin
                json_payload.update({
                    'fromAddr1': port.street or '',
                    'fromAddr2': port.street2 or '',
                    'fromPlace': port.city or '',
                    'fromPincode': port_pincode,
                    'actFromStateCode': port_state_code,
                })
            else:
                # For inbound overseas: use port address as ship-to destination
                json_payload.update({
                    'toAddr1': port.street or '',
                    'toAddr2': port.street2 or '',
                    'toPlace': port.city or '',
                    'toPincode': port_pincode,
                    'actToStateCode': port_state_code,
                })

        return json_payload
