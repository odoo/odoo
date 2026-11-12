import { PaymentMethod } from "@pos_payment_method/payment_method";
import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";

patch(PaymentMethod.prototype, {
    setup(electronicPaymentId, accessToken) {
        super.setup(...arguments);
        this.accessToken = accessToken;
    },

    async _callPaymentMethod(method, ...args) {
        if (
            ![
                "start_payment",
                "cancel_transaction",
                "get_transaction_status",
                "init_payment_method",
            ].includes(method)
        ) {
            return super._callPaymentMethod(...arguments);
        }
        const params = {
            access_token: this.accessToken,
            electronic_payment_id: this.id,
            args,
        };
        return await rpc(`/kiosk/payment/${method}`, params, {
            silent: true,
        });
    },
});
