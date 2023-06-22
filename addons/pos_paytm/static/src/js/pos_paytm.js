/** @odoo-module */

import { Payment } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";


patch(Payment.prototype, "pos_paytm.Payment", {
    init_from_JSON(json) {
        this._super(...arguments);
        if(this.payment_method?.use_payment_terminal === 'paytm'){
            this.paytm_authcode = json.paytm_authcode;
            this.paytm_issuer_card_no = json.paytm_issuer_card_no;
            this.paytm_issuer_bank = json.paytm_issuer_bank;
            this.paytm_payment_method = json.paytm_payment_method;
            this.paytm_reference_no = json.paytm_reference_no;
            this.paytm_card_scheme = json.paytm_card_scheme;
        }
    },
    export_as_JSON() {
        const result = this._super(...arguments);
        if(result && this.payment_method?.use_payment_terminal === 'paytm'){
            return Object.assign(result, {
                paytm_authcode: this.paytm_authcode,
                paytm_issuer_card_no: this.paytm_issuer_card_no,
                paytm_issuer_bank: this.paytm_issuer_bank,
                paytm_payment_method: this.paytm_payment_method,
                paytm_reference_no: this.paytm_reference_no,
                paytm_card_scheme: this.paytm_card_scheme,
            });
        }
        return result
    },
});
