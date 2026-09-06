import { Component, computed, usePlugin, useProps, t } from "@odoo/owl";
import { DashboardPlugin } from "../dashboard_plugin";

export class PlanBox extends Component {
    static template = "mysubscription.PlanBox";

    props = useProps({
        id: t.string(),
        title: t.string(),
        price: t.string().optional(""),
        hasSubscription: t.boolean(),
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
        this.dashboardState = usePlugin(DashboardPlugin).state;
    };

    isCurrentPlan = computed(() => {
        const currentPlan = this.props.hasSubscription
            ? "enterprise"
            : "community";
        return this.props.id === currentPlan;
    });

    showPlanButton = computed(() => {
        return this.props.id === "community" ? this.props.hasSubscription : true;
    });

    get price() {
        return this.props.price ?? "";
    }
}
