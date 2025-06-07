import { _t } from "@web/core/l10n/translation";
import { download } from "@web/core/network/download";

/**
 * Generates the report url given a report action.
 *
 * @param {Object} action the report action
 * @param {"text"|"qweb"|"html"} type the type of the report
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

// messages that might be shown to the user dependening on the state of wkhtmltopdf
function getWKHTMLTOPDF_MESSAGES(status) {
    const link = '<br><br><a href="http://wkhtmltopdf.org/" target="_blank">wkhtmltopdf.org</a>'; // FIXME missing markup
    const _status = {
        broken: _t(
            "Your installation of Wkhtmltopdf seems to be broken. The report will be shown in html.%(link)s",
            { link }
        ),
        install: _t(
            "Unable to find Wkhtmltopdf on this system. The report will be shown in html.%(link)s",
            { link }
        ),
        upgrade: _t(
            "You should upgrade your version of Wkhtmltopdf to at least 0.12.0 in order to get a correct display of headers and footers as well as support for table-breaking between pages.%(link)s",
            { link }
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
 * @returns {Promise<{success: boolean, message?: string}>}
 */
export async function downloadReport(rpc, action, type, userContext) {
    let message;
    if (type === "pdf") {
        // Cache the wkhtml status on the function. In prod this means is only
        // checked once, but we can reset it between tests to test multiple statuses.
        downloadReport.wkhtmltopdfStatusProm ||= rpc("/report/check_wkhtmltopdf");
        const status = await downloadReport.wkhtmltopdfStatusProm;
        message = getWKHTMLTOPDF_MESSAGES(status);
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
