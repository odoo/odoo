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
        this.pollingTimeout = null;
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
                    const paymentTransactionId = await this.pos.data.orm.call(
                        "account.payment",
                        "send_refund_request",
                        [
                            this.refundedOrder.payment_ids[0].online_account_payment_id.id,
                            Math.abs(line.amount),
                        ]
                    );
                    let accountPaymentId = await this.refundOnlineOrder(paymentTransactionId);
                    if (!accountPaymentId && paymentTransactionId) {
                        this.pos.notification.add(
                            _t(
                                "Your refund request has been processed. You will receive the refund as per the provider's timeline."
                            ),
                            {
                                type: "warning",
                                sticky: false,
                            }
                        );
                        this.pos.env.services.ui.unblock();
                        return await super.validateOrder(...arguments);
                    } else if (!accountPaymentId && !paymentTransactionId) {
                        this.pos.notification.add(
                            _t("Refund request failed! Please try with another payment method."),
                            {
                                type: "danger",
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
                }
            }
            this.pos.env.services.ui.unblock();
        }
        return await super.validateOrder(...arguments);
    },
    async refundOnlineOrder(paymentTransactionId) {
        let retryCount = 0;
        return new Promise((resolve, reject) => {
            const tryFetch = async () => {
                try {
                    const accountPaymentId = await this.pos.data.orm.call(
                        "account.payment",
                        "get_account_payment_id",
                        [false, paymentTransactionId]
                    );
                    if (accountPaymentId) {
                        return resolve(accountPaymentId);
                    }
                    if (retryCount >= 5) {
                        return resolve(false);
                    }
                    retryCount++;
                    this.pollingTimeout = setTimeout(tryFetch, 5000);
                } catch (error) {
                    reject(error);
                }
            };
            tryFetch();
        });
    },
});
