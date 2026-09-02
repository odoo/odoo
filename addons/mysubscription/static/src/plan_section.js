import { Component, computed, usePlugin, useProps, t } from "@odoo/owl";
import { DashboardPlugin } from "./dashboard_plugin";
import { useService } from "@web/core/utils/hooks";
import { DashboardBlock } from "./components/dashboard_block";
import { PlanBox } from "./components/plan_box"
import { SubscriptionDialog } from "./components/subscription_dialog";

export class PlanSection extends Component {
    static template = "mysubscription.PlanSection";
    static components = { PlanBox, DashboardBlock };

    props = useProps({
        hasSubscription: t.boolean(),
    });

    setup() {
        this.dialog = useService("dialog");
        this.dashboardState = usePlugin(DashboardPlugin).state;
        this.hasEnterpriseAccess = "enterprise_subscription" in this.env.services;

        this.hrefCommunityPlan = "https://www.odoo.com/page/editions";
    }

    hrefEnterprisePlan = computed(() => {
        return this.props.hasSubscription
            ? "https://accounts.odoo.com/my/home"
            : "https://www.odoo.com/pricing";
    });

    enterprisePlanButtons = computed(() => {
        if (this.props.hasSubscription && this.hasEnterpriseAccess) {
            return [
                {
                    text: "My Account",
                    class: "btn-primary",
                    href: this.hrefEnterprisePlan(),
                },
                {
                    text: "Subscription",
                    class: "btn-secondary",
                    onClick: () => this.openSubscriptionDialog(),
                },
            ]
        } else {
            return [{
                text: "Switch",
                class: "btn-primary",
                href: this.hrefEnterprisePlan(),
            }];
        }
    });

    communityPlanProps = computed(() => {
        return {
            id: "community",
            title: "Odoo Community",
            price: "Free",
            hasSubscription: this.props.hasSubscription,
            buttons: [{
                text: "Compare",
                class: "btn-secondary",
                href: this.hrefCommunityPlan,
            }],
            content: {
                subtitle: "Open Source Apps",
                addons: [],
            },
            onClickPlan: () =>  window.open(this.hrefCommunityPlan, "_blank"),
        };
    });

    enterprisePlanProps = computed(() => {
        return {
            id: "enterprise",
            title: "Odoo Enterprise",
            hasSubscription: this.props.hasSubscription,
            buttons: this.enterprisePlanButtons(),
            content: {
                subtitle: "Open Source Apps +",
                addons: [
                    { category: "Finance", apps: "Accounting, Documents" },
                    { category: "Services", apps: "Field Service" },
                    { category: "Logistic", apps: "Barcode, Shop Floor, PLM, Quality" },
                    { category: "HR", apps: "Referrals, Appraisals" },
                    { category: "Marketing", apps: "Automation, Social" },
                    { category: "Productivity", apps: "AI, Sign, ESG, Timesheets" },
                    { category: "Studio" },
                ],
            },
            onClickPlan: () =>  window.open(this.hrefEnterprisePlan(), "_blank"),
        };
    });

    openSubscriptionDialog() {
        this.dialog.add(SubscriptionDialog, {
            placeholder: this.dashboardState.enterpriseCode,
        });
    }
}
