import { browser } from "@web/core/browser/browser";
import { rpcBus } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { UPDATE_METHODS } from "@web/core/orm_service";

// reload the page if changes are being done to `account.analytic.plan`

registry.category("services").add("reloadAnalyticPlan", {
    dependencies: ["action"],
    start(env, { action }) {
        rpcBus.addEventListener("RPC:RESPONSE", (ev) => {
            const { data, error } = ev.detail;
            const { model, method } = data.params;
            if (!error && model === "account.analytic.plan" && UPDATE_METHODS.includes(method)) {
                if (!browser.localStorage.getItem("running_tour")) {
                    action.doAction("reload_context");
                }
            }
        });
    },
});
