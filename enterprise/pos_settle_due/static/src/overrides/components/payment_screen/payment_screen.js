import { _t } from "@web/core/l10n/translation";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { floatIsZero } from "@web/core/utils/numbers";
import { ask } from "@point_of_sale/app/store/make_awaitable_dialog";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { onWillUnmount } from "@odoo/owl";

patch(PaymentScreen.prototype, {
    //@Override
    setup() {
        super.setup(...arguments);
        onWillUnmount(this.onUnmount);
    },

    onUnmount() {
        /*
         * When the settlement payment selection dialog is opened,
         * `is_settling_account` is temporarily set to true.
         *
         * However, if the user exits the settlement process
         * (without completing the payment) and returns to the previous screen,
         * we must reset this flag to false.
         *
         * Failing to do so allows the same order to be used for
         * non-settlement operations, which can cause inconsistencies—
         * particularly in cases where invoices are mandatory
         * for all payments except settlements.
         */
        if (this.currentOrder?.is_settling_account && this.currentOrder.state !== "paid") {
            this.currentOrder.is_settling_account = false;
        }
    },

    toggleIsToInvoice() {
        if (
            !this.currentOrder.is_to_invoice() &&
            this.currentOrder.is_settling_account &&
            this.currentOrder.lines.length === 0
        ) {
            this.dialog.add(AlertDialog, {
                title: _t("Empty Order"),
                body: _t("Empty orders cannot be invoiced."),
            });
        } else {
            super.toggleIsToInvoice();
        }
    },
    get partnerInfos() {
        const order = this.currentOrder;
        return this.pos.getPartnerCredit(order.get_partner());
    },
    get highlightPartnerBtn() {
        const order = this.currentOrder;
        const partner = order.get_partner();
        return (!this.partnerInfos.useLimit && partner) || (!this.partnerInfos.overDue && partner);
    },
    //@override
    async validateOrder(isForceValidate) {
        const order = this.currentOrder;
        const change = order.get_change();
        const paylaterPaymentMethod = this.pos.models["pos.payment.method"].find(
            (pm) =>
                this.pos.config.payment_method_ids.some((m) => m.id === pm.id) &&
                pm.type === "pay_later"
        );
        const existingPayLaterPayment = order.payment_ids.find(
            (payment) => payment.payment_method_id.type == "pay_later"
        );
        if (
            order.get_orderlines().length === 0 &&
            paylaterPaymentMethod &&
            !existingPayLaterPayment
        ) {
            if (floatIsZero(change, this.pos.currency.decimal_places)) {
                this.dialog.add(AlertDialog, {
                    title: _t("The order is empty"),
                    body: _t("You can not deposit zero amount."),
                });
                return;
            }
            const partner = order.get_partner();
            if (partner) {
                const confirmed = await ask(this.dialog, {
                    title: _t("The order is empty"),
                    body: _t(
                        "Do you want to deposit %s to %s?",
                        this.env.utils.formatCurrency(change),
                        order.get_partner().name
                    ),
                    confirmLabel: _t("Yes"),
                });
                if (confirmed) {
                    const paylaterPayment = order.add_paymentline(paylaterPaymentMethod);
                    paylaterPayment.set_amount(-change);
                    return super.validateOrder(...arguments);
                }
            } else {
                const confirmed = await ask(this.dialog, {
                    title: _t("The order is empty"),
                    body: _t(
                        "Do you want to deposit %s to a specific customer? If so, first select him/her.",
                        this.env.utils.formatCurrency(change)
                    ),
                    confirmLabel: _t("Yes"),
                });
                if (confirmed && this.pos.selectPartner()) {
                    const paylaterPayment = order.add_paymentline(paylaterPaymentMethod);
                    paylaterPayment.set_amount(-change);
                    return super.validateOrder(...arguments);
                }
            }
        } else {
            return super.validateOrder(...arguments);
        }
    },
    async afterOrderValidation(suggestToSync = false) {
        await super.afterOrderValidation(...arguments);
        const hasCustomerAccountAsPaymentMethod = this.currentOrder.payment_ids.find(
            (paymentline) => paymentline.payment_method_id.type === "pay_later"
        );
        const partner = this.currentOrder.get_partner();
        if (hasCustomerAccountAsPaymentMethod && partner.total_due !== undefined) {
            this.pos.refreshTotalDueOfPartner(partner);
        }
    },
});
