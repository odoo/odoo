import { Component, onWillStart, proxy } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useChart } from "@web/core/utils/chart_hook";
import { getColor } from "@web/core/colors/colors";
import { FleetStatCard } from "./stat_card/stat_card";

export class FleetDashboard extends Component {
    static template = "fleet_training.FleetDashboard";
    static components = { FleetStatCard };

    setup() {
        this.dashboardData = useService("fleet_dashboard_data");
        this.state = proxy({
            total: 0,
            available: 0,
            assigned: 0,
            maintenance: 0,
            expiring_insurance: 0,
            total_maintenance_cost: 0,
            by_category: [],
        });
        this.chart = useChart(() => this.getChartConfig());
        onWillStart(async () => this.loadStats());
    }

    async loadStats() {
        const stats = await this.dashboardData.getStats();
        Object.assign(this.state, stats);
    }

    getChartConfig() {
        return {
            type: "pie",
            data: {
                labels: this.state.by_category.map((c) => c.name),
                datasets: [
                    {
                        data: this.state.by_category.map((c) => c.count),
                        backgroundColor: this.state.by_category.map((c, i) => getColor(i)),
                    },
                ],
            },
            options: {
                maintainAspectRatio: false,
            },
        };
    }
}

registry.category("actions").add("fleet_training.fleet_dashboard", FleetDashboard);
