import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.data.connectWebSocket("SQUARE_LATEST_RESPONSE", (data) => {
            const pendingLine = this.getPendingPaymentLine("square");

            if (pendingLine) {
                pendingLine.payment_method_id.payment_terminal.handleSquareStatusResponse(data);
            }
        });
    },
});
