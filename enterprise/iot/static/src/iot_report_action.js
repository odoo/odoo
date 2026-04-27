/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser"
import { DeviceController } from "@iot/device_controller";
import {
    IOT_REPORT_PREFERENCE_LOCAL_STORAGE_KEY,
    removeIoTReportIdFromBrowserLocalStorage,
    setReportIdInBrowserLocalStorage,
} from "./client_action/delete_local_storage";

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

/**
 * Get the devices from the ids stored in the localStorage
 * @param orm The ORM service
 * @param stored_content The list of devices in localStorage
 */
async function getDevicesFromIds(orm, stored_content) {
    return await orm.call("ir.actions.report", "get_devices_from_ids", [
        0,
        stored_content,
    ]);
}

/**
 * Send the report to the IoT device using longpolling
 * @param env The environment
 * @param orm The ORM service
 * @param args The arguments to send to the server to render the report
 * @param stored_device_ids The list of devices in localStorage to send the report to
 */
async function longpolling(env, orm, args, stored_device_ids) {
    const [report_id, active_record_ids, report_data, uuid] = args;
    const devices = await getDevicesFromIds(orm, stored_device_ids).catch((error) => {
        console.error("Failed to get devices from ids", error);
        throw error;
    });
    const jobs = await orm.call("ir.actions.report", "render_and_send", [
        report_id,
        devices,
        active_record_ids,
        report_data,
        uuid,
        false, // Do not use websocket
    ]);
    for (const job of jobs) {
        const [ ip, identifier, name, document, iot_idempotent_id ] = job;
        const longpollingHasFallback = true; // Prevent `IoTConnectionErrorDialog`
        env.services.notification.add(_t("Sending to printer %s...", name), { type: "info" });

        const iotDevice = new DeviceController(env.services.iot_longpolling, { iot_ip: ip, identifier });
        await iotDevice.action({ iot_idempotent_id, document, print_id: uuid }, longpollingHasFallback);
    }
}

/**
 * Try to send the report to the IoT device using longpolling, then fallback to the websocket
 * @param env The environment
 * @param orm The ORM service
 * @param args The arguments to send to the server to render the report
 * @param stored_device_ids The list of devices to send the report to
 */
export async function handleIoTConnectionFallbacks(env, orm, args, stored_device_ids) {
    // Define the connection types in the order of executions to try
    const connectionTypes = [
        () => longpolling(env, orm, args, stored_device_ids),
        () => env.services.iot_websocket.addJob(stored_device_ids, args, false),
    ];
    for (const connectionType of connectionTypes) {
        try {
            await connectionType();
            return;
        } catch (error) {
            if (error.type == "server") {
                removeIoTReportIdFromBrowserLocalStorage(args[0]); // args[0] = report_id
                env.services.ui.unblock();
                throw error;
            }
            console.debug("Send print request failed, attempting another protocol.");
        }
    }

    // Fail notification if all connections failed
    env.services.notification.add(_t("Failed to send to printer."), { type: "danger" });
    removeIoTReportIdFromBrowserLocalStorage(args[0]);  // args[0] = report_id
}

export async function getSelectedPrintersForReport(reportId, env) {
    const { orm, action, ui } = env.services;
    const selectedPrintersByReportId = JSON.parse(browser.localStorage.getItem(IOT_REPORT_PREFERENCE_LOCAL_STORAGE_KEY));
    const selectedPrinters = selectedPrintersByReportId?.[reportId];

    if (selectedPrinters) {
        return selectedPrinters;
    }

    // Open IoT devices selection wizard
    const openDeviceSelectionWizard = await orm.call("ir.actions.report", "get_action_wizard", [reportId]);
    await action.doAction(openDeviceSelectionWizard);

    // If the UI is currently blocked, we need to temporarily unblock it or the user won't be able to select the printer
    const uiWasBlocked = ui.isBlocked;
    if (uiWasBlocked) {
        ui.unblock();
    }

    // Wait for the popup to be closed and a printer selected
    return new Promise((resolve) => {
        const onPrinterSelected = (event) => {
            if (event.detail.reportId === reportId) {
                const selectedPrinters = event.detail.selectedPrinterIds;
                if (selectedPrinters) {
                    setReportIdInBrowserLocalStorage(reportId, selectedPrinters);
                }
                resolve(selectedPrinters);
                env.bus.removeEventListener("printer-selected", onPrinterSelected);
                if (uiWasBlocked) {
                    ui.block();
                }
            }
        };
        env.bus.addEventListener("printer-selected", onPrinterSelected);
    });
}

async function iotReportActionHandler(action, options, env) {
    if (action.device_ids && action.device_ids.length) {
        const orm = env.services.orm;
        action.data = action.data || {};
        const args = [action.id, action.context.active_ids, action.data, uuid()];
        const reportId = action.id;
        const printerIds = await getSelectedPrintersForReport(reportId, env);

        if (!printerIds) {
            // If the user does not select any printer, fall back to normal printing
            return false;
        }

        env.services.ui.block();
        // Try longpolling then websocket
        await handleIoTConnectionFallbacks(env, orm, args, printerIds);
        env.services.ui.unblock();

        options.onClose?.();
        return true;
    }
}

registry
    .category("ir.actions.report handlers")
    .add("iot_report_action_handler", iotReportActionHandler);
