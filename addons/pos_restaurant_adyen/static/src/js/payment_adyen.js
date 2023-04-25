/** @odoo-module */

import { PaymentAdyen } from "@pos_adyen/js/payment_adyen";
import { patch } from "@web/core/utils/patch";

patch(PaymentAdyen.prototype, "pos_restaurant_adyen.PaymentAdyen", {
    _adyen_pay_data() {
        var data = this._super(...arguments);

        if (data.SaleToPOIRequest.PaymentRequest.SaleData.SaleToAcquirerData) {
            data.SaleToPOIRequest.PaymentRequest.SaleData.SaleToAcquirerData +=
                "&authorisationType=PreAuth";
        } else {
            data.SaleToPOIRequest.PaymentRequest.SaleData.SaleToAcquirerData =
                "authorisationType=PreAuth";
        }

        return data;
    },

    send_payment_adjust(cid) {
        var order = this.pos.get_order();
        var line = order.get_paymentline(cid);
        var data = {
            originalReference: line.transaction_id,
            modificationAmount: {
                value: parseInt(line.amount * Math.pow(10, this.pos.currency.decimal_places)),
                currency: this.pos.currency.name,
            },
            merchantAccount: this.payment_method.adyen_merchant_account,
            additionalData: {
                industryUsage: "DelayedCharge",
            },
        };

        return this._call_adyen(data, "adjust");
    },

    canBeAdjusted(cid) {
        var order = this.pos.get_order();
        var line = order.get_paymentline(cid);
        return ["mc", "visa", "amex", "discover"].includes(line.card_type);
    },
});
