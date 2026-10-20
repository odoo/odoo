import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { PaymentInterfaceV2 } from "@point_of_sale/app/utils/payment/payment_interface_v2";
import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";

patch(PaymentInterface.prototype, {
    async callPaymentMethod(method, params) {
        params = {
            access_token: this.pos.access_token,
            args: params,
            kwargs: {},
        };
        return await rpc(`/kiosk/payment_method_action/${method}`, params, {
            silent: true,
        });
    },
});

patch(PaymentInterfaceV2.prototype, {
    setup() {
        super.setup(...arguments);
        // No cashier to "Check status": poll until the answer comes
        this.max_poll_failures = false;
        this.max_polling_duration = false;
    },
});
