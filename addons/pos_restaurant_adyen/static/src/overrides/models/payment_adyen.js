import { PaymentAdyen } from "@pos_adyen/app/payment_adyen";
import { patch } from "@web/core/utils/patch";

patch(PaymentAdyen.prototype, {
    _adyen_pay_data() {
        var data = super._adyen_pay_data(...arguments);

        if (data.SaleToPOIRequest.PaymentRequest.SaleData.SaleToAcquirerData) {
            data.SaleToPOIRequest.PaymentRequest.SaleData.SaleToAcquirerData +=
                "&authorisationType=PreAuth";
        } else {
            data.SaleToPOIRequest.PaymentRequest.SaleData.SaleToAcquirerData =
                "authorisationType=PreAuth";
        }

        return data;
    },

    send_payment_adjust(uuid) {
        var order = this.pos.get_order();
        var line = order.get_paymentline_by_uuid(uuid);
        var data = {
            originalReference: line.transaction_id,
            modificationAmount: {
                value: parseInt(line.amount * Math.pow(10, this.pos.currency.decimal_places)),
                currency: this.pos.currency.name,
            },
            merchantAccount: this.payment_method_id.adyen_merchant_account,
            additionalData: {
                industryUsage: "DelayedCharge",
            },
        };

        return this._call_adyen(data, "adjust");
    },

    canBeAdjusted(uuid) {
        var order = this.pos.get_order();
        var line = order.get_paymentline_by_uuid(uuid);
        return ["mc", "visa", "amex", "discover"].includes(line.card_type);
    },
});
