import { Component } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { useService } from "@web/core/utils/hooks";

export class EatingLocationPage extends Component {
    static template = "pos_self_order.EatingLocationPage";
    static props = {};

    setup() {
        this.selfOrder = useSelfOrder();
        this.router = useService("router");
    }

    back() {
        this.router.navigate("default");
    }

    selectPreset(preset) {
        this.selfOrder.currentOrder.setPreset(preset);
        this.router.navigate("product_list");
    }

    get presets() {
        return this.selfOrder.models["pos.preset"].getAll();
    }
}
