import { Component, onWillStart, providePlugins, plugin } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { SubscriptionSection } from "./subscription_section";
import { PlanSection } from "./plan_section";
import { DatabaseSection } from "./database_section";
import { AddressSection } from "./address_section";
import { IapSection } from "./iap_section";
import { DashboardPlugin } from "./dashboard_plugin";

const { DateTime } = luxon;

export class MySubscriptionDashboard extends Component {
    static template = "mysubscription.Dashboard";
    static components = {
        SubscriptionSection,
        AddressSection,
        PlanSection,
        DatabaseSection,
        IapSection,
    };
    static props;

    setup() {
        this.orm = useService("orm");

        providePlugins([DashboardPlugin]);
        this.dashboard = plugin(DashboardPlugin);
        this.state = this.dashboard.state;

        onWillStart(async () => {
            const data = await this.loadSubscription();
            this.state.enterpriseCode = data.enterprise_code;
            this.state.baseUrl = data.base_url;
            this.state.expirationReason = data.expiration_reason;

            // If the subscription expires, the enterprise_code will still be available.
            // We need to have both a future expiration_date and an enterprise_code to
            // qualify the database as having a subscription.
            if (data.enterprise_code && data.expiration_date) {
                const parsedDate = DateTime.fromSQL(data.expiration_date);

                if (parsedDate < DateTime.now()) {
                    this.state.expirationDate = parsedDate.toLocaleString(DateTime.DATE_FULL);
                    this.state.hasSubscription = true;
                }
                else {
                    this.state.expirationDate = parsedDate.toLocaleString(DateTime.DATE_FULL);
                    this.state.hasSubscription = false;
                }
            }
            else {
                this.state.hasSubscription = false;
                this.state.expirationDate = null;
            }
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

    get showSubscriptionSection() {
        // return this.state.hasSubscription || this.state.showSub;
        return this.state.hasSubscription;
    }

    // TODO: remove this later, it's for debug
    switchHasSubscription() {
        this.state.hasSubscription = !this.state.hasSubscription;
        // this.state.hasSubscription = this.state.hasSubscription ? "XXXXXX" : ""
    }
}

registry.category("actions").add("mysubscription.dashboard", MySubscriptionDashboard);
