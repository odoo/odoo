/** @odoo-module */

import { registry } from "@web/core/registry";

function runPoSJSTests({ env }) {
    return {
        type: "item",
        description: env._t("Run Point of Sale JS Tests"),
        callback: () => {
            env.services.action.doAction({
                name: env._t("JS Tests"),
                target: "new",
                type: "ir.actions.act_url",
                url: "/pos/ui/tests?debug=assets",
            });
        },
        sequence: 35,
    };
}

registry.category("debug").category("default").add("point_of_sale.runPoSJSTests", runPoSJSTests);
