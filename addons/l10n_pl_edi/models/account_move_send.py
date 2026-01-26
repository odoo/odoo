import base64
import logging

from odoo import fields, models

from odoo.addons.l10n_pl_edi.models.l10n_pl_ksef_api import KsefApiService

_logger = logging.getLogger(__name__)


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    def _get_all_extra_edis(self):
        res = super()._get_all_extra_edis()
        res.update({
            'pl_ksef': {
                'label': self.env._("by KSeF (e-Faktura)"),
                'is_applicable': lambda move: (
                        move.company_id.country_code == 'PL'
                        # Ensure you handle cases where this field might not exist yet if module is uninstalling
                        and 'l10n_pl_edi_register' in move.company_id._fields
                ),
                'help': self.env._('Send the electronic invoice to the Polish National e-Invoicing System (KSeF).'),
            }
        })
        return res

    def _get_alerts(self, moves, moves_data):
        # EXTENDS 'account'
        alerts = super()._get_alerts(moves, moves_data)
        if (
            (pl_moves := moves.filtered(lambda m: 'pl_ksef' in moves_data[m]['extra_edis'] or moves_data[m]['invoice_edi_format'] == 'fa3_pl'))
            and (it_alerts := pl_moves._check_mandatory_fields())
        ):
            alerts.update(**it_alerts)
        return alerts

    def _call_web_service_before_invoice_pdf_render(self, invoices_data):
        super()._call_web_service_before_invoice_pdf_render(invoices_data)

        invoices_for_ksef = {
            inv: data for inv, data in invoices_data.items()
            if 'pl_ksef' in data.get('extra_edis', {}) and inv.l10n_pl_ksef_status == 'to_send'
        }

        def set_error(moves, error_message):
            for move in moves:
                invoices_data[move]['error'] = {
                    'error_title': self.env._("Error when sending invoices to the KSeF"),
                    'errors': [error_message],
                }

        moves_by_company = self.env['account.move'].union(*invoices_for_ksef).grouped('company_id')
        for company, moves in moves_by_company.items():
            service = KsefApiService(company)
            try:
                service.open_ksef_session()
            except Exception as errors:  # noqa: BLE001
                set_error(moves, str(errors))
                continue
            for move in moves:
                try:
                    if move.invoice_date > fields.Date.context_today(self):
                        set_error(move, self.env._("The move was skipped because it is future-dated"))
                        continue
                    xml_content = move._l10n_pl_ksef_render_xml()
                    xml_content = xml_content.encode('utf-8')
                    response_data = service.send_invoice(xml_content)
                    l10n_pl_move_reference_number = response_data.get('referenceNumber')
                    filename = f"FA3-{move.name.replace('/', '_')}.xml"
                    self.env['ir.attachment'].create({
                        'name': filename,
                        'res_model': 'account.move',
                        'res_id': move.id,
                        'datas': base64.b64encode(xml_content),
                        'description': self.env._('KSeF Sent Invoice XML'),
                    })

                    move.write({
                        'l10n_pl_ksef_status': 'sent',
                        'l10n_pl_move_reference_number': l10n_pl_move_reference_number,
                        'l10n_pl_edi_header': self.env._('Invoice sent to KSeF. Ref: %s', l10n_pl_move_reference_number)
                    })
                    move.action_update_invoice_status()
                except Exception as errors:  # noqa: BLE001
                    set_error(move, str(errors))
