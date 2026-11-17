import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { EventBus, Plugin, signal, usePlugin } from "@odoo/owl";
import { BusParametersPlugin } from "@bus/bus_parameters_plugin";
import { services } from "@web/core/services";

export const WORKER_STATE = Object.freeze({
    UNINITIALIZED: "UNINITIALIZED",
    INITIALIZING: "INITIALIZING",
    INITIALIZED: "INITIALIZED",
    FAILED: "FAILED",
});

/**
 * @emits upgraded when the worker is replaced after a bump of the minor part
 * of the server `WebsocketConnectionHandler._VERSION`.
 */
export class WorkerPlugin extends Plugin {
    bus = new EventBus();
    #handlers = [];
    #params = usePlugin(BusParametersPlugin);
    #worker = null;
    #isUsingSharedWorker = Boolean(browser.SharedWorker);
    #state = signal(WORKER_STATE.UNINITIALIZED);
    #resolveWorkerInit = null;

    setup() {
        const promWithResolvers = Promise.withResolvers();
        this.workerInitPromise = promWithResolvers.promise;
        this.#resolveWorkerInit = promWithResolvers.resolve;
        if (!session.bus_info && session.websocket_worker_version) {
            console.warn(
                "'session.websocket_worker_version' is deprecated. Bus consumers should provide " +
                    "'bus_info' instead, including the 'last_id' to start from, to ensure that no notifications " +
                    "are missed between page load and subscription."
            );
            session.bus_info = { worker_version: session.websocket_worker_version };
        }
    }

    #startWorker() {
        if (!session.bus_info) {
            console.warn("Worker service cannot start: missing 'session.bus_info'.");
            this.#state.set(WORKER_STATE.FAILED);
            this.#resolveWorkerInit(false);
            return;
        }
        this.#state.set(WORKER_STATE.INITIALIZING);
        let workerURL = `${this.#params.serverURL()}/bus/websocket_worker_bundle?v=${
            session.bus_info.worker_version
        }`;
        if (this.#params.serverURL() !== window.origin) {
            // Worker service can be loaded from a different origin than the
            // bundle URL. The Worker expects an URL from this origin, give
            // it a base64 URL that will then load the bundle via "importScripts"
            // which allows cross origin.
            const source = `importScripts("${workerURL}");`;
            workerURL = "data:application/javascript;base64," + window.btoa(source);
        }
        const workerClass = this.#isUsingSharedWorker ? browser.SharedWorker : browser.Worker;
        this.#worker = new workerClass(workerURL, {
            name: this.#isUsingSharedWorker ? "odoo:bus_shared_worker" : "odoo:bus_worker",
        });
        this.#worker.onerror = (e) => this.#onInitError(e);
        this.#registerHandler((ev) => {
            if (ev.data.type === "BASE:INITIALIZED") {
                this.#state.set(WORKER_STATE.INITIALIZED);
                this.#resolveWorkerInit(true);
            }
        });
        if (this.#isUsingSharedWorker) {
            this.#worker.port.start();
        }
        this.#send("BASE:INIT");
    }

    /** @returns {Promise<boolean>} */
    ensureWorkerStarted() {
        if (this.#state() === WORKER_STATE.UNINITIALIZED) {
            this.#startWorker();
        }
        return this.workerInitPromise;
    }

    #onInitError(e) {
        // FIXME: SharedWorker can still fail for unknown reasons even when it is supported.
        if (this.#state() === WORKER_STATE.INITIALIZING && this.#isUsingSharedWorker) {
            console.warn("Error while loading SharedWorker, fallback on Worker: ", e);
            this.#isUsingSharedWorker = false;
            this.#worker?.port?.close?.();
            this.#startWorker();
        } else if (this.#state() === WORKER_STATE.INITIALIZING) {
            this.#state.set(WORKER_STATE.FAILED);
            this.#resolveWorkerInit(false);
            console.warn("Worker service failed to initialize: ", e);
        }
    }

    #registerHandler(handler) {
        if (this.#isUsingSharedWorker) {
            this.#worker.port.addEventListener("message", handler);
        } else {
            this.#worker.addEventListener("message", handler);
        }
    }

    #send(action, data) {
        const message = { action, data };
        if (this.#isUsingSharedWorker) {
            this.#worker.port.postMessage(message);
        } else {
            this.#worker.postMessage(message);
        }
    }

    /**
     * Send a message to the worker. If the worker is not yet started,
     * ignore the message. One should call `ensureWorkerStarted` if one
     * really needs the message to reach the worker.
     *
     * @param {String} action Action to be executed by the worker.
     * @param {Object|undefined} data Data required for the action to be
     * executed.
     */
    async send(action, data) {
        if (this.#state() === WORKER_STATE.UNINITIALIZED) {
            return;
        }
        // Wait for the new worker when the worker is replaced meanwhile.
        let initPromise;
        while (initPromise !== this.workerInitPromise) {
            initPromise = this.workerInitPromise;
            await initPromise;
        }
        if (this.#state() === WORKER_STATE.FAILED) {
            console.warn("Worker service failed to initialize, cannot send message.");
            return;
        }
        this.#send(action, data);
    }

    /**
     * Register a function to handle messages from the worker.
     *
     * @param {function} handler
     */
    async registerHandler(handler) {
        if (this.#state() === WORKER_STATE.UNINITIALIZED) {
            this.#startWorker();
        }
        await this.workerInitPromise;
        if (this.#state() === WORKER_STATE.FAILED) {
            console.warn("Worker service failed to initialize, cannot register handler.");
            return;
        }
        this.#registerHandler(handler);
        this.#handlers.push(handler);
    }

    /**
     * Replace the worker by the one of the given version. Return the reply
     * of the old worker to `leaveAction`: the state to keep.
     *
     * @param {string} version
     * @param {string} leaveAction
     * @param {string} responseType
     * @returns {Promise<{started: boolean, response: any}>}
     */
    async upgrade(version, leaveAction, responseType) {
        ({ promise: this.workerInitPromise, resolve: this.#resolveWorkerInit } =
            Promise.withResolvers());
        const { promise: responsePromise, resolve: resolveResponse } = Promise.withResolvers();
        this.#registerHandler(({ data }) => {
            if (data.type === responseType) {
                resolveResponse(data.data);
            }
        });
        this.#send(leaveAction);
        const response = await responsePromise;
        session.bus_info.worker_version = version;
        if (this.#isUsingSharedWorker) {
            this.#worker.port.close();
        } else {
            this.#worker.terminate();
        }
        this.#startWorker();
        if (!(await this.workerInitPromise)) {
            return { started: false, response };
        }
        for (const handler of this.#handlers) {
            this.#registerHandler(handler);
        }
        this.bus.trigger("upgraded");
        return { started: true, response };
    }

    get state() {
        return this.#state();
    }
}

services.add(WorkerPlugin);

/**
 * -----------------------------------------------------------------------------
 * @todo owl3 migration
 * temporary - to remove when all use of the worker_service service are removed
 * -----------------------------------------------------------------------------
 */
registry.category("services").add("worker_service", {
    dependencies: ["bus.parameters"],
    start() {
        return usePlugin(WorkerPlugin);
    },
});
