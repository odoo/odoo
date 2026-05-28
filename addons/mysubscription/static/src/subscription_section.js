import { _t } from "@web/core/l10n/translation";
import { Component, plugin } from "@odoo/owl";
import { DashboardPlugin } from "./dashboard_plugin";
import { DashboardBlock } from "./components/dashboard_block";

function capitalize(string) {
    if (string.length > 1) {
        return string.charAt(0).toUpperCase() + string.slice(1);
    } else {
        return string;
    }
}

export class SubscriptionSection extends Component {
    static template = "mysubscription.SubscriptionSection";
    static components = { DashboardBlock };
    static props;

    setup() {
        this.dashboardState = plugin(DashboardPlugin).state;
    }

    get expirationDate() {
        if (this.dashboardState.expirationDate) {
            return _t(`Expires on ${this.dashboardState.expirationDate}`);
        }
        else if (this.dashboardState.enterpriseCode) {
            return _t("Pending Validation");
        }
        else {
            return _t(`Running on ${capitalize(_t(this.dashboardState.expirationReason))}`);
        }
    }
}

