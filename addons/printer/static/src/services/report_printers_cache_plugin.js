import { registry } from "@web/core/registry";
import { services } from "@web/core/services";
import { Plugin, usePlugin, useScope } from "@odoo/owl";
import { ActionPlugin } from "@web/webclient/actions/action_plugin";
import { UIPlugin } from "@web/core/ui/ui_plugin";
import { ORM } from "@web/core/orm_plugin";
import { GlobalBusPlugin } from "@web/core/global_bus_plugin";

const STORAGE_KEY = "odoo_reports_printer";

function readFromStorage() {
    try {
        return JSON.parse(window.localStorage.getItem(STORAGE_KEY) || "{}");
    } catch {
        return {};
    }
}

function writeToStorage(cache) {
    if (Object.keys(cache).length === 0) {
        window.localStorage.removeItem(STORAGE_KEY);
    } else {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(cache));
    }
}

export class ReportPrintersCachePlugin extends Plugin {
    #scope = useScope();

    #action = usePlugin(ActionPlugin);
    #orm = usePlugin(ORM);
    #ui = usePlugin(UIPlugin);
    #globalBus = usePlugin(GlobalBusPlugin);

    #cache = readFromStorage(); // hydrated once

    get cache() {
        return this.#cache;
    }

    unCacheReport(reportId) {
        const updated = { ...this.#cache };
        delete updated[reportId];
        this.#writeCache(updated);
    }

    async getPrinterSettingsForReport(reportId) {
        const deviceSettings = this.#cache[reportId];

        if (deviceSettings?.skipDialog) {
            return deviceSettings;
        }

        const openDeviceSelectionWizard = await this.#orm.call(
            "ir.actions.report",
            "get_select_printer_wizard",
            [reportId, deviceSettings]
        );
        await this.#action.doAction(openDeviceSelectionWizard);

        const uiWasBlocked = this.#ui.isBlocked();
        if (uiWasBlocked) {
            this.#ui.unblock();
        }

        return new Promise((resolve) => {
            const onPrinterSelected = ({ detail }) => {
                if (detail.reportId !== reportId) {
                    return;
                }

                const { deviceSettings: newSettings } = detail;
                if (newSettings) {
                    this.#writeCache({ ...this.#cache, [reportId]: newSettings });
                }
                this.#globalBus.bus.removeEventListener("printer-selected", onPrinterSelected);
                if (uiWasBlocked) {
                    this.#ui.block();
                }
                resolve(newSettings ?? null);
            };
            this.#globalBus.bus.addEventListener("printer-selected", onPrinterSelected, {
                signal: this.#scope.abortSignal,
            });
        });
    }

    #writeCache(newCache) {
        this.#cache = newCache;
        writeToStorage(newCache);
    }
}

services.add(ReportPrintersCachePlugin);

/**
 * ----------------------------------------------------------------------------
 * @todo owl3 migration
 * Temporary - to remove when all uses of the "report_printers_cache" service
 * are removed
 * ----------------------------------------------------------------------------
 */
registry.category("services").add("report_printers_cache", {
    start() {
        return usePlugin(ReportPrintersCachePlugin);
    },
});
