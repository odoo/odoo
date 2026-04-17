import { Component, plugin, props, types as t } from "@odoo/owl";
import { DashboardPlugin } from "../dashboard_plugin";

export class PlanBox extends Component {
    static template = "mysubscription.PlanBox";

    props = props({
        data: t.object(),
    });

    setup() {
        this.dashboardState = plugin(DashboardPlugin).state;
    };

    onClickPlan() {
        this.dashboardState.selectedPlan = this.props.data.id;
    }

    get isCurrentPlanSelected() {
        return this.dashboardState.selectedPlan === this.props.data.id;
    }
}
