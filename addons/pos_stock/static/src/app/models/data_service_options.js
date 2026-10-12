import { patch } from "@web/core/utils/patch";
import { DataServiceOptions } from "@point_of_sale/app/models/data_service_options";

patch(DataServiceOptions.prototype, {
    get dynamicModels() {
        return ["pos.pack.operation.lot", ...super.dynamicModels];
    },

    get cascadeDeleteModels() {
        return ["pos.pack.operation.lot", ...super.cascadeDeleteModels];
    },
});
