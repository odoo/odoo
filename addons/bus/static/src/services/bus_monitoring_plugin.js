import { Plugin, signal, useListener, usePlugin } from "@odoo/owl";
import { WORKER_STATE } from "@bus/workers/websocket_worker";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { BusPlugin } from "@bus/services/bus_plugin";
import { services } from "@web/core/services";

/**
 * Detect lost connections to the bus. A connection is considered as lost if it
 * couldn't be established after a reconnect attempt, or if the worker is
 * outdated and the page must be reloaded.
 */
export class BusMonitoringPlugin extends Plugin {
    #busService = usePlugin(BusPlugin);
    isConnectionLost = signal(false);
    isOutdated = signal(false);
    #isReconnecting = signal(false);

    setup() {
        useListener(this.#busService, "BUS:WORKER_STATE_UPDATED", ({ detail }) =>
            this.#workerStateOnChange(detail)
        );
        useListener(this.#busService, "BUS:OUTDATED", () => {
            this.isOutdated.set(true);
            this.isConnectionLost.set(true);
        });
        useListener(browser, "offline", () => this.#isReconnecting.set(false));
    }

    /**
     * Handle state changes for the WebSocket worker.
     *
     * @param {WORKER_STATE[keyof WORKER_STATE]} state
     */
    #workerStateOnChange(state) {
        switch (state) {
            case WORKER_STATE.CONNECTING: {
                this.#isReconnecting.set(true);
                break;
            }
            case WORKER_STATE.CONNECTED: {
                this.#isReconnecting.set(false);
                this.isConnectionLost.set(false);
                break;
            }
            case WORKER_STATE.DISCONNECTED: {
                if (this.#isReconnecting()) {
                    this.isConnectionLost.set(true);
                    this.#isReconnecting.set(false);
                }
                break;
            }
        }
    }
}

services.add(BusMonitoringPlugin);

/**
 * -----------------------------------------------------------------------------
 * @todo owl3 migration
 * temporary - to remove when all use of the bus.monitoring_service service are removed
 * -----------------------------------------------------------------------------
 */
registry.category("services").add("bus.monitoring_service", {
    start() {
        return usePlugin(BusMonitoringPlugin);
    },
});
