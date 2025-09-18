// @ts-check

/** @module @web/webclient/actions/reports/utils - Report URL generation and download helper for ir.actions.report */

/**
 * Generates the report url given a report action.
 *
 * @param {Object} action the report action
 * @param {string} type the type of the report
 * @param {Object} userContext the user context
 * @returns {string}
 */

import { download } from "@web/core/network/download";
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
    const url = getReportUrl(action, type);
    await download({
        url: "/report/download",
        data: {
            data: JSON.stringify([url, action.report_type]),
            context: JSON.stringify(userContext),
        },
    });
    return { success: true };
}
