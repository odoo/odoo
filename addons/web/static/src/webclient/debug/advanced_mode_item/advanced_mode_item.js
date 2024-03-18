/** @odoo-module **/

import { Component } from "@odoo/owl";
import { useFeatures } from "@web/core/features";
import { registry } from "@web/core/registry";

export class AdvancedModeItem extends Component {
    static template = "web.DebugMenu.AdvancedModeItem";
    static props = {};
    setup() {
        this.features = useFeatures();
    }
    toggleMode() {
        this.features.advanced = !this.features.advanced;
    }
}

export function advancedModeItem() {
    return {
        type: "component",
        Component: AdvancedModeItem,
        sequence: 510,
    };
}
registry.category("debug").category("default").add("advancedModeItem", advancedModeItem);
