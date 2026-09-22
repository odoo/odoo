/** @odoo-module native */
import { executeAccountReportDownload } from "@report_formula/js/action_manager_account_report_dl";
import { registry } from "@web/core/registry";

async function executeAccountReportDownloadWithErrorWizard({ env, action }) {
    try {
        await executeAccountReportDownload({ env, action });
    } catch (e) {
        if (e.exceptionName !== "AccountReportFileDownloadException") {
            throw e;
        }
        const reportOptions = JSON.parse(action.data.options);
        const reportAction = await env.services.orm.call(
            "report.formula",
            "open_account_report_file_download_error_wizard",
            [reportOptions.report_id, e.data.arguments[0], e.data.arguments[1]],
        );
        env.services.action.doAction(reportAction);
    }
}

registry
    .category("action_handlers")
    .add(
        "ir_actions_account_report_download",
        executeAccountReportDownloadWithErrorWizard,
        {
            force: true,
        },
    );
