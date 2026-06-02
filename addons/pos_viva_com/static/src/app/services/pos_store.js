import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    async reloadData(fullReload = false) {
        window.localStorage.removeItem("vivawallet_app_answer");
        super.reloadData(fullReload);
    },
});
