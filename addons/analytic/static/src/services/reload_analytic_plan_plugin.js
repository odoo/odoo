import { Plugin, useListener, usePlugin } from "@odoo/owl";
import { rpcBus } from "@web/core/network/rpc";
import { UPDATE_METHODS } from "@web/core/orm_plugin";
import { services } from "@web/core/services";
import { ActionPlugin } from "@web/webclient/actions/action_plugin";

// reload the page if changes are being done to `account.analytic.plan`

export class ReloadAnalyticPlanPlugin extends Plugin {
    action = usePlugin(ActionPlugin);

    setup() {
        useListener(rpcBus, "RPC:RESPONSE", (ev) => {
            const { data, error } = ev.detail;
            const { model, method } = data.params;
            if (!error && model === "account.analytic.plan" && UPDATE_METHODS.includes(method)) {
                if (!window.localStorage.getItem("running_tour")) {
                    this.action.doAction("reload_context");
                }
            }
        });
    }
}

services.add(ReloadAnalyticPlanPlugin);
