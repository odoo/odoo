import { Component, plugin, props, types as t } from "@odoo/owl";
import { DashboardPlugin } from "../dashboard_plugin";

export class PlanBox extends Component {
    static template = "mysubscription.PlanBox";

    props = props({
        id: t.string(),
        title: t.string(),
        price: t.string().optional(""),
        buttons: t.array(t.object({
            class: t.string(),
            text: t.string(),
            href: t.string().optional(),
            onClick: t.function().optional(),
        })),
        content: t.object({
            subtitle: t.string(),
            addons: t.array(t.object({
                category: t.string(),
                apps: t.string().optional(),
            })).optional([]),
        }),
        onClickPlan: t.function(),
    });

    setup() {
        this.dashboardState = plugin(DashboardPlugin).state;
    };

    get isCurrentPlan() {
        const currentPlan = this.dashboardState.hasSubscription
            ? "enterprise"
            : "community";
        return this.props.id === currentPlan;
    }

    get showPlanButton() {
        return this.props.id === "community" ? this.dashboardState.hasSubscription : true;
    }

    get price() {
        return this.props.price ?? "";
    }
}
