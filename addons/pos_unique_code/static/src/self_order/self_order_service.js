import { patch } from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { SelfOrder } from "@pos_self_order/app/services/self_order_service";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { UniqueCodePopup } from "@pos_unique_code/app/unique_code_popup/unique_code_popup";

patch(SelfOrder.prototype, {
    /**
     * Ask for a one-time code before the kiosk sends the order to the server.
     * `confirmOrder` is re-entered after the stand number page, so the code is
     * only asked once per order.
     */
    async confirmOrder() {
        if (this.kioskMode && !this.currentOrder.uiState.uniqueCodeValidated) {
            const result = await makeAwaitable(this.dialog, UniqueCodePopup, {
                consume: (code) => this.consumeUniqueCode(code),
            });
            if (!result) {
                return;
            }
            this.currentOrder.uiState.uniqueCodeValidated = true;
            this.currentOrder.unique_code = result.code || false;
        }
        return await super.confirmOrder(...arguments);
    },

    async consumeUniqueCode(code) {
        try {
            return await rpc("/pos-self-order/consume-unique-code", {
                access_token: this.access_token,
                code,
            });
        } catch {
            return { success: false, message: _t("We couldn't reach the server. Please try again.") };
        }
    },
});
