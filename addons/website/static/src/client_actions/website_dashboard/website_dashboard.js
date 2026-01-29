/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Layout } from "@web/search/layout";
import { Component, useEffect, useState } from "@odoo/owl";
import { KeepLast } from "@web/core/utils/concurrency";

class WebsiteDashboard extends Component {
    setup() {
        super.setup();
        this.rpc = useService("rpc");
        this.userService = useService("user");
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
            this.rpc("/website/fetch_dashboard_data", {
                website_id: this.state.website,
            })
        );
        Object.assign(this.state, dashboardData);
    }
}
WebsiteDashboard.template = "website.WebsiteDashboardMain";
WebsiteDashboard.components = { Layout };

registry.category("actions").add("backend_dashboard", WebsiteDashboard);
