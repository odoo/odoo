import { Plugin, proxy } from "@odoo/owl";

export class DashboardPlugin extends Plugin {
    static id = "dashboardPlugin";
    state = proxy({
        expirationDate: null,
        enterpriseCode: null,
        baseUrl: null,
    });

}
