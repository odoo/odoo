import { Component, effect, plugin, props, types as t } from "@odoo/owl";
import { DashboardPlugin } from "../dashboard_plugin";

export class PlanBox extends Component {
    static template = "mysubscription.PlanBox";

    props = props({
        data: t.object(),
    });

    setup() {
        this.dashboardState = plugin(DashboardPlugin).state;
    };

    get isCurrentPlan() {
        const currentPlan = this.dashboardState.hasSubscription
            ? "enterprise"
            : "community";
        return this.props.data.id === currentPlan;
    }

    get showPlanButton() {
        return this.props.data.id === "community" ? this.dashboardState.hasSubscription : true;
    }
}
