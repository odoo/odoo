import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    setup() {
        super.setup(...arguments);
        this.uiState = {
            ...this.uiState,
            shadowTableName: "",
        };
    },
    get shadowTableName() {
        return this.uiState.shadowTableName || this.tracking_number;
    },
});
