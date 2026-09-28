import { Component, onWillStart, proxy } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { FleetStatCard } from "./stat_card/stat_card";

export class FleetDashboard extends Component {
    static template = "fleet_training.FleetDashboard";
    static components = { FleetStatCard };

    setup() {
        this.orm = useService("orm");
        this.state = proxy({
            total: 0,
            available: 0,
            assigned: 0,
            maintenance: 0,
        });
        onWillStart(async () => this.loadStats());
    }

    async loadStats() {
        const stats = await this.orm.call("fleet_training.vehicle", "get_fleet_dashboard_stats", []);
        Object.assign(this.state, stats);
    }
}

registry.category("actions").add("fleet_training.fleet_dashboard", FleetDashboard);
