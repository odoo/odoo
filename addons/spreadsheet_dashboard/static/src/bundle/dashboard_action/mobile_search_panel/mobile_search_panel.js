import { _t } from "@web/core/l10n/translation";

import { Component, proxy, t, useProps } from "@odoo/owl";

export class DashboardMobileSearchPanel extends Component {
    static template = "spreadsheet_dashboard.DashboardMobileSearchPanel";

    props = useProps({
        activeDashboard: t.object().optional(),
        groups: t.array(t.object()),
        onDashboardSelected: t.function([t.number()]),
    });

    setup() {
        this.state = proxy({ isOpen: false });
    }

    get searchBarText() {
        return this.props.activeDashboard
            ? this.props.activeDashboard.data.name
            : _t("Choose a dashboard....");
    }

    /**
     * @param {number} dashboardId
     */
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
