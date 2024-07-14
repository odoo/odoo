/** @odoo-module */

import { registry } from "@web/core/registry";
import { download } from "@web/core/network/download";

async function executeAccountReportDownload({ env, action }) {
    env.services.ui.block();

    const url = "/account_reports";
    const data = action.data;

    try {
        await download({ url, data });
        env.services.action.doAction({type: 'ir.actions.act_window_close'});
    } catch (e) {
        if (e.exceptionName === 'AccountReportFileDownloadException') {
            const reportOptions = JSON.parse(data.options);
            const reportAction = await env.services.orm.call(
                'account.report',
                'open_account_report_file_download_error_wizard',
                [reportOptions.report_id, e.data.arguments[0], e.data.arguments[1]],
            );
            env.services.action.doAction(reportAction);
        } else {
            throw e;
        }
    } finally {
        env.services.ui.unblock();
    }
}

registry
    .category("action_handlers")
    .add('ir_actions_account_report_download', executeAccountReportDownload);
