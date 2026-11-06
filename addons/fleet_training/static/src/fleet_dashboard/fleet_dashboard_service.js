import { registry } from "@web/core/registry";

export const fleetDashboardService = {
    dependencies: ["orm"],
    start(env, { orm }) {
        let cache = null;
        return {
            async getStats(forceRefresh = false) {
                if (!cache || forceRefresh) {
                    cache = await orm.call("fleet_training.vehicle", "get_fleet_dashboard_stats", []);
                }
                return cache;
            },
        };
    },
};

registry.category("services").add("fleet_dashboard_data", fleetDashboardService);
