import { EventBus, Plugin, signal, useListener, usePlugin } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { session } from "@web/session";
import { services } from "@web/core/services";
import { useEnv } from "@web/owl2/utils";
import { MultiTabPlugin } from "@bus/multi_tab_plugin";
import { BusParametersPlugin } from "@bus/bus_parameters_plugin";
import { WorkerPlugin } from "@bus/services/worker_plugin";

// List of worker events that should not be broadcasted.
const INTERNAL_EVENTS = new Set([
    "BUS:INITIALIZED",
    "BUS:LAST_ID_RESET",
    "BUS:NOTIFICATION",
    "BUS:PROVIDE_LOGS",
]);
// Slightly delay the reconnection when coming back online as the network is not
// ready yet and the exponential backoff would delay the reconnection by a lot.
export const BACK_ONLINE_RECONNECT_DELAY = 5000;

/**
 * Communicate with a SharedWorker in order to provide a single websocket
 * connection shared across multiple tabs.
 *
 *  @emits BUS:CONNECT
 *  @emits BUS:DISCONNECT
 *  @emits BUS:RECONNECT
 *  @emits BUS:RECONNECTING
 *  @emits BUS:WORKER_STATE_UPDATED
 *  @emits BUS:OUTDATED
 */
export class BusPlugin extends Plugin {
    multiTab = usePlugin(MultiTabPlugin);
    params = usePlugin(BusParametersPlugin);
    workerService = usePlugin(WorkerPlugin);
    env = useEnv();

    /** @type {?Promise<void>} */
    workerInitPromise = null;
    /** @type {(value?: void) => void | null} */
    resolveWorkerInit = null;
    startedAt = null;
    backOnlineTimeout = null;
    isActive = signal(false);
    workerState = signal(null);

    /** @private */
    bus = new EventBus();
    /** @private */
    notificationBus = new EventBus();
    /** @private */
    subscribeFnToWrapper = new Map();

    setup() {
        this.startedAt = luxon.DateTime.now().set({ milliseconds: 0 });

        useListener(browser, "pagehide", ({ persisted }) => {
            if (!persisted) {
                // Page is gonna be unloaded, disconnect this client
                // from the worker.
                this.workerService.send("BUS:LEAVE");
            }
        });
        useListener(
            browser,
            "online",
            () => {
                this.backOnlineTimeout = browser.setTimeout(() => {
                    if (this.isActive()) {
                        this.workerService.send("BUS:START");
                    }
                }, BACK_ONLINE_RECONNECT_DELAY);
            },
            { capture: true }
        );
        useListener(
            browser,
            "offline",
            () => {
                clearTimeout(this.backOnlineTimeout);
                this.workerService.send("BUS:STOP");
            },
            {
                capture: true,
            }
        );
    }

    /**
     * Handle messages received from the shared worker and fires an
     * event according to the message type.
     *
     * @param {MessageEvent} messageEv
     * @param {{type: WorkerEvent, data: any}[]}  messageEv.data
     */
    handleMessage(messageEv) {
        const { type, data } = messageEv.data;
        switch (type) {
            case "BUS:PROVIDE_LOGS": {
                const blob = new Blob([JSON.stringify(data, null, 2)], {
                    type: "application/json",
                });
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = `bus_logs_${luxon.DateTime.now().toFormat(
                    "yyyy-LL-dd-HH-mm-ss"
                )}.json`;
                a.click();
                URL.revokeObjectURL(url);
                break;
            }
            case "BUS:NOTIFICATION": {
                const notifications = data.map(({ id, message }) => ({ id, ...message }));
                const receivedLastId = notifications.at(-1).id;
                const lsLastId = parseInt(localStorage.getItem("bus.last_notification_id") ?? 0);
                if (receivedLastId > lsLastId) {
                    localStorage.setItem("bus.last_notification_id", receivedLastId);
                }
                for (const { id, type, payload } of notifications) {
                    this.notificationBus.trigger(type, { id, payload });
                }
                break;
            }
            case "BUS:INITIALIZED": {
                this.resolveWorkerInit();
                break;
            }
            case "BUS:WORKER_STATE_UPDATED":
                this.workerState.set(data);
                break;
            case "BUS:OUTDATED": {
                if (data.unregisterMultiTab) {
                    this.multiTab.unregister();
                }
                break;
            }
            case "BUS:LAST_ID_RESET":
                localStorage.setItem("bus.last_notification_id", data);
                break;
        }
        if (!INTERNAL_EVENTS.has(type)) {
            this.bus.trigger(type, data);
        }
    }

    /**
     * Start the "bus_service" workerService.
     */
    async ensureWorkerStarted() {
        if (this.workerInitPromise) {
            return this.workerInitPromise;
        }
        ({ promise: this.workerInitPromise, resolve: this.resolveWorkerInit } =
            Promise.withResolvers());
        let uid = Array.isArray(session.user_id) ? session.user_id[0] : user.userId;
        if (!uid && uid !== undefined) {
            uid = false;
        }
        await this.workerService.ensureWorkerStarted();
        await this.workerService.registerHandler((ev) => this.handleMessage(ev));
        this.workerService.send("BUS:INITIALIZE_CONNECTION", {
            websocketURL: `${this.params.serverURL().replace("http", "ws")}/websocket?version=${
                session.websocket_worker_version
            }`,
            db: session.db,
            lastNotificationId: parseInt(localStorage.getItem("bus.last_notification_id")) || 0,
            uid,
            startTs: this.startedAt.valueOf(),
        });
        return this.workerInitPromise;
    }

    addEventListener(type, listener) {
        this.bus.addEventListener(type, listener);
    }

    removeEventListener(type, listener) {
        this.bus.removeEventListener(type, listener);
    }

    async addChannel(channel) {
        await this.ensureWorkerStarted();
        this.workerService.send("BUS:ADD_CHANNEL", channel);
        this.workerService.send("BUS:START");
        this.isActive.set(true);
    }

    deleteChannel(channel) {
        this.workerService.send("BUS:DELETE_CHANNEL", channel);
    }

    setLoggingEnabled(isEnabled) {
        return this.workerService.send("BUS:SET_LOGGING_ENABLED", isEnabled);
    }

    downloadLogs() {
        return this.workerService.send("BUS:REQUEST_LOGS");
    }

    forceUpdateChannels() {
        return this.workerService.send("BUS:FORCE_UPDATE_CHANNELS");
    }

    send(eventName, data) {
        return this.workerService.send("BUS:SEND", { event_name: eventName, data });
    }

    async start() {
        await this.ensureWorkerStarted();
        this.workerService.send("BUS:START");
        this.isActive.set(true);
    }

    stop() {
        this.workerService.send("BUS:LEAVE");
        this.isActive.set(false);
    }

    /**
     * Subscribe to a single notification type.
     *
     * @param {string} notificationType
     * @param {function} callback
     */
    subscribe(notificationType, callback) {
        const wrapper = ({ detail }) => {
            const { id, payload } = detail;
            callback(JSON.parse(JSON.stringify(payload)), { id });
        };
        this.subscribeFnToWrapper.set(callback, wrapper);
        this.notificationBus.addEventListener(notificationType, wrapper);

        return () => this.unsubscribe(notificationType, callback);
    }

    /**
     * Unsubscribe from a single notification type.
     *
     * @param {string} notificationType
     * @param {function} callback
     */
    unsubscribe(notificationType, callback) {
        this.notificationBus.removeEventListener(
            notificationType,
            this.subscribeFnToWrapper.get(callback)
        );
        this.subscribeFnToWrapper.delete(callback);
    }
}

services.add(BusPlugin);

/**
 * -----------------------------------------------------------------------------
 * @todo owl3 migration
 * temporary - to remove when all use of the bus_service service are removed
 * -----------------------------------------------------------------------------
 */
export const busService = {
    dependencies: ["bus.parameters", "localization", "multi_tab", "worker_service"],
    start() {
        const busPlugin = usePlugin(BusPlugin);
        const busServiceWrapper = Object.create(busPlugin);
        Object.defineProperty(busServiceWrapper, "isActive", {
            get() {
                return busPlugin.isActive();
            },
        });
        Object.defineProperty(busServiceWrapper, "workerState", {
            get() {
                return busPlugin.workerState();
            },
        });
        const INTERNAL_METHODS = new Set(["constructor", "setup", "handleMessage"]);
        for (const method of Object.getOwnPropertyNames(BusPlugin.prototype)) {
            if (!INTERNAL_METHODS.has(method) && typeof busPlugin[method] === "function") {
                busServiceWrapper[method] = busPlugin[method].bind(busPlugin);
            }
        }
        return busServiceWrapper;
    },
};

registry.category("services").add("bus_service", busService);
