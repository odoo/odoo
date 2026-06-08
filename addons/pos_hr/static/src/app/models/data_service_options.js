import { DataServiceOptions } from "@point_of_sale/app/models/data_service_options";
import { patch } from "@web/core/utils/patch";

patch(DataServiceOptions.prototype, {
    get uniqueModels() {
        return [...super.uniqueModels, "hr.employee"];
    },
});
