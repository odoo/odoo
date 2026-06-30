from shutil import move

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_id_pajakio_transaction_id = fields.Char(
        string="Pajak.io Transaction ID",
        readonly=True,
        copy=False,
        help="Unique identifier of transaction to create invoice in Pajak.io"
    )
    l10n_id_pajakio_transaction_url = fields.Char(
        string="Pajak.io Document URL",
        copy=False,
        help="URL to access the receipt of DJP approval of the submitted invoice in Pajak.io"
    )
    l10n_id_pajakio_invoice_number = fields.Char(
        string="Pajak.io Invoice Number",
        readonly=True,
        copy=False,
        help="Invoice number assigned by DJP for the submitted invoices in Pajak.io"
    )
    l10n_id_pajakio_status = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("waiting", "Waiting For Approval"),
            ("approved", "Approved"),
            ('rejected', "Rejected"),
            ("cancel", "Cancelled")
        ],
        string="Pajak.io Invoice Status",
        readonly=True,
        copy=False,
        help="Status of submitted invoices in Pajak.io",
        tracking=True
    )
    l10n_id_pajakio_reject_reason = fields.Text(
        string="Pajak.io Rejected Reason",
        readonly=True,
        copy=False,
        help="When DJP rejects an invoice submitted via pajak.io, they will provide a reason"
    )
    l10n_id_pajakio_file = fields.Binary(
        string="Pajak.io File",
        copy=False,
        readonly=True,
        export_string_translation=False,
    )
    def _l10n_id_pajakio_is_eligible(self):
        """ Check if invoice is eligible to be sent to Pajak.io. Raise errors if
        some conditions are violated """

        err_messages = []

        if not self.company_id.vat:
            err_messages.append(_("Your company's NPWP is not found in the tax settings"))
        if not self.company_id.city:
            err_messages.append(_("Your company's city hasn't been configured yet."))

        # check for every customer
        for partner in self.partner_id:
            comm = partner.commercial_partner_id
            if not comm.l10n_id_pkp:
                err_messages.append(_("Customer %s is not taxable, tick ID PKP if necessary", comm.name))
            if comm.l10n_id_buyer_document_type != 'TIN' and not comm.l10n_id_buyer_document_number:
                err_messages.append(_("Document number for customer %s hasn't been filled in", comm.name))
            if not comm.vat:
                err_messages.append(_("NPWP for customer %s hasn't been filled in yet", comm.name))
            if not comm.country_id:
                err_messages.append(_("No country is set for customer %s", comm.name))

        # check for every invoice
        for record in self:
            if record.state == 'draft':
                err_messages.append(_('Invoice %s is in draft state', record.name))
            if record.country_code != 'ID':
                err_messages.append(_("Invoice %s is not under Indonesian company", record.name))
            if record.move_type != 'out_invoice':
                err_messages.append(_("Entry %s is not an invoice", record.name))
            if not record.line_ids.tax_ids:
                err_messages.append(_("Invoice %s does not contain any taxes", record.name))
            if record.l10n_id_kode_transaksi == "07":
                if not (record.l10n_id_coretax_add_info_07 and record.l10n_id_coretax_facility_info_07):
                    err_messages.append(_("Invoice %s doesn't contain the Additional info and Facility Stamp yet (Kode 07)", record.name))
            if record.l10n_id_kode_transaksi == "08":
                if not (record.l10n_id_coretax_add_info_08 and record.l10n_id_coretax_facility_info_08):
                    err_messages.append(_("Invoice %s doesn't contain the Additional info and Facility Stamp yet (Kode 08)", record.name))

        if err_messages:
            err_messages = [_('Unable to send to pajak.io for the following reasons(s):')] + err_messages
            raise UserError('\n - '.join(err_messages))

    def _prepare_invoice_payload_pajakio(self):
        """ Prepare the JSON data that will be used when sending invoice data to Pajak.io """

        self.ensure_one()
        self._l10n_id_pajakio_is_eligible()

        efaktur = self.prepare_efaktur_vals()[0]

        document_type_mapping = {
            "TIN": "NPWP",
            "NIK": "NIK",
            "Passport": "PASPOR",
            "Other": "LAINNYA"
        }

        document = document_type_mapping.get(efaktur["BuyerDocument"], "NIK")
        payload = {
            "autoUploadDjp": True,
            "pengganti": False,
            "noInvoice": efaktur["RefDesc"],
            "kdJenisTransaksi": 'TD.003' + efaktur['TrxCode'],
            "lawanTransaksi": {
                "identityType": document,
                "identityValue": efaktur["BuyerDocumentNumber"] if document != "NPWP" else efaktur["BuyerTin"],
                "nitku": efaktur["BuyerIDTKU"],
                "nama": efaktur["BuyerName"],
                "alamatJalan": efaktur["BuyerAdress"],
                "kodeNegara": efaktur["BuyerCountry"],
            },
            "masaPajak": self.invoice_date.strftime("%m"),
            "tahunPajak": self.invoice_date.strftime("%Y"),
            "tanggalFaktur": efaktur["TaxInvoiceDate"],
            "tarifPpn": 11.0,
            "barangJasa": [{
                "jenis": "JASA" if line["Opt"] == "B" else "BARANG",
                "kode": line["Code"],
                "nama": line["Name"],
                "jumlah": float(line["Qty"]),
                "kodeSatuan": line["Unit"],
                "harga": float(line["Price"]),
                "totalHarga": float(line["Price"]) * float(line["Qty"]),
                "diskon": float(line["TotalDiscount"]),
                "tarifPpn": float(line["VATRate"]),
                "dpp": float(line["TaxBase"]),
                "cekDppLain": self.l10n_id_kode_transaksi == "04",
                "dppLain": float(line["OtherTaxBase"]),
                "ppn": float(line["VAT"]),
                "tarifPpnbm": 0,
                "ppnbm": 0
            } for line in efaktur["lines"]],
            "terminPembayaran": {
                "type": "NORMAL"
            },
            "penandatangan": {
                "nama": self.company_id.name,
                "npwp": self.company_id.vat,
                "jabatan": "Penandatangan",
                "kota": self.company_id.city,
                "passphrase": self.company_id.name
            },
            "pembuatFaktur": {
                "npwp": self.company_id.vat,
                "nama": self.company_id.name,
            }
        }
        return payload

    def _l10n_id_pajakio_send(self, json_content):
        """ Send invoice JSON payload to IAP, which will create an invoice in Pajak.io """

        self.ensure_one()
        response = self.env['iap.account']._l10n_id_pajakio_iap_connect(
            {"invoice_payload": json_content},
            "/api/pajakio/1/create_invoice"
        )

        if 'error' in response:
            return response['error']

        data = response.get('data')
        self.l10n_id_pajakio_transaction_id = data.get('transactionId')

    def _l10n_id_pajakio_update_status(self):
        """ Updating the status of invoice submission on Pajak.io platform """

        self.ensure_one()

        transaction_ids = self.mapped('l10n_id_pajakio_transaction_id')
        response = self.env['iap.account']._l10n_id_pajakio_iap_connect(
            {"transaction_ids": transaction_ids},
            "/api/pajakio/1/update"
        )

        if 'error' in response:
            return response['error']

        # update the status of invoices based on the status repsonse for each transaction
        trx_status_map = response.get('data')
        for move in self.filtered(lambda mv: mv.l10n_id_pajakio_transaction_id):
            invoice_response = trx_status_map.get(move.l10n_id_pajakio_transaction_id)
            invoice_data = invoice_response.get('data')

            # "cancelled" invoices are not reflected on the status but instead "jenisFaktur" (invoice type)
            if invoice_data.get('jenisFaktur') == "BATAL":
                move.l10n_id_pajakio_status = "cancel"
                continue

            # else check based on status
            response_status = invoice_response.get('status')

            message = ""
            if response_status == "missing":
                message = _("The following transaction is not found in Pajak.io")
            elif response_status == "error":
                reason = response_status.get("error")
                message = _("The update failed with the following response: %s", reason)
            elif response_status == "APPROVAL_SUKSES":
                message = _("The invoice has been approved by DJP")
                move.write({
                    "l10n_id_pajakio_status": "approved",
                    "l10n_id_pajakio_invoice_number": invoice_data.get('nofa'),
                    "l10n_id_pajakio_reject_reason": False,
                    "l10n_id_pajakio_transaction_url": invoice_data.get('urlPdf')
                })
            elif response_status == "MENUNGGU_VERIFIKASI_DJP":
                move.l10n_id_pajakio_status = "waiting"
            elif response_status == "DITOLAK":
                reason = invoice_data.get('alasan')
                message = _("The invoice has been rejected by DJP with the following reason: %s", reason)
                move.write({
                    "l10n_id_pajakio_status": "rejected",
                    "l10n_id_pajakio_reject_reason": reason,
                })
            else:
                message = _("The invoice status is unknown")

            if message:
                move.message_post(body=message)

    def action_update_pajakio_status(self):
        """ User action to update the status of invoice submission on Pajak.io platform. This will call the API to get the latest status and update the invoice accordingly """
        error = self._l10n_id_pajakio_update_status()
        if error:
            raise UserError(_("Pajak.io: Unable to update status with the following error: %s", error))

    def button_request_cancel(self):
        """ Override such that w ealso send cancel request to Pajak.io and update status afterwards """

        res = super().button_request_cancel()
        if not self.l10n_id_pajakio_status == 'approved':
            raise UserError(_("Only invoices that have been approved in Pajak.io can be cancelled"))

        response = self.env['iap.account']._l10n_id_pajakio_iap_connect(
            {"transaction_ids": [self.l10n_id_pajakio_transaction_id]},
            "/api/pajakio/1/cancel_invoice"
        )
        if 'error' in response:
            raise UserError(_("Pajak.io: Unable to cancel invoice with the following error: %s", response['error']))
        # if cancellec successfully, any error that happens after this should be handled (not raising error)
        # since we cannot re-cancel in pajak.io again
        error = self._l10n_id_pajakio_update_status()
        if error:
            self.message_post(body=_("Pajak.io: Invoice cancellation might be successful but unable to update status with the following error: %s", error))
        return res

    def _need_cancel_request(self):
        # EXTENDS 'account'
        return super()._need_cancel_request() or self.l10n_id_pajakio_status == 'approved'
