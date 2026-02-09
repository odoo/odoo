import logging

from odoo import fields, models

from odoo.addons.l10n_pl_edi.tools.ksef_api_service import KsefApiService

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
                    and move.company_id.l10n_pl_edi_register
                ),
                'help': self.env._('Send the electronic invoice to the Polish National e-Invoicing System (KSeF).'),
            }
        })
        return res

    def _get_alerts(self, moves, moves_data):
        # EXTENDS 'account'
        alerts = super()._get_alerts(moves, moves_data)

        if it_alerts := moves.filtered(lambda move:
            'pl_ksef' in moves_data[move]['extra_edis']
            or moves_data[move]['invoice_edi_format'] == 'fa3_pl'
        )._l10n_pl_edi_check_mandatory_fields():
            alerts.update(**it_alerts)

        return alerts

    def _call_web_service_before_invoice_pdf_render(self, invoices_data):
        super()._call_web_service_before_invoice_pdf_render(invoices_data)

        def set_error(moves, error_message):
            for move in moves:
                invoices_data[move]['error'] = {
                    'error_title': self.env._("Error when sending invoices to the KSeF"),
                    'errors': [error_message],
                }

        def is_ksef(move):
            return 'pl_ksef' in invoices_data[move].get('extra_edis', []) and not move.l10n_pl_edi_status

        moves_by_company = self.env['account.move'].union(*invoices_data).filtered(is_ksef).grouped('company_id')
        for company, moves in moves_by_company.items():

            service = KsefApiService(company)
            try:
                service.open_ksef_session()
            except Exception as errors:  # noqa: BLE001
                set_error(moves, str(errors))
                continue

            for move in moves:

                if move.invoice_date > fields.Date.context_today(self):
                    set_error(move, self.env._("The move was skipped because it is future-dated"))
                    continue

                try:
                    self.env['res.company']._with_locked_records(move)
                    xml_content = move._l10n_pl_edi_render_xml()
                    xml_content = xml_content.encode('utf-8')
                    response_data = service.send_invoice(xml_content)
                    l10n_pl_edi_ref = response_data.get('referenceNumber')

                    move.write({
                        'l10n_pl_edi_status': 'sent',
                        'l10n_pl_edi_ref': l10n_pl_edi_ref,
                        'l10n_pl_edi_session_id': move.company_id.l10n_pl_edi_session_id,
                        'l10n_pl_edi_header': False,
                    })
                    # Will be linked in _link_invoice_documents
                    invoices_data[move]['l10n_pl_edi_attachment_file'] = xml_content

                except Exception as errors:  # noqa: BLE001
                    set_error(move, str(errors))

            if self._can_commit():
                self.env.cr.commit()

        # Check the status already
        if moves_by_company:
            self.env.ref('l10n_pl_edi.cron_auto_checks_the_polish_invoice_status')._trigger()

    def _link_invoice_documents(self, invoices_data):
        # EXTENDS 'account'
        super()._link_invoice_documents(invoices_data)

        for move, invoice_data in invoices_data.items():
            if 'l10n_pl_edi_attachment_file' in invoice_data:
                move.l10n_pl_edi_attachment_id = self.env['ir.attachment'].sudo().create({
                    'description': self.env._('KSeF Sent Invoice XML'),
                    'name': f"FA3-{move.name.replace('/', '_')}.xml",
                    'type': 'binary',
                    'mimetype': 'application/xml',
                    'raw': invoice_data['l10n_pl_edi_attachment_file'],
                    'res_id': move.id,
                    'res_model': move._name,
                    'res_field': 'l10n_pl_edi_attachment_file',
                })
                move.sudo().with_context(no_new_invoice=True).message_post(
                    body=self.env._("The KSeF XML has been attached."),
                    attachment_ids=move.l10n_pl_edi_attachment_id.ids,
                )

        self.env['account.move'].union(*invoices_data).invalidate_recordset(fnames=[
            'l10n_pl_edi_attachment_id',
            'l10n_pl_edi_attachment_file',
        ])
