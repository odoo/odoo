import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    setup(vals) {
        super.setup(...arguments);
        if (this.isChileanCompany()) {
            this.to_invoice = vals.to_invoice === false ? vals.to_invoice : true;
            this.invoice_type = vals.invoice_type || "boleta";
            this.voucher_number = vals.voucher_number || "";
        }
    },
    doNotAllowRefundAndSales() {
        return this.isChileanCompany() || super.doNotAllowRefundAndSales(...arguments);
    },
    isChileanCompany() {
        return this.company.country_id?.code == "CL";
    },
    is_to_invoice() {
        if (this.isChileanCompany()) {
            return true;
        }
        return super.is_to_invoice(...arguments);
    },
    set_to_invoice(to_invoice) {
        if (this.isChileanCompany()) {
            this.assert_editable();
            this.to_invoice = true;
        } else {
            super.set_to_invoice(...arguments);
        }
    },
    isFactura() {
        if (this.invoice_type == "boleta") {
            return false;
        }
        return true;
    },
    export_for_printing(baseUrl, headerData) {
        const result = super.export_for_printing(...arguments);
        if (!this.isChileanCompany()) {
            return result;
        }
        return {
            ...result,
            voucher_number: this.voucher_number,
            l10n_cl_sii_barcode_image: this.account_move?.l10n_cl_sii_barcode_image,
            l10n_cl_dte_resolution_number: this.company_id.l10n_cl_dte_resolution_number,
            l10n_cl_dte_resolution_date: this.company_id.l10n_cl_dte_resolution_date,
        };
    },
});
