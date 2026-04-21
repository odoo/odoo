from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class EfakturDocument(models.Model):
    _inherit = "l10n_id_efaktur_coretax.document"

    document_type = fields.Selection(
        [
            ('coretax', 'Coretax'),
            ('pajakio', 'Pajak.io'),
        ],
        string="Document Type",
        default="coretax",
    )

    l10n_id_pajakio_transaction_id = fields.Char(
        string="Pajak.io Transaction ID",
        readonly=True,
        copy=False,
        help="Unique identifier of transaction to create invoice in Pajak.io",
    )
    l10n_id_pajakio_transaction_url = fields.Char(
        string="Pajak.io Document URL",
        readonly=True,
        copy=False,
        help="URL to access the receipt of DJP approval of the submitted invoice in Pajak.io",
    )
    l10n_id_pajakio_invoice_number = fields.Char(
        string="Pajak.io Invoice Number",
        readonly=True,
        copy=False,
        help="Invoice number assigned by DJP for the submitted invoices in Pajak.io",
    )
    l10n_id_pajakio_status = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("waiting", "Waiting For Approval"),
            ("approved", "Approved"),
            ('rejected', "Rejected"),
            ("cancel", "Cancelled"),
        ],
        string="Pajak.io Invoice Status",
        readonly=True,
        copy=False,
        help="Status of submitted invoices in Pajak.io",
        tracking=True,
    )
    l10n_id_pajakio_reject_reason = fields.Text(
        string="Pajak.io Rejected Reason",
        readonly=True,
        copy=False,
        help="When DJP rejects an invoice submitted via pajak.io, they will provide a reason",
    )
    l10n_id_pajakio_file = fields.Binary(
        string="Pajak.io File",
        copy=False,
        readonly=True,
        export_string_translation=False,
    )
    l10n_id_pajakio_cancel_reason = fields.Char(string="Reason for Cancellation")

    @api.constrains('document_type', 'invoice_ids')
    def _check_only_one_invoice(self):
        # Might remove in the future when Pajak.io supports batch operations
        for document in self:
            if document.document_type == 'pajakio' and len(document.invoice_ids) > 1:
                raise ValidationError(self.env._("A Pajak.io e-Faktur document can only be linked to a single invoice."))

    def _l10n_id_pajakio_prepare_line_payload(self, line):
        """ Build one 'barangJasa' entry from the raw (unrounded) e-Faktur line amounts """
        idr = self.env.ref('base.IDR')
        amounts = line._l10n_id_coretax_compute_line_amounts()
        other_tax_base = idr.round(amounts['other_tax_base'])
        return {
            "jenis": "JASA" if amounts['opt'] == "B" else "BARANG",
            "kode": amounts['code'],
            "nama": amounts['name'],
            "jumlah": amounts['qty'],
            "kodeSatuan": amounts['unit'],
            "harga": idr.round(amounts['price']),
            "totalHarga": idr.round(amounts['price'] * amounts['qty']),
            "diskon": idr.round(amounts['total_discount']),
            "tarifPpn": amounts['vat_rate'],
            "dpp": idr.round(amounts['tax_base']),
            "cekDppLain": line.move_id.l10n_id_kode_transaksi == "04",
            "dppLain": other_tax_base,
            "ppn": idr.round(other_tax_base * amounts['vat_rate'] / 100),
            "tarifPpnbm": 0,
            "ppnbm": 0,
        }

    def _prepare_invoice_payload_pajakio(self):
        """ Prepare the JSON data that will be used when sending invoice data to Pajak.io """

        self.ensure_one()
        invoice = self.invoice_ids
        if not invoice:
            raise ValidationError(self.env._("Unable to prepare e-Faktur data: no invoice linked to this document"))

        vals = {}
        invoice._l10n_id_coretax_build_invoice_vals(vals)

        document_type_mapping = {
            "TIN": "NPWP",
            "NIK": "NIK",
            "Passport": "PASPOR",
            "Other": "LAINNYA",
        }

        document = document_type_mapping.get(vals["BuyerDocument"], "NIK")
        return {
            "autoUploadDjp": True,
            "pengganti": False,
            "noInvoice": vals["RefDesc"],
            "kdJenisTransaksi": 'TD.003' + vals['TrxCode'],
            "lawanTransaksi": {
                "identityType": document,
                "identityValue": vals["BuyerDocumentNumber"] if document != "NPWP" else vals["BuyerTin"],
                "nitku": vals["BuyerIDTKU"],
                "nama": vals["BuyerName"],
                "alamatJalan": vals["BuyerAdress"],
                "kodeNegara": vals["BuyerCountry"],
            },
            "masaPajak": invoice.invoice_date.strftime("%m"),
            "tahunPajak": invoice.invoice_date.strftime("%Y"),
            "tanggalFaktur": vals["TaxInvoiceDate"],
            "barangJasa": [
                self._l10n_id_pajakio_prepare_line_payload(line) for line in invoice.invoice_line_ids
            ],
            "terminPembayaran": {
                "type": "NORMAL",
            },
            "penandatangan": {
                "nama": invoice.company_id.name,
                "npwp": invoice.company_id.vat,
                "jabatan": "Penandatangan",
                "kota": invoice.company_id.city,
                "passphrase": invoice.company_id.name,
            },
            "pembuatFaktur": {
                "npwp": invoice.company_id.vat,
                "nama": invoice.company_id.name,
            },
        }

    def _l10n_id_pajakio_send(self, json_content):
        """ Send invoice JSON payload to IAP, which will create an invoice in Pajak.io """

        self.ensure_one()
        response = self.env['iap.account'].with_company(self.company_id)._l10n_id_pajakio_iap_connect(
            {"invoice_payload": json_content},
            "/api/pajakio/1/create_invoice",
            include_account_token=True,
        )

        if 'error' in response:
            return response['error']

        data = response.get('data')
        self.l10n_id_pajakio_transaction_id = data.get('transactionId')
        return None

    def _l10n_id_pajakio_send_multi(self, payload_map):
        """ Create invoices in Pajak.io for every document in `self` (all must belong to
        the same company, mirroring `_l10n_id_pajakio_update_status`). Will use `_l10n_id_pajakio_send`
        if there is only a single document involved.
        The response will be one of the following:
        1. The API call failed:
            {'error': 'some error message'}
        2.The API call succeeded and actually returned a result
            {'data': {
                'invoice_number_1': {'transactionId': 'some_id'},
                'invoice_number_2': {'transactionId': 'some_id'},
                'invoice_number_3': {'error': 'some error message', 'transactionId': None},
            }}
        """
        if not self:
            return {}
        if len(self) == 1:
            if error := self._l10n_id_pajakio_send(payload_map[self]):
                return {self: error}
            return {}

        company = self.company_id
        response = self.env['iap.account'].with_company(company)._l10n_id_pajakio_iap_connect(
            {"invoice_payloads": [payload_map[document] for document in self]},
            "/api/pajakio/1/create_invoices",
            include_account_token=True,
        )
        # means there's some error unrelated to response from API call, so tag all invoices with same error
        if 'error' in response:
            return dict.fromkeys(self, response['error'])

        results = response.get('data', {})
        errors = {}
        for document in self:
            result = results.get(payload_map[document]['noInvoice']) or {}
            transaction_id = result.get('transactionId')
            if not transaction_id:
                errors[document] = result.get('error') or self.env._("No response received from Pajak.io for this invoice")
                continue
            document.l10n_id_pajakio_transaction_id = transaction_id
        return errors

    def _l10n_id_pajakio_update_status(self):
        """ Updating the status of invoice submission on Pajak.io platform.

        Can be called on several documents at once (they must belong to the same company),
        in which case a single IAP call fetches the status of every transaction. """

        transaction_ids = self.mapped('l10n_id_pajakio_transaction_id')
        if len(self.company_id) > 1:
            raise UserError(self.env._("All documents must belong to be the same company to be updated altogether"))

        response = self.env['iap.account'].with_company(self.company_id)._l10n_id_pajakio_iap_connect(
            {"transaction_ids": transaction_ids},
            "/api/pajakio/1/update",
        )

        if 'error' in response:
            return response['error']

        # update the status of documents based on the status response for each transaction
        trx_status_map = response.get('data') or {}
        for document in self.filtered(lambda doc: doc.l10n_id_pajakio_transaction_id):
            invoice_response = trx_status_map.get(document.l10n_id_pajakio_transaction_id) or {}
            response_status = invoice_response.get('status')

            # transactions that are absent from the response or failed to be fetched have no
            # invoice data, so handle it and move on to the next transaction
            if not invoice_response or response_status == "missing":
                document.message_post(body=self.env._("This invoice is not found in Pajak.io"))
                continue
            if response_status == "error":
                reason = invoice_response.get("error")
                document.message_post(body=self.env._("The update failed with the following response: %(reason)s", reason=reason))
                continue

            invoice_data = invoice_response.get('data') or {}

            # "canceled" invoices are not reflected on the status but instead "jenisFaktur" (invoice type)
            if invoice_data.get('jenisFaktur') == "BATAL":
                document.l10n_id_pajakio_status = "cancel"
                continue

            message = ""
            if response_status == "APPROVAL_SUKSES":
                message = self.env._("The invoice has been approved by DJP")
                document.write({
                    "l10n_id_pajakio_status": "approved",
                    "l10n_id_pajakio_invoice_number": invoice_data.get('nofa'),
                    "l10n_id_pajakio_reject_reason": False,
                    "l10n_id_pajakio_transaction_url": invoice_data.get('urlPdf'),
                })
            elif response_status in ["MENUNGGU_VERIFIKASI_DJP", "SEDANG_DIKIRIM"]:
                document.l10n_id_pajakio_status = "waiting"
            elif response_status == "DITOLAK":
                reason = invoice_data.get('alasan')
                message = self.env._("The invoice has been rejected by DJP with the following reason: %(reason)s", reason=reason)
                document.write({
                    "l10n_id_pajakio_status": "rejected",
                    "l10n_id_pajakio_reject_reason": reason,
                })
            else:
                message = self.env._("The invoice status is unknown")

            if message:
                document.message_post(body=message)
        return None

    def _cron_l10n_id_pajakio_update_waiting_status(self):
        """ Cron: refresh the DJP approval status of Pajak.io documents still 'waiting',
        batching same-company documents into a single IAP call. """
        documents = self.search([
            ('document_type', '=', 'pajakio'),
            ('l10n_id_pajakio_status', '=', 'waiting'),
            ('company_id.l10n_id_pajakio_active', '=', True),
        ])
        for company_docs in documents.grouped('company_id').values():
            company_docs._l10n_id_pajakio_update_status()

    def action_update_pajakio_status(self):
        """ User action to update the status of invoice submission on Pajak.io platform. This will call the API to get the latest status and update the invoice accordingly """
        error = self._l10n_id_pajakio_update_status()
        if error:
            raise UserError(self.env._("Pajak.io: Unable to update status with the following error: %(error)s", error=error))

    def _l10n_id_pajakio_cancel_request(self):
        """Send invoice cancellation request to Pajak.io and update the status"""
        self.ensure_one()

        if not self.l10n_id_pajakio_status == 'approved':
            raise UserError(self.env._("Only invoices that have been approved can be cancelled"))

        response = self.env['iap.account'].with_company(self.company_id)._l10n_id_pajakio_iap_connect(
            {"transaction_ids": [self.l10n_id_pajakio_transaction_id]},
            "/api/pajakio/1/cancel_invoice",
        )
        if 'error' in response:
            raise UserError(self.env._("Pajak.io: Unable to cancel invoice with the following error: %(error)s", error=response['error']))

        self.l10n_id_pajakio_status = 'cancel'

        update_error = self._l10n_id_pajakio_update_status()
        if update_error:
            self.message_post(body=self.env._("Pajak.io: Invoice cancellation is successful but status update failed with the following error: %(error)s", error=update_error))
