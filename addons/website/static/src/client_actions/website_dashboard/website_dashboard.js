import { useLayoutEffect } from "@web/owl2/utils";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { Layout } from "@web/search/layout";
import { Component, proxy } from "@odoo/owl";
import { KeepLast } from "@web/core/utils/concurrency";
import { DocumentationLink } from "@web/views/widgets/documentation_link/documentation_link";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

const MAX_VISIBLE_WEBSITES = 8;

class WebsiteDashboard extends Component {
    static template = "website.WebsiteDashboardMain";
    static components = { Layout, DocumentationLink, Dropdown, DropdownItem };

    setup() {
        super.setup();
        this.keepLast = new KeepLast();

        this.state = proxy({
            website: false,
            groups: {},
            websites: [],
            dashboards: {},
        });

        useLayoutEffect(
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

    /**
     * Websites shown as buttons. The selected website is always visible, even
     * if it would otherwise be part of the overflow dropdown.
     */
    get visibleWebsites() {
        const websites = this.state.websites;
        if (websites.length <= MAX_VISIBLE_WEBSITES) {
            return websites;
        }
        const visible = websites.slice(0, MAX_VISIBLE_WEBSITES);
        const selected = websites.find((website) => website.selected);
        if (selected && !visible.includes(selected)) {
            visible[MAX_VISIBLE_WEBSITES - 1] = selected;
        }
        return visible;
    }

    get hiddenWebsites() {
        const visible = this.visibleWebsites;
        return this.state.websites.filter((website) => !visible.includes(website));
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
