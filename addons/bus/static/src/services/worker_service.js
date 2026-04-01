import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { Deferred } from "@web/core/utils/concurrency";
import { session } from "@web/session";

export const WORKER_STATE = Object.freeze({
    UNINITIALIZED: "UNINITIALIZED",
    INITIALIZING: "INITIALIZING",
    INITIALIZED: "INITIALIZED",
    FAILED: "FAILED",
});

export class WorkerService {
    constructor(env, services) {
        this.params = services["bus.parameters"];
        this.worker = null;
        this.isUsingSharedWorker = Boolean(browser.SharedWorker);
        this._state = WORKER_STATE.UNINITIALIZED;
        this.connectionInitializedDeferred = new Deferred();
    }

    startWorker() {
        this._state = WORKER_STATE.INITIALIZING;
        let workerURL = `${this.params.serverURL}/bus/websocket_worker_bundle?v=${session.websocket_worker_version}`;
        if (this.params.serverURL !== window.origin) {
            // Worker service can be loaded from a different origin than the
            // bundle URL. The Worker expects an URL from this origin, give
            // it a base64 URL that will then load the bundle via "importScripts"
            // which allows cross origin.
            const source = `importScripts("${workerURL}");`;
            workerURL = "data:application/javascript;base64," + window.btoa(source);
        }
        const workerClass = this.isUsingSharedWorker ? browser.SharedWorker : browser.Worker;
        this.worker = new workerClass(workerURL, {
            name: this.isUsingSharedWorker ? "odoo:bus_shared_worker" : "odoo:bus_worker",
        });
        this.worker.onerror = (e) => this.onInitError(e);
        this._registerHandler((ev) => {
            if (ev.data.type === "BASE:INITIALIZED") {
                this._state = WORKER_STATE.INITIALIZED;
                this.connectionInitializedDeferred.resolve();
            }
        });
        if (this.isUsingSharedWorker) {
            this.worker.port.start();
        }
        this._send("BASE:INIT");
    }

    async ensureWorkerStarted() {
        if (this._state === WORKER_STATE.UNINITIALIZED) {
            this.startWorker();
        }
        await this.connectionInitializedDeferred;
    }

    onInitError(e) {
        // FIXME: SharedWorker can still fail for unknown reasons even when it is supported.
        if (this._state === WORKER_STATE.INITIALIZING && this.isUsingSharedWorker) {
            console.warn("Error while loading SharedWorker, fallback on Worker: ", e);
            this.isUsingSharedWorker = false;
            this.worker?.port?.close?.();
            this.startWorker();
        } else if (this._state === WORKER_STATE.INITIALIZING) {
            this._state = WORKER_STATE.FAILED;
            this.connectionInitializedDeferred.resolve();
            console.warn("Worker service failed to initialize: ", e);
        }
    }

    _registerHandler(handler) {
        if (this.isUsingSharedWorker) {
            this.worker.port.addEventListener("message", handler);
        } else {
            this.worker.addEventListener("message", handler);
        }
    }

    _send(action, data) {
        const message = { action, data };
        if (this.isUsingSharedWorker) {
            this.worker.port.postMessage(message);
        } else {
            this.worker.postMessage(message);
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
        if (this._state === WORKER_STATE.UNINITIALIZED) {
            return;
        }
        await this.connectionInitializedDeferred;
        if (this._state === WORKER_STATE.FAILED) {
            console.warn("Worker service failed to initialize, cannot send message.");
        }
        this._send(action, data);
    }

    /**
     * Register a function to handle messages from the worker.
     *
     * @param {function} handler
     */
    async registerHandler(handler) {
        if (this._state === WORKER_STATE.UNINITIALIZED) {
            this.startWorker();
        }
        await this.connectionInitializedDeferred;
        if (this._state === WORKER_STATE.FAILED) {
            console.warn("Worker service failed to initialize, cannot register handler.");
        }
        this._registerHandler(handler);
    }

    get state() {
        return this._state;
    }
}

export const workerService = {
    dependencies: ["bus.parameters"],
    start(env, services) {
        return new WorkerService(env, services);
    },
};

registry.category("services").add("worker_service", workerService);
