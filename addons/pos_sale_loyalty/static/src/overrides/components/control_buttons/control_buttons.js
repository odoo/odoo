import { patch } from "@web/core/utils/patch";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";

patch(ControlButtons.prototype, {
    getPotentialRewards() {
        if (this.pos.getOrder().uiState._isSettlingSO) {
            return [];
        }
        return super.getPotentialRewards();
    },
});
