import { _t } from "@web/core/l10n/translation";

import { Component, useState } from "@odoo/owl";

export class DashboardMobileSearchPanel extends Component {
    static template = "spreadsheet_dashboard.DashboardMobileSearchPanel";
    static props = {
        /**
         * (dashboardId: number) => void
         */
        onDashboardSelected: Function,
        groups: Object,
        activeDashboard: {
            type: Object,
            optional: true,
        },
    };

    setup() {
        this.state = useState({ isOpen: false });
    }

    get searchBarText() {
        return this.props.activeDashboard
            ? this.props.activeDashboard.data.name
            : _t("Choose a dashboard....");
    }

    onDashboardSelected(dashboardId) {
        this.props.onDashboardSelected(dashboardId);
        this.state.isOpen = false;
    }

    openDashboardSelection() {
        const dashboards = this.props.groups.map((group) => group.dashboards).flat();
        if (dashboards.length > 1) {
            this.state.isOpen = true;
        }
    }
}
