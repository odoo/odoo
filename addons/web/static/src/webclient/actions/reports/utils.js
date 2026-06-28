import { _t } from "@web/core/l10n/translation";
import { download } from "@web/core/network/download";

/**
 * Generates the report url given a report action.
 *
 * @param {Object} action the report action
 * @param {"text"|"qweb"|"html"|"pdf"} type the type of the report
 * @param {Object} userContext the user context
 * @returns {string}
 */
export function getReportUrl(action, type, userContext) {
    let url = `/report/${type}/${action.report_name}`;
    const actionContext = action.context || {};
    if (action.data && JSON.stringify(action.data) !== "{}") {
        // build a query string with `action.data` (it's the place where reports
        // using a wizard to customize the output traditionally put their options)
        const options = encodeURIComponent(JSON.stringify(action.data));
        const context = encodeURIComponent(JSON.stringify(actionContext));
        url += `?options=${options}&context=${context}`;
    } else {
        if (actionContext.active_ids) {
            url += `/${actionContext.active_ids.join(",")}`;
        }
        if (type === "html") {
            const context = encodeURIComponent(JSON.stringify(userContext));
            url += `?context=${context}`;
        }
    }
    return url;
}

// messages that might be shown to the user dependening on the PDF engine state
function getPdfEngineMessage(status) {
    const _status = {
        broken: _t(
            "Your installation of PDF engine seems to be broken, check with the administrator. The report will be shown in html."
        ),
        install: _t(
            "Unable to find the PDF engine on this system. The report will be shown in html."
        ),
        upgrade: _t(
            "You should upgrade your version of the PDF engine in order to get a correct render it.",
        ),
        workers: _t(
            "You need to start Odoo with at least two workers to print a pdf version of the reports."
        ),
    };
    return _status[status];
}

/**
 * Launches download action of the report
 *
 * @param {Function} rpc a function to perform RPCs
 * @param {Object} action the report action
 * @param {"pdf"|"text"} type the type of the report to download
 * @param {Object} userContext the user context
 * @param {"string"} [engineName] the pdf rendering engine to use
 * @returns {Promise<{success: boolean, message?: string}>}
 */
export async function downloadReport(rpc, action, type, userContext, engineName) {
    let message;
    if (type === "pdf") {
        // Cache the engine status on the function. In prod this means is only
        // checked once, but we can reset it between tests to test multiple statuses.
        let params = {};
        if (engineName){
            params.engine_name = engineName;
        }
        downloadReport.reportingEngineStatusProm ||= rpc("/report/get_pdf_engine_state", params);
        const status = await downloadReport.reportingEngineStatusProm;
        message = getPdfEngineMessage(status);
        if (!["upgrade", "ok"].includes(status)) {
            return { success: false, message };
        }
    }
    const url = getReportUrl(action, type);
    await download({
        url: "/report/download",
        data: {
            data: JSON.stringify([url, action.report_type]),
            context: JSON.stringify(userContext),
        },
    });
    return { success: true, message };
}
