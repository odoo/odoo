import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { UniqueCodePopup } from "@pos_unique_code/app/unique_code_popup/unique_code_popup";

patch(PosStore.prototype, {
    async validateOrder(args = {}) {
        const order = args.order || this.getOrder();
        if (!(await this.askUniqueCode(order))) {
            return;
        }
        return await super.validateOrder(args);
    },

    async validateOrderFast(paymentMethod) {
        if (!(await this.askUniqueCode(this.getOrder()))) {
            return;
        }
        return await super.validateOrderFast(paymentMethod);
    },

    /**
     * Ask the customer for a one-time code before the order is validated. The
     * cashier can bypass it with "Force Validate". Once an order got through,
     * a later retry never asks for (and burns) a second code.
     *
     * @returns {boolean} whether the validation may go on
     */
    async askUniqueCode(order) {
        if (!order || order.uiState.uniqueCodeValidated) {
            return true;
        }
        const result = await makeAwaitable(this.dialog, UniqueCodePopup, {
            consume: (code) => this.consumeUniqueCode(code),
            allowForce: true,
        });
        if (!result) {
            return false;
        }
        order.uiState.uniqueCodeValidated = true;
        order.unique_code = result.code || false;
        if (result.forced) {
            this.notification.add(_t("Order validated without an order code."), {
                type: "warning",
            });
        }
        return true;
    },

    async consumeUniqueCode(code) {
        try {
            return await this.data.call("pos.unique.code", "consume_code", [code]);
        } catch {
            return { success: false, message: _t("We couldn't reach the server. Please try again.") };
        }
    },
});
