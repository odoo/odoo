import { PosRouterPlugin } from "@point_of_sale/app/plugins/pos_router_plugin";
import { patch } from "@web/core/utils/patch";

patch(PosRouterPlugin.prototype, {
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
