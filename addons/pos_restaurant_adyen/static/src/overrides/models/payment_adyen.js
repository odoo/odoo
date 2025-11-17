import { PaymentAdyen } from "@pos_adyen/app/utils/payment/payment_adyen";
import { patch } from "@web/core/utils/patch";

patch(PaymentAdyen.prototype, {
    _adyenPayData() {
        var data = super._adyenPayData(...arguments);

        if (data.SaleToPOIRequest.PaymentRequest.SaleData.SaleToAcquirerData) {
            data.SaleToPOIRequest.PaymentRequest.SaleData.SaleToAcquirerData +=
                "&authorisationType=PreAuth";
        } else {
            data.SaleToPOIRequest.PaymentRequest.SaleData.SaleToAcquirerData =
                "authorisationType=PreAuth";
        }

        return data;
    },
});
