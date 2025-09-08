import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Counter } from "./counter";

class AwesomeDashboard extends Component {
    static template = "awesome_dashboard.AwesomeDashboard";
    static components = { Counter };
}

registry.category("actions").add("awesome_dashboard.dashboard", AwesomeDashboard);
