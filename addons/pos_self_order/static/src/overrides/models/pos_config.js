import { PosConfig } from "@point_of_sale/app/models/pos_config";
import { patch } from "@web/core/utils/patch";

patch(PosConfig.prototype, {
    get isShareable() {
        return super.isShareable || this.module_pos_restaurant;
    },
    get useDynamicQr() {
        return (
            this.module_pos_restaurant &&
            this.self_ordering_mode === "mobile" &&
            this.self_ordering_service_mode === "dynamic_qr"
        );
    },
});
