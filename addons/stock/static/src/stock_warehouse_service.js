import { registry } from "@web/core/registry";

registry.category("services").add("stock_warehouse", {
    dependencies: ["action", "bus_service"],
    start(env, { action, bus_service }) {
        bus_service.subscribe("stock_group_sync", () => action.doAction("reload_context"));
    },
});
