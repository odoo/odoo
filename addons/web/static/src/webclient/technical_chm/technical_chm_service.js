/** @odoo-module **/

import { registry } from "@web/core/registry";
import { TechnicalItem } from "./technical_chm_item";
import { reactive } from "@odoo/owl";

export const technicalService = {
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

registry.category("services").add("technical-chm", technicalService);
