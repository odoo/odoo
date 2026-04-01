import { WORKER_STATE } from "@bus/workers/websocket_worker";
import { reactive } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

/**
 * Detect lost connections to the bus. A connection is considered as lost if it
 * couldn't be established after a reconnect attempt.
 */
export class BusMonitoringService {
    isConnectionLost = false;

    constructor(env, services) {
        const reactiveThis = reactive(this);
        reactiveThis.setup(env, services);
        return reactiveThis;
    }

    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    setup(env, { bus_service }) {
        bus_service.addEventListener("BUS:WORKER_STATE_UPDATED", ({ detail }) =>
            this.workerStateOnChange(detail)
        );
        browser.addEventListener("offline", () => (this.isReconnecting = false));
    }

    /**
     * Handle state changes for the WebSocket worker.
     *
     * @param {WORKER_STATE[keyof WORKER_STATE]} state
     */
    workerStateOnChange(state) {
        switch (state) {
            case WORKER_STATE.CONNECTING: {
                this.isReconnecting = true;
                break;
            }
            case WORKER_STATE.CONNECTED: {
                this.isReconnecting = false;
                this.isConnectionLost = false;
                break;
            }
            case WORKER_STATE.DISCONNECTED: {
                if (this.isReconnecting) {
                    this.isConnectionLost = true;
                    this.isReconnecting = false;
                }
                break;
            }
        }
    }
}

export const busMonitoringservice = {
    dependencies: ["bus_service"],
    start(env, services) {
        return new BusMonitoringService(env, services);
    },
};

registry.category("services").add("bus.monitoring_service", busMonitoringservice);
