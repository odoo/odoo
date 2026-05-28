import { Plugin, proxy, effect } from "@odoo/owl";

export class DashboardPlugin extends Plugin {
    static id = "dashboardPlugin";
    state = proxy({
        hasSubscription: false,
        expirationDate: null,
        enterpriseCode: null,
        baseUrl: null,
        // showSub: false,
    });

    setup() {
        effect(() => {
            console.log("Dashboard modified:", JSON.parse(JSON.stringify(this.state)));
        });
    }
}
