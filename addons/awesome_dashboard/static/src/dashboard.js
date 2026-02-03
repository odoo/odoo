import { Layout } from "@web/search/layout";
import { Component, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { DashboardItem } from "./dashboard_item";
import { rpc } from "@web/core/network/rpc";
import { PieChart } from "./pie_chart";
import { useService } from "@web/core/utils/hooks";

class AwesomeDashboard extends Component {
    static template = "awesome_dashboard.AwesomeDashboard";
    static components = { Layout, DashboardItem, PieChart };

    setup() {
        this.statistics = false;
        this.statistics = useService("awesome_dashboard.statistics");


        onWillStart(async () => {
            this.statistics = await rpc("/awesome_dashboard/statistics");
        });
    }
}

registry.category("actions").add("awesome_dashboard.dashboard", AwesomeDashboard);
