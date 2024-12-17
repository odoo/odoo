import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    setup() {
        super.setup(...arguments);
        if (this.company.country_id?.code === "TW" && this.config.is_ecpay_enabled) {
            if (!this.partner_id && this.session._default_tw_customer_id) {
                this.update({ partner_id: this.session._default_tw_customer_id });
            }
            if (this.partner_id) {
                this.l10n_tw_edi_is_b2b = this.partner_id.commercial_partner_id.is_company;
            }
        }
    },

    set_invoice_info(
        l10n_tw_edi_is_print,
        l10n_tw_edi_love_code,
        l10n_tw_edi_carrier_type,
        l10n_tw_edi_carrier_number,
        l10n_tw_edi_carrier_number_2
    ) {
        this.l10n_tw_edi_is_print = l10n_tw_edi_is_print;
        this.l10n_tw_edi_love_code = l10n_tw_edi_love_code;
        this.l10n_tw_edi_carrier_type = l10n_tw_edi_carrier_type;
        this.l10n_tw_edi_carrier_number = l10n_tw_edi_carrier_number;
        this.l10n_tw_edi_carrier_number_2 = l10n_tw_edi_carrier_number_2;
    },

    export_for_printing(baseUrl, headerData) {
        const result = super.export_for_printing(...arguments);
        const is_print_ecpay_invoice =
            this.config.is_ecpay_enabled &&
            this.company.country_id?.code === "TW" &&
            this.is_to_invoice() &&
            this.l10n_tw_edi_is_print &&
            !this.l10n_tw_edi_is_b2b &&
            !this.get_orderlines().some((line) => line.refunded_orderline_id);

        if (is_print_ecpay_invoice) {
            return {
                ...result,
                invoice_month: this.invoice_month,
                iis_number: this.iis_number,
                iis_create_date: this.iis_create_date,
                iis_random_number: this.iis_random_number,
                iis_tax_amount: this.iis_tax_amount,
                l10n_tw_edi_invoice_amount: this.l10n_tw_edi_invoice_amount,
                iis_identifier: this.iis_identifier,
                iis_carrier_type: this.iis_carrier_type,
                iis_carrier_num: this.iis_carrier_num,
                iis_category: this.iis_category,
                l10n_tw_edi_ecpay_seller_identifier: this.l10n_tw_edi_ecpay_seller_identifier,
                pos_barcode: this.pos_barcode,
                qrcode_left: this.qrcode_left ? this.get_ecpay_qrcode(this.qrcode_left) : undefined,
                qrcode_right: this.qrcode_right
                    ? this.get_ecpay_qrcode(this.qrcode_right)
                    : undefined,
                company_name: this.company.name,
                ecpay_error: this.error,
                is_print_ecpay_invoice: is_print_ecpay_invoice,
            };
        }
        return result;
    },

    get_ecpay_qrcode(data) {
        const codeWriter = new window.ZXing.BrowserQRCodeSvgWriter();
        const qrCodeSvg = new XMLSerializer().serializeToString(codeWriter.write(data, 250, 250));
        return "data:image/svg+xml;base64," + window.btoa(qrCodeSvg);
    },
});
