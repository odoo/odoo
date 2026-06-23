import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";

const STORAGE_KEY = "odoo_reports_printer";

function readFromStorage() {
    try {
        return JSON.parse(browser.localStorage.getItem(STORAGE_KEY) || "{}");
    } catch {
        return {};
    }
}

function writeToStorage(cache) {
    if (Object.keys(cache).length === 0) {
        browser.localStorage.removeItem(STORAGE_KEY);
    } else {
        browser.localStorage.setItem(STORAGE_KEY, JSON.stringify(cache));
    }
}

registry.category("services").add("report_printers_cache", {
    dependencies: ["action", "bus_service", "orm", "ui"],

    start(env, { action, bus_service: bus, orm, ui }) {
        let cache = readFromStorage(); // hydrated once

        function writeCache(newCache) {
            cache = newCache;
            writeToStorage(newCache);
        }

        return {
            get cache() {
                return cache;
            },

            unCacheReport(reportId) {
                const updated = { ...cache };
                delete updated[reportId];
                writeCache(updated);
            },

            async getPrinterSettingsForReport(reportId) {
                const deviceSettings = cache[reportId];

                if (deviceSettings?.skipDialog) {
                    return deviceSettings;
                }

                const openDeviceSelectionWizard = await orm.call(
                    "ir.actions.report",
                    "get_select_printer_wizard",
                    [reportId, deviceSettings]
                );
                await action.doAction(openDeviceSelectionWizard);

                const uiWasBlocked = ui.isBlocked;
                if (uiWasBlocked) {
                    ui.unblock();
                }

                return new Promise((resolve) => {
                    const onPrinterSelected = ({ detail }) => {
                        if (detail.reportId !== reportId) return;

                        const { deviceSettings: newSettings } = detail;
                        if (newSettings) {
                            writeCache({ ...cache, [reportId]: newSettings });
                        }
                        bus.removeEventListener("printer-selected", onPrinterSelected);
                        if (uiWasBlocked) {
                            ui.block();
                        }
                        resolve(newSettings ?? null);
                    };
                    bus.addEventListener("printer-selected", onPrinterSelected);
                });
            },
        };
    },
});
