/** @odoo-module **/
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Layout } from "@web/search/layout";
import { Component, useEffect, useState } from "@odoo/owl";
import { KeepLast } from "@web/core/utils/concurrency";

class WebsiteDashboard extends Component {
    static template = "website.WebsiteDashboardMain";
    static components = { Layout };
    setup() {
        super.setup();
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
            rpc("/website/fetch_dashboard_data", {
                website_id: this.state.website,
            })
        );
        Object.assign(this.state, dashboardData);
    }
}

registry.category("actions").add("backend_dashboard", WebsiteDashboard);
