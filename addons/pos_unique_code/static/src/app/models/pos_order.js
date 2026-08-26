import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    initState() {
        super.initState();
        // Set once a one-time code has been consumed (or the cashier forced the
        // validation) so a retry never burns a second code.
        this.uiState.uniqueCodeValidated = false;
    },
});
