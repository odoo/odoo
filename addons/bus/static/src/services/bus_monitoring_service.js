import { WORKER_STATE } from "@bus/workers/websocket_worker";
import { reactive } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

export const CONNECTION_LOST_WARNING_DELAY = 15000;
export const CONNECTION_STATUS = Object.freeze({
    CONNECTED: 0,
    CONNECTION_LOST: 1,
    CONNECTION_LOST_LONG: 2,
});

/**
 * Detect lost connections to the bus. A connection is considered as lost if it
 * couldn't be established after a reconnect attempt.
 */
export class BusMonitoringService {
    connectionStatus = CONNECTION_STATUS.CONNECTED;
    timeout;

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
        bus_service.addEventListener("worker_state_updated", ({ detail }) =>
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
        if (!navigator.onLine) {
            return;
        }
        switch (state) {
            case WORKER_STATE.CONNECTING: {
                this.isReconnecting = true;
                break;
            }
            case WORKER_STATE.CONNECTED: {
                this.isReconnecting = false;
                this.connectionStatus = CONNECTION_STATUS.CONNECTED;
                if (this.timeout) {
                    clearTimeout(this.timeout);
                    this.timeout = undefined;
                }
                break;
            }
            case WORKER_STATE.DISCONNECTED: {
                if (this.isReconnecting) {
                    this.isReconnecting = false;
                }
                if (!this.timeout) {
                    this.connectionStatus = CONNECTION_STATUS.CONNECTION_LOST;
                    this.timeout = browser.setTimeout(() => {
                        this.connectionStatus = CONNECTION_STATUS.CONNECTION_LOST_LONG;
                    }, CONNECTION_LOST_WARNING_DELAY);
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
