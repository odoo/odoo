/** @odoo-module */

import { registry } from "@web/core/registry";
import { downloadReport } from "@web/webclient/actions/reports/utils";

export const reportService = {
    dependencies: ["rpc", "user", "ui"],
    start(env, { rpc, user, ui }) {
        const reportActionsCache = {};
        return {
            async doAction(reportXmlId, active_ids) {
                ui.block();
                try {
                    reportActionsCache[reportXmlId] ||= rpc("/web/action/load", {
                        action_id: reportXmlId,
                    });
                    const reportAction = await reportActionsCache[reportXmlId];
                    // await instead of return because we want the ui to stay blocked
                    await downloadReport(
                        rpc,
                        { ...reportAction, context: { active_ids } },
                        "pdf",
                        user.context
                    );
                } finally {
                    ui.unblock();
                }
            },
        };
    },
};

registry.category("services").add("report", reportService);
