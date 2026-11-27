import { rpc } from "@web/core/network/rpc";
import { QFPay } from "@pos_qfpay/app/qfpay";

export class KioskQFPay extends QFPay {
    setup(env, paymentMethod, errorCallback, accessToken) {
        super.setup(...arguments);
        this.accessToken = accessToken;
    }

    signRequest(order) {
        return rpc("/pos-self-order/qfpay-sign-trade", {
            access_token: this.accessToken,
            order_id: order.id,
            order_access_token: order.access_token,
            payment_method_id: this.paymentMethod.id,
        });
    }
}
