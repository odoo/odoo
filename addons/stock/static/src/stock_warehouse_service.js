import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { UPDATE_METHODS } from "@web/core/orm_plugin";
import { rpcBus } from "@web/core/network/rpc";

registry.category("services").add("stock_warehouse", {
    dependencies: ["action", "bus_service"],
    start(env, { action, bus_service }) {
        rpcBus.addEventListener("RPC:RESPONSE", (ev) => {
            rpcBus.trigger("CLEAR-CACHES", "stock.warehouse");
            const controller = action.currentController;
            const viewType = controller?.view?.type;

            const { data, error } = ev.detail;
            const { model, method } = data.params;
            if (!error && model === "stock.warehouse") {                
                if (UPDATE_METHODS.includes(method) && !browser.localStorage.getItem("running_tour") && viewType === "form") { 
                    action.doAction("reload_context");
                }
            }
        });
    }
});