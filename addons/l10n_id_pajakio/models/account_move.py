# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"


    # Pajak.io related fields
    # NOTE: at the moment, we want to limit 1 database to be associated to just 1 account
    # this is due to the fact that each database can only have 1 IAP account and therefore
    # paid credit management will be difficult to manage if there are multiple accounts
    # in the same database
    l10n_id_pajakio_transaction_id = fields.Char(
        string="Pajak.io Transaction ID",
        readonly=True,
        copy=False,
        help="Unique identifier of invoices created in pajak.io"
    )

    l10n_id_pajakio_trx_url = fields.Char(
        string="Pajak.io Transaction URL",
        readonly=True,
        copy=False,
        help="URL to view the invoice receipt validated in pajak.io"
    )
    l10n_id_pajakio_nofa = fields.Char(
        string="Pajak.io Invoice Number",
        readonly=True,
        copy=False,
        help="Inoivce number assigned by pajak.io"
    )
    l10n_id_pajakio_failure_reason = fields.Text(
        string="Pajak.io Failure Reason",
        readonly=True,
        copy=False,
        help="Reason for failure during the invoice upload to DJP"
    )
    l10n_id_pajakio_status = fields.Selection(
        [
            ("waiting", "Waiting for Approval"),
            ('approved', "Approved"),
            ('rejected', "Rejected"),
            ('cancel', "Cancelled")
        ],
        string="Pajak.io Status",
        readonly=True,
        copy=False,
        help="Current status of the transaction in pajak.io",
    )
    l10n_id_pajakio_file = fields.Binary(
        string="Pajak.io File",
        copy=False,
        readonly=True,
        export_string_translation=False,
    )

    def _l10n_id_pajakio_check_before_generate(self):
        # taken from the original l10n_id_efaktur_coretax
        if len(self.company_id) > 1:
            raise UserError(_("You are not allowed to generate e-Faktur document from invoices coming from different companies"))

        err_messages = []

        if not self.company_id.vat:
            err_messages.append(_("Your company's VAT hasn't been configured yet"))
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
            if not record.country_code == 'ID':
                err_messages.append(_("Invoice %s is not under Indonesian company", record.name))
            if not record.move_type == 'out_invoice':
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
        """ Using standard method `_l10n_id_coretax_build_invoice_vals` to generate values
        which will then be converted to the data fitting for API. 
        Since the API method will always be batched, we will always prepare a list of values as well """
        
        # Pre-check to report error in case of missing/invalid data
        self._l10n_id_pajakio_check_before_generate()

        efaktur_vals = self.prepare_efaktur_vals()
        payload = {}

        document_type_mapping = {
            "TIN": "NPWP",
            "NIK": "NIK",
            "Passport": "PASPOR",
            "Other": "LAINNYA"
        }

        for efaktur, move in zip(efaktur_vals, self):
            document = document_type_mapping.get(efaktur["BuyerDocument"], "NIK")

            payload.update({
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
                "masaPajak": move.invoice_date.strftime("%m"),
                "tahunPajak": move.invoice_date.strftime("%Y"),
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
                    "cekDppLain": True if move.l10n_id_kode_transaksi == "04" else False,
                    "dppLain": float(line["OtherTaxBase"]),
                    "ppn": float(line["VAT"]),
                    "tarifPpnbm": 0,
                    "ppnbm": 0
                } for line in efaktur["lines"]],
                "terminPembayaran": {
                    "type": "NORMAL"
                },
                "penandatangan": {
                    "nama": move.company_id.name,
                    "npwp": move.company_id.vat,
                    "jabatan": "Penandatangan",
                    "kota": move.company_id.city,
                    "passphrase": move.company_id.name
                },
                "pembuatFaktur": {
                    "npwp": move.company_id.vat,
                    "nama": move.company_id.name,
                }
            })
        return payload

    # ---------- pajakio integrations methods ----------
    def _l10n_id_pajakio_send(self, json_content):
        """ Send the invoice payload to IAP pajak.io connector """
        self.ensure_one()
        response = self.env['iap.account']._l10n_id_pajakio_iap_connect(
           {"invoice_payload": json_content},
            "/l10n_id_pajakio/create_invoice"
        )

        if 'error' in response:
            return response['error']

        data = response.get("data")

        # fill iin the transaction id and mark as uploaded
        self.l10n_id_pajakio_transaction_id = data.get("transactionId")

    def _l10n_id_pajakio_update_status(self):
        """ Trigger for creating the invoice payload and pass it over to the IAP side to 
        generate pajak.io faktur in batch mode"""

        transaction_ids = self.mapped("l10n_id_pajakio_transaction_id")
        response = self.env['iap.account']._l10n_id_pajakio_iap_connect(
            {"transaction_ids": transaction_ids},
            "/l10n_id_pajakio/update"
        )
        
        if 'error' in response:
            return response["error"]
        
        # response data should be in the format of {'transaction_id': {..}}
        data = response.get("data")
        for move in self:
            result = data.get(move.l10n_id_pajakio_transaction_id)
            status = result["status"]
            detail = result["data"]

            if detail.get('jenisFaktur') == 'BATAL':
                move.write({
                    "l10n_id_pajakio_status": "cancel",
                })
            # successful approval
            elif status == "APPROVAL_SUKSES":
                move.write({
                    "l10n_id_pajakio_status": "approved",
                    "l10n_id_pajakio_trx_url": detail.get("urlPdf"),
                    "l10n_id_pajakio_nofa": detail.get("nofa"),
                    "l10n_id_pajakio_failure_reason": False
                })
            # still waiting
            elif status == "MENUNGGU_VERIFIKASI_DJP":
                move.write({
                    "l10n_id_pajakio_status": "waiting",
                })
            # rejected
            elif status == "DITOLAK":
                move.write({
                    "l10n_id_pajakio_status": "rejected",
                    "l10n_id_pajakio_failure_reason": detail.get("keteranganDjp"),
                })

    def _l10n_id_pajakio_cancel(self):
        """Cancel invoice in pajak.io. This operation is only allowed on transactions that have been 
        uploaded and have been succesfully approved by DJP. We will update the invoice status as well
        """

        # ensure all inovices have the latest status before cancelling
        self._l10n_id_pajakio_update_status()
        if invoice := self.filtered(lambda m: m.l10n_id_pajakio_status != "approved"):
            raise UserError(_("Some of the selected invoices have not been approved yet in pajak.io: %s. You can update the status first.", invoice.mapped("name")))
        
        transaction_ids = self.mapped("l10n_id_pajakio_transaction_id")
        response = self.env['iap.account']._l10n_id_pajakio_iap_connect(
            {"transaction_ids": transaction_ids},
            "/l10n_id_pajakio/cancel_invoice"
        )

        if 'error' in response:
            raise UserError(response["error"])

        # if any of cancel fails, we should log it
        data = response.get("data")
        for move in self:
            result = data.get(move.l10n_id_pajakio_transaction_id)
            if "error" in result:
                move.message_post(body=_("Failed to cancel invoice in pajak.io: %s" % result.get("error")))
            else:
                move._message_log(body='The pajak.io faktur has been cancelled succesfully!')


    @api.depends("l10n_id_pajakio_status")
    def _compute_need_cancel_request(self):
        # EXTENDS 'account'
        super()._compute_need_cancel_request()

    def _need_cancel_request(self):
        # EXTENDS 'account'
        return super()._need_cancel_request() or self.l10n_id_pajakio_status == 'approved'

    def button_request_cancel(self):
        # EXTENDS 'account'
        res = super().button_request_cancel()
        pajakio_invoices = self.filtered(lambda m: m.l10n_id_pajakio_status == 'approved')
        if pajakio_invoices:
            pajakio_invoices._l10n_id_pajakio_cancel()
            pajakio_invoices._l10n_id_pajakio_update_status()
            pajakio_invoices.button_cancel()

        return res

    def _cron_update_pajakio_status(self):
        """ CRON method to update the status for all invoices whose status is still waiting """
        pending_invoices = self.search([('l10n_id_pajakio_status', '=', 'waiting')])
        pending_invoices._l10n_id_pajakio_update_status()
