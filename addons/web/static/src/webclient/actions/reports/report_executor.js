// @ts-check

/** @module @web/webclient/actions/reports/report_executor - Executes ir.actions.report as HTML preview or PDF/text download */

/**
 * Report action executor functions for the action service.
 *
 * Handles execution of ir.actions.report actions, including HTML previews
 * (via ReportAction client component) and PDF/text downloads.
 */

import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { user } from "@web/services/user";

import { ReportAction } from "./report_action";
import { downloadReport, getReportUrl } from "./utils";

/**
 * Execute a report action as a client-side HTML preview.
 *
 * @param {Object} action the report action descriptor
 * @param {Object} options action execution options
 * @param {Object} ctx
 * @param {Function} ctx.makeController create a controller object
 * @param {Function} ctx.getActionInfo build action info (props, config, state)
 * @param {Function} ctx.updateUI render the controller in the action container
 * @returns {Promise}
 */
export function executeReportClientAction(action, options, ctx) {
    const { makeController, getActionInfo, updateUI } = ctx;
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

    const controller = makeController({
        Component: ReportAction,
        action,
        ...getActionInfo(action, props),
    });

    return updateUI(controller, options);
}

/**
 * Execute a report action. Delegates to registered report handlers first,
 * then falls back to HTML preview or PDF/text download.
 *
 * @param {Object} action the report action descriptor
 * @param {Object} options action execution options
 * @param {Object} ctx
 * @param {Object} ctx.env the OWL environment
 * @param {Function} ctx.doAction execute another action
 * @param {Function} ctx.makeController create a controller object
 * @param {Function} ctx.getActionInfo build action info
 * @param {Function} ctx.updateUI render the controller
 * @returns {Promise}
 */
export async function executeReportAction(action, options, ctx) {
    const { env, doAction, makeController, getActionInfo, updateUI } = ctx;
    const clientActionCtx = { makeController, getActionInfo, updateUI };

    const handlers = registry.category("ir.actions.report handlers").getAll();
    for (const handler of handlers) {
        const result = await handler(action, options, env);
        if (result) {
            const { onClose } = options;
            if (action.close_on_report_download) {
                return doAction({ type: "ir.actions.act_window_close" }, { onClose });
            } else if (onClose) {
                onClose();
            }
            return result;
        }
    }
    if (action.report_type === "qweb-html") {
        return executeReportClientAction(action, options, clientActionCtx);
    } else if (
        action.report_type === "qweb-pdf" ||
        action.report_type === "qweb-text"
    ) {
        const type = action.report_type.slice(5);
        let success, message;
        env.services.ui.block();
        try {
            const downloadContext = { ...user.context };
            if (action.context) {
                Object.assign(downloadContext, action.context);
            }
            ({ success, message } = await downloadReport(
                rpc,
                action,
                type,
                downloadContext,
            ));
        } finally {
            env.services.ui.unblock();
        }
        if (message) {
            env.services.notification.add(message, {
                sticky: true,
                title: _t("Report"),
            });
        }
        if (!success) {
            return executeReportClientAction(action, options, clientActionCtx);
        }
        const { onClose } = options;
        if (action.close_on_report_download) {
            return doAction({ type: "ir.actions.act_window_close" }, { onClose });
        } else if (onClose) {
            onClose();
        }
    } else {
        console.error(
            `The ActionManager can't handle reports of type ${action.report_type}`,
            action,
        );
    }
}
