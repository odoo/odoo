import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(OrderPaymentValidation.prototype, {
    /**
     * @override
     */
    setup(vals) {
        super.setup(...arguments);
        this.refundedOrder = this.order.refunded_order_id;
    },
    /**
     * @override
     */
    async validateOrder(isForceValidate) {
        if (
            this.refundedOrder?.source === "mobile" &&
            this.refundedOrder?.payment_ids[0].online_account_payment_id &&
            !isForceValidate
        ) {
            this.pos.env.services.ui.block();
            for (const line of this.order.payment_ids) {
                if (
                    line.payment_method_id.id ===
                    this.pos.config.self_order_online_payment_method_id?.id
                ) {
                    let accountPaymentId = await this.pos.data.orm.call(
                        "account.payment",
                        "send_refund_request",
                        [
                            this.refundedOrder.payment_ids[0].online_account_payment_id.id,
                            Math.abs(line.amount),
                            this.order.id,
                            line.payment_method_id.id,
                        ]
                    );
                    if (!accountPaymentId) {
                        this.pos.notification.add(
                            _t("Refund request failed! Please try with another payment method."),
                            {
                                type: "warning",
                                sticky: false,
                            }
                        );
                        this.pos.env.services.ui.unblock();
                        return;
                    }
                    [accountPaymentId] = await this.pos.data.searchRead("account.payment", [
                        ["id", "=", accountPaymentId],
                    ]);
                    line.online_account_payment_id = accountPaymentId;
                    line.setPaymentStatus("done");
                }
            }
            this.pos.env.services.ui.unblock();
        }
        return await super.validateOrder(...arguments);
    },
});
