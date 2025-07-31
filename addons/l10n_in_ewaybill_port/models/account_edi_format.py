from odoo import _, models


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    def _check_move_configuration(self, move):
        error_message = super()._check_move_configuration(move)
        # Check if the E-Way Bill format is applicable
        # and if the shipping port code is set correctly for the move
        if (
            self.code != 'in_ewaybill_1_03'
            or move.l10n_in_mode not in ['3', '4']
            or not move.l10n_in_shipping_port_code_id
        ):
            return error_message

        shipping_port = move.l10n_in_shipping_port_code_id
        if not shipping_port.state_id:
            error_message.append(_('- Please configure the state for the shipping port.'))
        if not shipping_port.zip:
            error_message.append(_('- Please configure the PIN Code for shipping port.'))

        return error_message

    def _l10n_in_edi_ewaybill_generate_json(self, invoices):
        json_payload = super()._l10n_in_edi_ewaybill_generate_json(invoices)

        # Check if invoice has a shipping port defined and involves overseas or SEZ supply
        extract_digits = self._l10n_in_edi_extract_digits
        shipping_port = invoices.l10n_in_shipping_port_code_id

        if invoices.l10n_in_gst_treatment == 'overseas' and shipping_port:
            port_state_id = shipping_port.state_id
            port_state_code = port_state_id.l10n_in_tin and int(port_state_id.l10n_in_tin) or ''
            port_pincode = int(extract_digits(shipping_port.zip)) or ''

            if invoices.is_outbound():
                # For outbound overseas/SEZ: use port address as dispatch origin
                json_payload.update({
                    'fromAddr1': shipping_port.street or '',
                    'fromAddr2': shipping_port.street2 or '',
                    'fromPlace': shipping_port.city or '',
                    'fromPincode': port_pincode,
                    'actFromStateCode': port_state_code,
                })
            else:
                # For inbound overseas/SEZ: use port address as ship-to destination
                json_payload.update({
                    'toAddr1': shipping_port.street or '',
                    'toAddr2': shipping_port.street2 or '',
                    'toPlace': shipping_port.city or '',
                    'toPincode': port_pincode,
                    'actToStateCode': port_state_code,
                })

        return json_payload
