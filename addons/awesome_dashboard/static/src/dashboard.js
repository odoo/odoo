import { Layout } from "@web/search/layout";
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Counter } from "./counter";
import { DashboardItem } from "./dashboard_item";

class AwesomeDashboard extends Component {
    static template = "awesome_dashboard.AwesomeDashboard";
    static components = { Layout, Counter, DashboardItem };
}

registry.category("actions").add("awesome_dashboard.dashboard", AwesomeDashboard);
