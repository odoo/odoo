/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    // @Override
    async _processData(loadedData) {
        await super._processData(...arguments);
        if (this.isChileanCompany()) {
            this.l10n_latam_identification_types = loadedData["l10n_latam.identification.type"];
            this.sii_taxpayer_types = loadedData["sii_taxpayer_types"];
            this.consumidorFinalAnonimoId = loadedData["consumidor_final_anonimo_id"];
        }
    },
    isChileanCompany() {
        return this.company.country?.code == "CL";
    },
    doNotAllowRefundAndSales() {
        return this.isChileanCompany() || super.doNotAllowRefundAndSales(...arguments);
    },
    _getCreateOrderContext(orders, options) {
        let context = super._getCreateOrderContext(...arguments);
        if (this.isChileanCompany()) {
            // FIXME in master: when processing multiple orders, and at least one is an invoice of type Factura,
            //  then we will generate the pdf for all invoices linked to the orders,
            //  since the context is applicable for the whole RPC requests `create_from_ui` on all orders.
            const noOrderRequiresInvoicePrinting = orders.every(
                (order) => order.data.to_invoice && order.data.invoiceType === "boleta"
            );
            if (noOrderRequiresInvoicePrinting) {
                context = { ...context, generate_pdf: false };
            }
        }
        return context;
    },
    getReceiptHeaderData(order) {
        const result = super.getReceiptHeaderData(...arguments);
        if (!this.isChileanCompany() || !order) {
            return result;
        }
        result.company.cl_vat = this.company.vat;
        result.l10n_cl_sii_regional_office = order.l10n_cl_sii_regional_office;
        result.l10n_latam_document_type = order.l10n_latam_document_type;
        result.l10n_latam_document_number = order.l10n_latam_document_number;
        result.date = order.receiptDate;

        return result;
    },
});

patch(Order.prototype, {
    setup() {
        super.setup(...arguments);
        if (this.pos.isChileanCompany()) {
            this.to_invoice = true;
            this.invoiceType = "boleta";
            if (!this.partner) {
                this.partner = this.pos.db.partner_by_id[this.pos.consumidorFinalAnonimoId];
            }
            this.voucherNumber = false;
        }
    },
    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        if (this.pos.isChileanCompany()) {
            json["invoiceType"] = this.invoiceType ? this.invoiceType : false;
            json["voucherNumber"] = this.voucherNumber;
        }
        return json;
    },
    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.voucherNumber = json.voucher_number || false;
        this.l10n_latam_document_type = json.l10n_latam_document_type || false;
        this.l10n_latam_document_number = json.l10n_latam_document_number || false;
        this.l10n_cl_sii_barcode = json.l10n_cl_sii_barcode || false;
        this.l10n_cl_sii_regional_office = json.l10n_cl_sii_regional_office
            ? json.l10n_cl_sii_regional_office[0]
            : false;
    },
    is_to_invoice() {
        if (this.pos.isChileanCompany()) {
            return true;
        }
        return super.is_to_invoice(...arguments);
    },
    set_to_invoice(to_invoice) {
        if (this.pos.isChileanCompany()) {
            this.assert_editable();
            this.to_invoice = true;
        } else {
            super.set_to_invoice(...arguments);
        }
    },
    isFactura() {
        if (this.invoiceType == "boleta") {
            return false;
        }
        return true;
    },
    export_for_printing() {
        return {
            ...super.export_for_printing(...arguments),
            voucherNumber: this.voucherNumber,
            l10n_cl_sii_barcode: this.l10n_cl_sii_barcode,
            l10n_cl_dte_resolution_number: this.pos.company.l10n_cl_dte_resolution_number,
            l10n_cl_dte_resolution_date: this.pos.company.l10n_cl_dte_resolution_date,
        };
    },
    wait_for_push_order() {
        var result = super.wait_for_push_order(...arguments);
        result = Boolean(result || this.pos.isChileanCompany());
        return result;
    },
});
