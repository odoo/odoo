// @ts-check
/** @odoo-module native */

import { registry } from "@web/core/registry";
import { user } from "@web/core/user";

import { ReportAction } from "./report_action.js";
import { downloadReport, getReportUrl } from "./utils.js";

registry
    .category("ir.actions.report handlers")
    .addValidation((entry) => typeof entry === "function");

/** @import { ActionManager, ActionOptions, ReportAction as ReportActionType } from "../action_service.js" */

/**
 * @param {ReportActionType} action
 * @param {ActionOptions} options
 * @param {ActionManager} am
 * @returns {Promise<any>}
 */
export async function executeReportClientAction(action, options, am) {
    if (action.target !== "new" && !options.newWindow) {
        if (!(await am.confirmLeave({ forceLeave: options.forceLeave }))) {
            return;
        }
    }
    const props = {
        ...options.props,
        data: action.data,
        display_name: action.display_name,
        name: action.name,
        report_file: action.report_file,
        report_name: action.report_name,
        report_url: getReportUrl(action, "html", user.context),
        context: { ...action.context },
    };

    const controller = am.makeController({
        Component: ReportAction,
        action,
        ...am.getActionInfo(action, props),
    });

    return am.updateUI(controller, options);
}

/**
 * @param {ReportActionType} action
 * @param {ActionOptions} options
 * @param {ActionManager} am
 * @returns {Promise<any>|undefined}
 */
function finishReport(action, options, am) {
    const { onClose } = options;
    if (action.close_on_report_download) {
        return am.doAction({ type: "ir.actions.act_window_close" }, { onClose });
    }
    onClose?.();
    return undefined;
}

/**
 * @param {ReportActionType} action
 * @param {ActionOptions} options
 * @param {ActionManager} am
 * @returns {Promise<any>}
 */
export async function executeReportAction(action, options, am) {
    const token = am.navigation.snapshot();
    const handlers = registry.category("ir.actions.report handlers").getAll();
    for (const handler of handlers) {
        const result = await handler(action, options, am.env);
        if (result) {
            return finishReport(action, options, am) ?? result;
        }
        token.throwIfSuperseded();
    }
    if (action.report_type === "qweb-html") {
        return executeReportClientAction(action, options, am);
    } else if (
        action.report_type === "qweb-pdf" ||
        action.report_type === "qweb-text"
    ) {
        const type = action.report_type === "qweb-pdf" ? "pdf" : "text";
        am.uiService.block();
        try {
            await downloadReport(action, type, user.context);
        } finally {
            am.uiService.unblock();
        }
        return finishReport(action, options, am);
    } else {
        console.error(
            `The ActionManager can't handle reports of type ${action.report_type}`,
            action,
        );
        options.onClose?.();
    }
}
