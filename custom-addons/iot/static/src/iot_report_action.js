/** @odoo-module **/

import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser"

/**
 * Generate a unique identifier (64 bits) in hexadecimal.
 * Copied beacause if imported from web import too many other modules
 * 
 * @returns {string}
 */
function uuid() {
    const array = new Uint8Array(8);
    window.crypto.getRandomValues(array);
    // Uint8Array to hex
    return [...array].map((b) => b.toString(16).padStart(2, "0")).join("");
}


async function iotReportActionHandler(action, options, env) {
    if (action.device_ids && action.device_ids.length) {
        const orm = env.services.orm;
        action.data = action.data || {};
        action.data["device_ids"] = action.device_ids;
        const args = [action.id, action.context.active_ids, action.data, uuid()];
        const report_id = action.id;
        const local_lists = JSON.parse(browser.localStorage.getItem("odoo-iot-linked_reports"));
        const list = local_lists ? local_lists[report_id] : undefined;
        if (!list) {
            const action_wizard = await orm.call("ir.actions.report", "get_action_wizard", args);
            await env.services.action.doAction(action_wizard);
        }
        else {
            await env.services.iot_websocket.addJob(list, args);
        }
        if (options.onClose) {
            options.onClose();
        }
        return true;
    }
}

registry
    .category("ir.actions.report handlers")
    .add("iot_report_action_handler", iotReportActionHandler);
