import { PosRouterPlugin } from "@point_of_sale/app/plugins/pos_router_plugin";
import { patch } from "@web/core/utils/patch";

patch(PosRouterPlugin.prototype, {
    get openOrder() {
        if (this.config.module_pos_restaurant) {
            return (
                this.config.models["pos.order"].find(
                    (o) => o.state === "draft" && o.isDirectSale
                ) || window.posmodel?.addNewOrder()
            );
        }
        return super.openOrder;
    },
    get defaultPage() {
        if (this.config.module_pos_restaurant && this.config.default_screen === "tables") {
            return {
                page: "FloorScreen",
                params: {},
            };
        }
        return super.defaultPage;
    },
});
