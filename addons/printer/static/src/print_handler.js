import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import {
    PRINTER_LINKED_TO_REPORT,
    setReportIdInLocalStorage,
} from "./local_storage/printer_local_storage";

const ENDPOINTS = { office_printer: "/print/pdf" };

async function sendToProxy({ printer, payload }) {
    const { name, printer_type, printer_ip } = printer;

    const binary = atob(payload);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i);
    }

    const response = await fetch(`http://${printer_ip}${ENDPOINTS[printer_type]}`, {
        method: "POST",
        headers: { "Content-Type": "application/octet-stream" },
        body: bytes,
        signal: AbortSignal.timeout(30000),
        targetAddressSpace: "loopback",
    });

    if (!response.ok) {
        throw new Error(`Print failed for printer at ${name}`);
    }
}

async function executePrint(env, reportId, printerIds, recordIds, reportData) {
    const { orm, notification, ui } = env.services;
    try {
        ui.block();

        const jobs = await orm.call("ir.actions.report", "generate_print_data", [
            reportId,
            printerIds,
            recordIds,
            reportData,
        ]);

        for (const job of jobs) {
            await sendToProxy(job);
        }

        notification.add(_t("Print job sent successfully"), { type: "success" });
        return true;
    } catch (error) {
        notification.add(_t("Failed to print document") + ": " + error.message, { type: "danger" });
        return false;
    } finally {
        ui.unblock();
    }
}

async function selectPrinters(reportId, env) {
    const { orm, action, ui } = env.services;
    const printerSettingsByReportId = JSON.parse(
        browser.localStorage.getItem(PRINTER_LINKED_TO_REPORT)
    );

    const printerSetting = printerSettingsByReportId?.[reportId];
    if (printerSetting && printerSetting.skipDialog) {
        return printerSetting.selectedPrinters;
    }

    const wizard = await orm.call("ir.actions.report", "get_printer_selection_wizard", [
        reportId,
        printerSetting?.selectedPrinters,
    ]);
    await action.doAction(wizard);

    const wasBlocked = ui.isBlocked;
    if (wasBlocked) {
        ui.unblock();
    }

    return new Promise((resolve) => {
        const handler = (event) => {
            if (event.detail.reportId === reportId) {
                const settings = event.detail.printerSettings;
                if (settings) {
                    setReportIdInLocalStorage(reportId, settings);
                }
                resolve(settings ? settings.selectedPrinters : null);
                env.bus.removeEventListener("report-printer-selected", handler);
                if (wasBlocked) {
                    ui.block();
                }
            }
        };
        env.bus.addEventListener("report-printer-selected", handler);
    });
}

async function printReportHandler(action, options, env) {
    const printerIds = await selectPrinters(action.id, env);
    if (!printerIds?.length) {
        return false;
    }

    const success = await executePrint(
        env,
        action.id,
        printerIds,
        action.context.active_ids.filter((e) => typeof e === "number"),
        action.data || {}
    );

    if (success) {
        options.onClose?.();
    }
    return success;
}

registry.category("ir.actions.report handlers").add("print_handler", printReportHandler);
