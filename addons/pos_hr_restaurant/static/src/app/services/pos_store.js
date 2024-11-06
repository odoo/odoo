import { patch } from "@web/core/utils/patch";
import "@pos_restaurant/app/services/pos_store";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    shouldResetIdleTimer() {
        return this.mainScreen?.name !== "LoginScreen" && super.shouldResetIdleTimer(...arguments);
    },
});
