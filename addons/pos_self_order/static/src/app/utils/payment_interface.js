import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";

patch(PaymentInterface.prototype, {
    async callPaymentMethod(method, args, kwargs = {}) {
        const params = {
            access_token: this.pos.access_token,
            args,
            kwargs,
        };
        return await rpc(`/kiosk/payment_method_action/${method}`, params, {
            silent: true,
        });
    },
});
