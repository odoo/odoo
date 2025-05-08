import { reactive } from "@odoo/owl";

import { registry } from "@web/core/registry";

export const busLogsService = {
    dependencies: ["bus_service", "multi_tab"],
    /**
     * @param {import("@web/env").OdooEnv}
     * @param {Partial<import("services").Services>} services
     */
    start(env, { bus_service, multi_tab }) {
        const state = reactive({
            enabled: multi_tab.getSharedValue("bus_log_menu.enabled", false),
            toggleLogging() {
                state.enabled = !state.enabled;
                bus_service.setLoggingEnabled(state.enabled);
                multi_tab.setSharedValue("bus_log_menu.enabled", state.enabled);
            },
        });
        multi_tab.bus.addEventListener("shared_value_updated", ({ detail }) => {
            if (detail.key === "bus_log_menu.enabled") {
                state.enabled = JSON.parse(detail.newValue);
            }
        });
        bus_service.setLoggingEnabled(state.enabled);
        odoo.busLogging = {
            stop: () => state.enabled && state.toggleLogging(),
            start: () => !state.enabled && state.toggleLogging(),
            download: () => bus_service.downloadLogs(),
        };
        if (state.enabled) {
            console.log(
                "Bus logging is enabled. To disable it, use `odoo.busLogging.stop()`. To download the logs, use `odoo.busLogging.download()`."
            );
        }
        return state;
    },
};

registry.category("services").add("bus.logs_service", busLogsService);
