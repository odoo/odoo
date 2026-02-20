import { patch } from "@web/core/utils/patch";
import { DataServiceOptions } from "@point_of_sale/app/models/data_service_options";

patch(DataServiceOptions.prototype, {
    get dynamicModels() {
        const models = super.dynamicModels;
        return ["pos.pack.operation.lot", ...models];
    },

    get cascadeDeleteModels() {
        const models = super.cascadeDeleteModels;
        return ["pos.pack.operation.lot", ...models];
    },
});
