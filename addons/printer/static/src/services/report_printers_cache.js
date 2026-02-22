import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";

export class ReportPrintersCacheService {
    STORAGE_KEY = "odoo_reports_printer";

    constructor({ action, bus_service, orm, ui }) {
        this.orm = orm;
        this.action = action;
        this.ui = ui;
        this.bus = bus_service;
    }

    get cache() {
        try {
            return JSON.parse(browser.localStorage.getItem(this.STORAGE_KEY) || "{}");
        } catch {
            return {};
        }
    }

    _updateCache(cache) {
        if (Object.keys(cache).length === 0) {
            browser.localStorage.removeItem(this.STORAGE_KEY);
        } else {
            // Replace the entry in LocalStorage by the same object with the key 'report_id' removed
            browser.localStorage.setItem(this.STORAGE_KEY, JSON.stringify(cache));
        }
    }

    unCacheReport(reportId) {
        const cache = this.cache;
        delete cache[reportId];
        this._updateCache(cache);
    }

    cacheReportSettings(reportId, settings) {
        this._updateCache({ ...this.cache, [reportId]: settings })
    }

    async getSelectedPrintersForReport(reportId) {
        const deviceSettings = this.cache?.[reportId];

        if (deviceSettings?.skipDialog) {
            return deviceSettings;
        }

        // Open printers selection wizard
        const openDeviceSelectionWizard = await this.orm.call("ir.actions.report", "get_select_printer_wizard", [
            reportId,
            deviceSettings,
        ]);
        await this.action.doAction(openDeviceSelectionWizard);

        // If the UI is currently blocked, we need to temporarily unblock it or the user won't be able to select the printer
        const uiWasBlocked = this.ui.isBlocked;
        if (uiWasBlocked) {
            this.ui.unblock();
        }

        // Wait for the popup to be closed and a printer selected
        return new Promise((resolve) => {
            const onPrinterSelected = ({ detail }) => {
                if (detail.reportId === reportId) {
                    const newDeviceSettings = detail.deviceSettings;
                    if (newDeviceSettings) {
                        this.cacheReportSettings(reportId, newDeviceSettings);
                    }
                    resolve(newDeviceSettings || null);
                    this.bus.removeEventListener("printer-selected", onPrinterSelected);
                    if (uiWasBlocked) {
                        this.ui.block();
                    }
                }
            };
            this.bus.addEventListener("printer-selected", onPrinterSelected);
        });
    }
}

export const reportPrintersCacheService = {
    dependencies: ["action", "bus_service", "orm", "ui"],

    start(env, services) {
        return new ReportPrintersCacheService(services);
    }
};

registry.category("services").add("report_printers_cache", reportPrintersCacheService);
