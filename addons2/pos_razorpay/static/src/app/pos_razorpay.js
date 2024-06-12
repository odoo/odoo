/** @odoo-module */

import { Payment } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";


patch(Payment.prototype, {
    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        if(this.payment_method?.use_payment_terminal === 'razorpay'){
            this.razorpay_authcode = json.razorpay_authcode;
            this.razorpay_issuer_card_no = json.razorpay_issuer_card_no;
            this.razorpay_issuer_bank = json.razorpay_issuer_bank;
            this.razorpay_payment_method = json.razorpay_payment_method;
            this.razorpay_reference_no = json.razorpay_reference_no;
            this.razorpay_reverse_ref_no = json.razorpay_reverse_ref_no;
            this.razorpay_card_scheme = json.razorpay_card_scheme;
            this.razorpay_card_owner_name = json.razorpay_card_owner_name;
        }
    },
    export_as_JSON() {
        const result = super.export_as_JSON(...arguments);
        if(result && this.payment_method?.use_payment_terminal === 'razorpay'){
            return Object.assign(result, {
                razorpay_authcode: this.razorpay_authcode,
                razorpay_issuer_card_no: this.razorpay_issuer_card_no,
                razorpay_issuer_bank: this.razorpay_issuer_bank,
                razorpay_payment_method: this.razorpay_payment_method,
                razorpay_reference_no: this.razorpay_reference_no,
                razorpay_reverse_ref_no: this.razorpay_reverse_ref_no,
                razorpay_card_scheme: this.razorpay_card_scheme,
                razorpay_card_owner_name: this.razorpay_card_owner_name,
            });
        }
        return result
    },
});
