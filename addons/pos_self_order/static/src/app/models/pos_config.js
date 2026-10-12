import { PosConfig } from "@point_of_sale/app/models/pos_config";
import { patch } from "@web/core/utils/patch";

patch(PosConfig.prototype, {
    get displayBigTrackingNumber() {
        return true;
    },

    get serviceAtTable() {
        return (
            this.self_ordering_service_mode === "table" ||
            this.self_ordering_service_mode === "dynamic_qr"
        );
    },
});
