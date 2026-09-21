/** @odoo-module native */
import { download } from "@web/core/network";
import { registry } from "@web/core/registry";

export async function executeAccountReportDownload({ env, action }) {
    env.services.ui.block();

    const url = "/account_reports";
    const data = action.data;

    try {
        await download({ url, data });
        if (!data.no_closing_after_download) {
            if (data.next_action) {
                env.services.action.doAction(data.next_action);
            } else {
                env.services.action.doAction({ type: "ir.actions.act_window_close" });
            }
        }
    } finally {
        env.services.ui.unblock();
    }
}

registry
    .category("action_handlers")
    .add("ir_actions_account_report_download", executeAccountReportDownload);
