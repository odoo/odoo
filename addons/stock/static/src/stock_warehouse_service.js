/** @odoo-module **/

import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { UPDATE_METHODS } from "@web/core/orm_service";

registry.category("services").add("stock_warehouse", {
    dependencies: ["action"],
    start(env, { action }) {
        env.bus.addEventListener("RPC:RESPONSE", (ev) => {
            const { data, error } = ev.detail;
            const { model, method } = data.params;
            if (!error && model === "stock.warehouse") {
                if (UPDATE_METHODS.includes(method) && !browser.localStorage.getItem("running_tour")) {
                    action.doAction("reload_context");
                }
            }
        });
    },
});
