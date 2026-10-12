import { Plugin, signal, useListener, usePlugin } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { services } from "@web/core/services";
import { BusPlugin } from "@bus/services/bus_plugin";
import { WorkerPlugin } from "@bus/services/worker_plugin";

export class BusLogsPlugin extends Plugin {
    /** @private */
    busService = usePlugin(BusPlugin);
    /** @private */
    workerService = usePlugin(WorkerPlugin);

    enabled = signal(JSON.parse(localStorage.getItem("bus_log_menu.enabled")));

    setup() {
        useListener(browser, "storage", ({ key, newValue }) => {
            if (key === "bus_log_menu.enabled") {
                this.enabled.set(JSON.parse(newValue));
            }
        });
        this.workerService.workerInitPromise.then(() => {
            this.busService.setLoggingEnabled(this.enabled());
        });
        odoo.busLogging = {
            stop: () => this.disableLogging(),
            start: () => this.enableLogging(),
            download: () => this.busService.downloadLogs(),
        };
        if (this.enabled()) {
            console.log(
                "Bus logging is enabled. To disable it, use `odoo.busLogging.stop()`. To download the logs, use `odoo.busLogging.download()`."
            );
        }
    }

    enableLogging() {
        this.enabled.set(true);
        this.busService.setLoggingEnabled(true);
        localStorage.setItem("bus_log_menu.enabled", true);
    }

    disableLogging() {
        this.enabled.set(false);
        this.busService.setLoggingEnabled(false);
        localStorage.setItem("bus_log_menu.enabled", false);
    }

    toggleLogging() {
        if (this.enabled()) {
            this.disableLogging();
        } else {
            this.enableLogging();
        }
    }
}

services.add(BusLogsPlugin);

/**
 * -----------------------------------------------------------------------------
 * @todo owl3 migration
 * temporary - to remove when all use of the bus.logs_service service are removed
 * -----------------------------------------------------------------------------
 */
registry.category("services").add("bus.logs_service", {
    start() {
        return usePlugin(BusLogsPlugin);
    },
});
