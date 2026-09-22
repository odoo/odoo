import { patch } from "@web/core/utils/patch";
import { PaymentScreenStatus } from "@point_of_sale/app/screens/payment_screen/payment_status/payment_status";
import { useService } from "@web/core/utils/hooks";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

patch(PaymentScreenStatus.prototype, {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
    },

    async onClickSplitAndPay() {
        const originOrder = this.order;
        const blockingReason = originOrder.splitPaymentBlockingReason;
        if (blockingReason) {
            this.dialog.add(AlertDialog, {
                title: _t("Split and pay unavailable"),
                body: blockingReason,
            });
            return;
        }

        const shares = originOrder.computeSplitPaymentShares(originOrder.amountPaid);
        const floatingOrder = this.pos.addNewOrder({ floating_order_name: _t("Split Payment") });
        originOrder.transferSplitPaymentInfosTo(floatingOrder);
        for (const { baseLine, delta } of shares) {
            if (!floatingOrder.currency.isZero(delta)) {
                await this.pos.addSplitPaymentLine(floatingOrder, baseLine, delta);
            }
        }
        originOrder.transferPaymentLinesTo(floatingOrder);
        if (!originOrder.isSynced) {
            await this.pos.syncAllOrders({ orders: [originOrder] });
        }
        floatingOrder.split_origin_order_id = originOrder;

        const accepted = await this.pos.validateOrder({ order: floatingOrder });
        if (!accepted) {
            floatingOrder.transferPaymentLinesTo(originOrder);
            this.pos.setOrder(originOrder);
            this.pos.removeOrder(floatingOrder, false);
        }
    },

    get isSplitAndPayDisabled() {
        const order = this.order;
        const hasValidatedPartialPayment =
            order.currency.isPositive(order.amountPaid) &&
            order.currency.isPositive(order.totalDue - order.amountPaid);
        const hasPaymentInProgress = order.payment_ids.some((payment) => !payment.isDone());
        const requiresPartner =
            !order.getPartner() &&
            (order.isToInvoice() ||
                order.payment_ids.some((payment) => payment.payment_method_id.type == "pay_later"));
        return !hasValidatedPartialPayment || hasPaymentInProgress || requiresPartner;
    },
});
