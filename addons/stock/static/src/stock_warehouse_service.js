import { rpcBus } from "@web/core/network/rpc";
import { UPDATE_METHODS } from "@web/core/orm_plugin";
import { registry } from "@web/core/registry";

registry.category("services").add("stock_warehouse", {
    dependencies: ["action", "bus_service", "ui"],
    start(env, { action, bus_service, ui }) {
        // Reload after the save outside of a dialog
        const reloadAfterSave = (ev) => {
            const { data, error } = ev.detail;
            if (
                !error &&
                UPDATE_METHODS.includes(data.params.method) &&
                ui.activeElement === document
            ) {
                rpcBus.removeEventListener("RPC:RESPONSE", reloadAfterSave);
                action.doAction("reload_context");
            }
        };
        bus_service.subscribe("stock_group_sync", () => {
            if (ui.activeElement === document) {
                action.doAction("reload_context");
            } else {
                rpcBus.addEventListener("RPC:RESPONSE", reloadAfterSave);
            }
        });
    },
});
