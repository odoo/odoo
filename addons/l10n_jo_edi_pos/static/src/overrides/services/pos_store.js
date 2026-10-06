import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    /**
     * @override
     */
    useBackendOrderView() {
        return this.config.company_id.country_id.code === "JO" || super.useBackendOrderView();
    },
});
