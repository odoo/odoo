import { Layout } from "@web/search/layout";
import { Component, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { DashboardItem } from "./dashboard_item";
import { rpc } from "@web/core/network/rpc";

class AwesomeDashboard extends Component {
    static template = "awesome_dashboard.AwesomeDashboard";
    static components = { Layout, DashboardItem };

    setup() {
        this.statistics = false;
        onWillStart(async () => {
            this.statistics = await rpc("/awesome_dashboard/statistics");
        });
    }
}

registry.category("actions").add("awesome_dashboard.dashboard", AwesomeDashboard);
