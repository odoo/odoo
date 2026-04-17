import { Plugin, proxy } from "@odoo/owl";

export class DashboardPlugin extends Plugin {
    static id = "dashboardPlugin";
    state = proxy({
        selectedPlan: null,
        hasSubscription: false,
        expirationDate: null,
        enterpriseCode: null,
        baseUrl: null,
        showSub: false,
    });
}
