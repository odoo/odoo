/** @odoo-module **/

import { registry } from "@web/core/registry";
import { TechnicalItem } from "./advanced_item";
import { reactive } from "@odoo/owl";

export const advancedService = {
    start(env) {
        function technicalItem() {
            return {
                type: "component",
                Component: TechnicalItem,
                sequence: 510,
            };
        }
        registry.category("debug").category("default").add("technicalItem", technicalItem);

        return reactive({ active: !!env.debug });
    },
};

registry.category("services").add("advanced", advancedService);
