/** @odoo-module */

import { reportService } from "@point_of_sale/app/utils/report_service";
import { patch } from "@web/core/utils/patch";

patch(reportService, {
    async start(env, { rpc, user, ui, orm, pos }) {
        const superReportService = await super.start(...arguments);
        return {
            async doAction(reportXmlId, active_ids) {
                if (pos.isChileanCompany() && reportXmlId === "account.account_invoices") {
                    //Invoices are not downloaded in the POS in chili. The invoice is on a receipt ticket of type electronic invoice (factura).
                    return;
                }
                return superReportService.doAction(reportXmlId, active_ids);
            },
        };
    },
});
