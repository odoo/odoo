import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { onMounted, onWillStart } from "@odoo/owl";
import { useVivaApp } from "@pos_viva_com/app/hooks/use_viva_app";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        onMounted(() => {
            const pendingPaymentLine = this.currentOrder.payment_ids.find(
                (paymentLine) =>
                    paymentLine.payment_method_id.payment_provider === "viva_com" &&
                    !paymentLine.isDone() &&
                    paymentLine.getPaymentStatus() !== "pending"
            );
            if (!pendingPaymentLine) {
                return;
            }
        });

        this.vivaApp = useVivaApp(this.onClickValidate.bind(this));
        onWillStart(async () => {
            await this.vivaApp.process();
        });
    },
    async onClickValidate(args = {}) {
        const validationOptions = this.pos.getValidationOrderOptions(args);
        const fastPaymentMethod = validationOptions.fastPaymentMethod;
        if (fastPaymentMethod && this.vivaApp.use(fastPaymentMethod)) {
            await this.addNewPaymentLine(fastPaymentMethod);
            return;
        }
        return super.onClickValidate(...arguments);
    },
    async addNewPaymentLine(pm, args = {}) {
        if (this.vivaApp.use(pm)) {
            for (const lineUuid of this.currentOrder.payment_ids.map((line) => line.uuid)) {
                const paymentLine = this.currentOrder.getPaymentlineByUuid(lineUuid);
                if (this.vivaApp.use(paymentLine.payment_method_id) && !paymentLine.isDone()) {
                    paymentLine.delete();
                }
            }

            this.vivaApp.start(pm, this.isRefundOrder);
            return;
        }

        if (pm.payment_provider === "viva_com" && this.isRefundOrder) {
            const refundedOrder = this.currentOrder.lines[0]?.refunded_orderline_id?.order_id;
            const amountDue = Math.abs(this.currentOrder.remainingDue);
            const matchedPaymentLine = refundedOrder.payment_ids.find(
                (line) =>
                    line.payment_method_id.payment_provider === "viva_com" &&
                    line.amount === amountDue
            );
            if (matchedPaymentLine) {
                const paymentLineAddedSuccessfully = await super.addNewPaymentLine(pm, args);
                if (paymentLineAddedSuccessfully) {
                    const newPaymentLine = this.paymentLines.at(-1);
                    newPaymentLine.updateRefundPaymentLine(matchedPaymentLine);
                }
                return paymentLineAddedSuccessfully;
            }
        }

        return await super.addNewPaymentLine(pm, args);
    },
    deletePaymentLine(lineUuid) {
        const line = this.currentOrder.getPaymentlineByUuid(lineUuid);
        // Payments made with the Viva app are not known by the terminal, there is
        // nothing to cancel there.
        if (this.vivaApp.use(line.payment_method_id)) {
            this.currentOrder.removePaymentline(line);
            return;
        }
        return super.deletePaymentLine(lineUuid);
    },
    async sendPaymentRequest(line) {
        if (this.vivaApp.use(line.payment_method_id)) {
            return;
        }
        return await super.sendPaymentRequest(...arguments);
    },
    async sendPaymentCancel(line) {
        if (this.vivaApp.use(line.payment_method_id)) {
            return;
        }
        return await super.sendPaymentCancel(...arguments);
    },
});
