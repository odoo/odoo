import { patch } from "@web/core/utils/patch";
import { GeneratePrinterData } from "@point_of_sale/app/utils/printer/generate_printer_data";

const { DateTime } = luxon;

/**
 * This class is a JS copy of the class PosOrderReceipt in Python.
 */
patch(GeneratePrinterData.prototype, {
    generateReceiptData() {
        const data = super.generateReceiptData(...arguments);

        if (this.order?.isPrintEcpayInvoice && !this.order.ecpay_error) {
            let iisCreateDate = this.order?.iis_create_date || "";
            if (iisCreateDate?.toFormat) {
                iisCreateDate = iisCreateDate.toFormat("yyyy-MM-dd HH:mm:ss");
            } else if (iisCreateDate instanceof Date) {
                iisCreateDate = DateTime.fromJSDate(iisCreateDate).toFormat("yyyy-MM-dd HH:mm:ss");
            }
            data.extra_data.isPrintEcpayInvoice = this.order.isPrintEcpayInvoice;
            data.extra_data.ecpay_error = this.order.ecpay_error;
            data.extra_data.account_fiscal_country_code =
                this.company.account_fiscal_country_id.code;
            data.extra_data.invoice_month = this.order.invoice_month;
            data.extra_data.iis_number = this.order.iis_number;
            data.extra_data.iis_create_date = iisCreateDate;
            data.extra_data.iis_random_number = this.order.iis_random_number;
            data.extra_data.l10n_tw_edi_invoice_amount = this.formatCurrency(
                this.order.l10n_tw_edi_invoice_amount
            );
            data.extra_data.iis_tax_amount = this.formatCurrency(this.order.iis_tax_amount);
            data.extra_data.total_amount = this.formatCurrency(
                this.order.l10n_tw_edi_invoice_amount - this.order.iis_tax_amount
            );
            data.extra_data.l10n_tw_edi_carrier_number = this.order.l10n_tw_edi_carrier_number;
            data.extra_data.l10n_tw_edi_carrier_type = this.order.l10n_tw_edi_carrier_type;
            data.extra_data.l10n_tw_edi_ecpay_seller_identifier =
                this.order.l10n_tw_edi_ecpay_seller_identifier;
            data.image.pos_barcode = this.order.pos_barcode;
            if (this.order.pos_barcode) {
                data.image.pos_barcode_src =
                    "/report/barcode/Code128/" + encodeURIComponent(this.order.pos_barcode);
            }
            if (this.order.qrcode_left) {
                data.image.qrcode_left = "data:image/png;base64," + this.order.qrcode_left;
            }
            if (this.order.qrcode_right) {
                data.image.qrcode_right = "data:image/png;base64," + this.order.qrcode_right;
            }
        }

        return data;
    },

    generateLineData() {
        const lines = super.generateLineData(...arguments);
        return lines.map((data, index) => {
            const line = this.order.lines[index];
            return {
                ...data,
                // Add custom code here to always get the price including tax for the receipt
                price_subtotal_incl_custom: this.formatCurrency(line?.price_subtotal_incl || 0),
                price_unit_incl_custom:
                    line?.qty && line.qty !== 0
                        ? this.formatCurrency(line.price_subtotal_incl / line.qty)
                        : this.formatCurrency(0),
            };
        });
    },
});
