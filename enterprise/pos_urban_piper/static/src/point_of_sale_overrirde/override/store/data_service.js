import { PosData } from "@point_of_sale/app/models/data_service";
import { patch } from "@web/core/utils/patch";

patch(PosData.prototype, {
    /**
     * @override
     */
    async preLoadData(data) {
        const loadData = await super.preLoadData(data);
        const config = this.models["pos.config"].getFirst();
        if (!config.module_pos_urban_piper || !config.urbanpiper_store_identifier) {
            return loadData;
        }
        if (loadData["pos.order"]) {
            loadData["pos.order"] = loadData["pos.order"].filter((o) => !o.delivery_identifier);
        }
        if (loadData["pos.order.line"]) {
            loadData["pos.order.line"] = loadData["pos.order.line"].filter(
                (ol) => ol.order_id && !ol.order_id.delivery_identifier
            );
        }
        return loadData;
    },
});
