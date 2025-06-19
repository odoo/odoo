from odoo import models, api, _
from ..models.l10n_pl_ksef_api import KsefApiService
from ...sale_stock.models.res_company import company


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _get_all_extra_edis(self):
        res = super()._get_all_extra_edis()
        res.update({
            'pl_ksef': {
                'label': _("Send via KSeF (e-Faktura)"),
                'is_applicable': lambda move: (
                    move.company_id.country_code == 'PL'
                    and move.company_id.l10n_pl_edi_mode
                ),
                'help': _('Send the electronic invoice to the Polish National e-Invoicing System (KSeF).'),
            }
        })
        return res

    def _call_web_service_before_invoice_pdf_render(self, invoices_data):
        res = super()._call_web_service_before_invoice_pdf_render(invoices_data)
        invoices_for_ksef = {
            inv: data for inv, data in invoices_data.items()
            if 'pl_ksef' in data.get('extra_edis', {})
        }
        if not invoices_for_ksef:
            return res

        # all invoices_for_ksef have company in pl for each company create a KsefApiService
        # so I need a map company_id -> KsefApiService
        company_services = {}
        for move in invoices_for_ksef.keys():
            if move.company_id.id not in company_services:
                company_services[move.company_id.id] = KsefApiService(move.company_id)

        for company in company_services:
           company_services[company].open_ksef_session()


        for move, invoice_data in invoices_for_ksef.items():
            xml_content_bytes = move._l10n_pl_ksef_render_xml().encode('utf-8')
            service = company_services[move.company_id.id]
            response_data = service.send_invoice(xml_content_bytes)

            ksef_ref_number = response_data.get('referenceNumber')
            self.env['ir.attachment'].create({'name': f'ksef_{ksef_ref_number}.xml', 'res_model': 'account.move', 'res_id': move.id, 'raw': xml_content_bytes })
            move.ksef_status = 'accepted'
            move.ksef_reference_number = ksef_ref_number

        for company in company_services:
            service = company_services[company]
            service.close_ksef_session()

        return res
