/** @odoo-module */

import { registry } from "@web/core/registry";
import { reportService } from "@point_of_sale/app/utils/report_service";
import { patch } from "@web/core/utils/patch";

patch(reportService, {
    async start(env, { rpc, user, ui }) {
        const superReportService = await super.start(...arguments);
        return {
            async doAction(action, options) {
                const handlers = registry.category("ir.actions.report handlers").getAll();
                const reportAction = await rpc("/web/action/load", {
                    action_id: action,
                });
                reportAction.context = { active_ids: options };
                for (const handler of handlers) {
                    const result = await handler(reportAction, options, env);
                    if (result) {
                        return result;
                    }
                }
                return superReportService.doAction(action, options);
            }
        };
    },
});
