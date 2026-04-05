/** @odoo-module **/
import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class ShowcaseCrmDashboard extends Component {
    static template = "odx_owl.ShowcaseCrmDashboard";
    static props = { "*": true };
    setup() {
        this.state = useState({ period: "month" });
    }
    setPeriod(p) { this.state.period = p; }
}

registry.category("actions").add("odx_showcase_crm_dashboard", ShowcaseCrmDashboard);
