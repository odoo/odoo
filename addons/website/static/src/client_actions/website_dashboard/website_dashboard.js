/** @odoo-module **/
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { Layout } from "@web/search/layout";
import { Component, useEffect, useState } from "@odoo/owl";
import { KeepLast } from "@web/core/utils/concurrency";
import { DocumentationLink } from "@web/views/widgets/documentation_link/documentation_link";

class WebsiteDashboard extends Component {
    static template = "website.WebsiteDashboardMain";
    static components = { Layout, DocumentationLink };
    static props = ["*"];
    setup() {
        super.setup();
        this.keepLast = new KeepLast();

        this.state = useState({
            website: false,
            groups: {},
            websites: [],
            dashboards: {},
        });

        useEffect(
            () => {
                this.fetchData();
            },
            () => [this.state.website]
        );
    }

    get display() {
        return {
            controlPanel: {},
        };
    }

    async fetchData() {
        const dashboardData = await this.keepLast.add(
            rpc("/website/fetch_dashboard_data", {
                website_id: this.state.website,
            })
        );
        Object.assign(this.state, dashboardData);
    }
}

registry.category("actions").add("backend_dashboard", WebsiteDashboard);
