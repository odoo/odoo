import { Component, signal, proxy, plugin, props, types as t } from "@odoo/owl";
import { DashboardPlugin } from "./dashboard_plugin";
import { useService } from "@web/core/utils/hooks";
import { DashboardBlock } from "./components/dashboard_block";
import { PlanBox } from "./components/plan_box"
import { SubscriptionDialog } from "./components/subscription_dialog";

export class PlanSection extends Component {
    static template = "mysubscription.PlanSection";
    static components = { PlanBox, DashboardBlock };

    props = props({
        hasSubscription: t.boolean(),
    });

    setup() {
        this.subscription = useService("enterprise_subscription");
        this.dialog = useService("dialog");
        this.inputRef = signal(null);
        this.state = proxy({buttonText: "Submit"});
        this.dashboardState = plugin(DashboardPlugin).state;

        this.hrefCommunityPlan = "https://www.odoo.com/page/editions";
    }

    get hrefEnterprisePlan() {
        return this.dashboardState.hasSubscription
            ? "https://accounts.odoo.com/my/home"
            : "https://www.odoo.com/pricing";
    }

    get enterprisePlanButtons() {
        if (this.dashboardState.hasSubscription) {
            return [
                {
                    text: "Subscription",
                    class: "btn-primary",
                    onClick: () => this.openSubscriptionDialog(),
                },
                {
                    text: "My Account",
                    class: "btn-primary",
                    href: this.hrefEnterprisePlan,
                },
            ]
        } else {
            return [{
                text: "Switch",
                class: "btn-primary",
                href: this.hrefEnterprisePlan,
            }];
        }
    }

    get communityPlanProps() {
        return {
            id: "community",
            title: "Odoo Community",
            price: "Free",
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
    }

    get enterprisePlanProps() {
        return {
            id: "enterprise",
            title: "Odoo Enterprise",
            buttons: this.enterprisePlanButtons,
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
            onClickPlan: () =>  window.open(this.hrefEnterprisePlan, "_blank"),
        };
    }

    openSubscriptionDialog() {
        this.dialog.add(SubscriptionDialog, {});
    }
}
