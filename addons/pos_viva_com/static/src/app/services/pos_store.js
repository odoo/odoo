import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.data.connectWebSocket("VIVA_COM_LATEST_RESPONSE", () => {
            const pendingLine = this.getPendingPaymentLine("viva_com");

            if (pendingLine) {
                pendingLine.payment_method_id.payment_terminal.handleVivaComStatusResponse();
            }
        });
    },
});
