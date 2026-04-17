import { Component, signal, proxy, plugin, props, types as t } from "@odoo/owl";
import { DashboardPlugin } from "./dashboard_plugin";
import { useService } from "@web/core/utils/hooks";
import { DashboardBlock } from "./components/dashboard_block";
import { PlanBox } from "./components/plan_box"

export class PlanSection extends Component {
    static template = "mysubscription.PlanSection";
    static components = { PlanBox, DashboardBlock };

    props = props({
        hasSubscription: t.boolean(),
    });

    setup() {
        this.subscription = useService("enterprise_subscription");
        this.inputRef = signal(null);
        this.state = proxy({buttonText: "Submit"});
        this.dashboardState = plugin(DashboardPlugin).state;
    }

    get enterprisePlanButton() {
        return this.dashboardState.hasSubscription
            ? { href: "https://accounts.odoo.com/my/home", text: "View" }
            : { href: "https://www.odoo.com/pricing", text: "Upgrade" }
    }

    get communityPlan() {
        return {
            id: "community",
            title: "Odoo Community",
            price: "Free",
            isEnterprise: false,
            content: {
                subtitle: "Open Source Apps",
                addons: [],
            }
        };
    }

    get enterprisePlan() {
        return {
            id: "enterprise",
            title: "Odoo Enterprise",
            price: "46.80€",
            button: this.enterprisePlanButton,
            isEnterprise: true,
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
            }
        };
    }

    async onCodeSubmit() {
        const enterpriseCode = this.inputRef().value;
        if (!enterpriseCode) {
            return;
        }
        await this.subscription.submitCode(enterpriseCode);
        if (this.subscription.lastRequestStatus === "success") {
            console.log("SUCCESS");
        } else {
            console.log("NOT A SUCCESS");
            this.state.buttonText = "Retry";
        }
    }

    showSubscriptionCode() {
        return this.dashboardState.selectedPlan === "enterprise";
    }
}
