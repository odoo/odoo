import { Component, Portal, proxy } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class DashboardMobileSearchPanel extends Component {
    static template = "spreadsheet_dashboard.DashboardMobileSearchPanel";
    static components = { Portal };
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
        this.state = proxy({ isOpen: false });
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
