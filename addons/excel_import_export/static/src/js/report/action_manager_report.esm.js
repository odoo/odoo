/** @odoo-module **/

import {download} from "@web/core/network/download";
import {registry} from "@web/core/registry";

function getReportUrl({report_name, context, data}, env) {
    // Rough copy of action_service.js _getReportUrl method.
    let url = `/report/excel/${report_name}`;
    const actionContext = context || {};
    if (data && JSON.stringify(data) !== "{}") {
        const encodedOptions = encodeURIComponent(JSON.stringify(data));
        const encodedContext = encodeURIComponent(JSON.stringify(actionContext));
        return `${url}?options=${encodedOptions}&context=${encodedContext}`;
    }
    if (actionContext.active_ids) {
        url += `/${actionContext.active_ids.join(",")}`;
    }
    const userContext = encodeURIComponent(JSON.stringify(env.services.user.context));
    return `${url}?context=${userContext}`;
}

async function triggerDownload(action, {onClose}, env) {
    // Rough copy of action_service.js _triggerDownload method.
    env.services.ui.block();
    try {
        await download({
            url: "/report/download",
            data: {
                data: JSON.stringify([getReportUrl(action, env), "excel"]),
                context: JSON.stringify(env.services.user.context),
            },
        });
    } finally {
        env.services.ui.unblock();
    }
    if (action.close_on_report_download) {
        return env.services.action.doAction(
            {type: "ir.actions.act_window_close"},
            {onClose}
        );
    }
    if (onClose) {
        onClose();
    }
}

registry
    .category("ir.actions.report handlers")
    .add("excel_handler", async function (action, options, env) {
        if (action.report_type === "excel") {
            await triggerDownload(action, options, env);
            return true;
        }
        return false;
    });
