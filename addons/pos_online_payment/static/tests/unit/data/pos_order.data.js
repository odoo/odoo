import { patch } from "@web/core/utils/patch";
import { roundPrecision } from "@web/core/utils/numbers";
import { PosOrder } from "@point_of_sale/../tests/unit/data/pos_order.data";

patch(PosOrder.prototype, {
    get_and_set_online_payments_data(orderId, next_online_payment_amount = false) {
        const [order] = this.browse(orderId);
        if (["paid", "done"].includes(order.state)) {
            return { id: order.id, paid_order: this.read([order.id], [], false) };
        }

        const payments = this.env["pos.payment"].read(
            order.payment_ids,
            ["amount", "payment_method_id", "online_account_payment_id"],
            false
        );
        const onlinePayments = payments
            .filter((payment) => payment.online_account_payment_id)
            .map(({ payment_method_id, amount }) => ({ payment_method_id, amount }));
        const amountPaid = payments.reduce((total, payment) => total + payment.amount, 0);
        const data = {
            id: order.id,
            online_payments: onlinePayments,
            amount_unpaid: roundPrecision(order.amount_total - amountPaid, 0.01),
        };
        if (
            typeof next_online_payment_amount === "number" &&
            next_online_payment_amount === 0 &&
            onlinePayments.length === 0 &&
            order.state === "draft"
        ) {
            data.deleted = true;
        }
        return data;
    },
});
