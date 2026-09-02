import { Component, onWillStart, providePlugins, usePlugin } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { PlanSection } from "./plan_section";
import { DatabaseSection } from "./database_section";
import { IapSection } from "./iap_section";
import { DashboardPlugin } from "./dashboard_plugin";
import { MySubscriptionNavBar } from "./components/navbar";

const { DateTime } = luxon;

export class MySubscriptionDashboard extends Component {
    static template = "mysubscription.Dashboard";
    static target = "fullscreen";
    static components = {
        PlanSection,
        DatabaseSection,
        IapSection,
        MySubscriptionNavBar,
    };

    setup() {
        this.orm = useService("orm");

        providePlugins([DashboardPlugin]);
        this.dashboardState = usePlugin(DashboardPlugin).state;

        onWillStart(async () => {
            const data = await this.loadSubscription();
            this.dashboardState.enterpriseCode = data.enterprise_code;
            this.dashboardState.baseUrl = data.base_url;
            this.dashboardState.expirationReason = data.expiration_reason;

            // If the subscription expires, the enterprise_code will still be available.
            // We need to have both a future expiration_date and an enterprise_code to
            // qualify the database as having a subscription.
            if (data.enterprise_code && data.expiration_date) {
                const parsedDate = DateTime.fromSQL(data.expiration_date);
                this.dashboardState.expirationDate = parsedDate.toLocaleString(DateTime.DATE_FULL);
                this.hasSubscription = (parsedDate > DateTime.now());
            }
            else {
                this.dashboardState.expirationDate = null;
                this.hasSubscription = false;
            }

            this.iapAccounts = await this.loadIap();
        });
    }

    // Fetches expiration date and reason, base_url, is the user an admin and enterprise code
    async loadSubscription() {
        const configData = await this.orm.call(
            "mysubscription.mysubscription",
            "get_dashboard_data",
            []
        );
        return configData;
    }

    async loadIap() {
        const configData = await this.orm.call(
            "mysubscription.mysubscription",
            "get_iap_data",
            []
        );
        return configData;
    }
}

registry.category("actions").add("mysubscription.dashboard", MySubscriptionDashboard);
