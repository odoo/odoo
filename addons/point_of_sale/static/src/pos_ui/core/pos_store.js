/** @odoo-module */

import Registries from "point_of_sale.Registries";
import { reactive } from "@odoo/owl";

export class PosStore {
    constructor({ numberBuffer }) {
        this.state = reactive({
            showDebugWidget: true,
            screen: { component: Registries.Component.get("ProductScreen") },
            tempScreen: null,
        });
        this.numberBuffer = numberBuffer;
    }

    showScreen(name, props) {
        this.screen = { component: Registries.Component.get(name), props };
    }

    toggleDebugWidget() {
        this.state.showDebugWidget = !this.state.showDebugWidget;
    }
}
