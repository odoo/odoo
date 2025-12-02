import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { Deferred } from "@web/core/utils/concurrency";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { EventBus, reactive } from "@odoo/owl";
import { user } from "@web/core/user";

// List of worker events that should not be broadcasted.
const INTERNAL_EVENTS = new Set([
    "BUS:INITIALIZED",
    "BUS:OUTDATED",
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
 */
export const busService = {
    dependencies: [
        "bus.parameters",
        "localization",
        "multi_tab",
        "legacy_multi_tab",
        "notification",
        "worker_service",
    ],

    start(
        env,
        {
            multi_tab: multiTab,
            legacy_multi_tab: legacyMultiTab,
            notification,
            "bus.parameters": params,
            worker_service: workerService,
        }
    ) {
        const bus = new EventBus();
        const notificationBus = new EventBus();
        const subscribeFnToWrapper = new Map();
        let backOnlineTimeout;
        const startedAt = luxon.DateTime.now().set({ milliseconds: 0 });
        let connectionInitializedDeferred;

        /**
         * Handle messages received from the shared worker and fires an
         * event according to the message type.
         *
         * @param {MessageEvent} messageEv
         * @param {{type: WorkerEvent, data: any}[]}  messageEv.data
         */
        function handleMessage(messageEv) {
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
                    state.lastNotificationId = notifications.at(-1).id;
                    legacyMultiTab.setSharedValue("last_notification_id", state.lastNotificationId);
                    for (const { id, type, payload } of notifications) {
                        notificationBus.trigger(type, { id, payload });
                        busService._onMessage(env, id, type, payload);
                    }
                    break;
                }
                case "BUS:INITIALIZED": {
                    connectionInitializedDeferred.resolve();
                    break;
                }
                case "BUS:WORKER_STATE_UPDATED":
                    state.workerState = data;
                    break;
                case "BUS:OUTDATED": {
                    multiTab.unregister();
                    notification.add(
                        _t(
                            "Save your work and refresh to get the latest updates and avoid potential issues."
                        ),
                        {
                            title: _t("The page is out of date"),
                            type: "warning",
                            sticky: true,
                            buttons: [
                                {
                                    name: _t("Refresh"),
                                    primary: true,
                                    onClick: () => {
                                        browser.location.reload();
                                    },
                                },
                            ],
                        }
                    );
                    break;
                }
            }
            if (!INTERNAL_EVENTS.has(type)) {
                bus.trigger(type, data);
            }
        }

        /**
         * Start the "bus_service" workerService.
         */
        async function ensureWorkerStarted() {
            if (!connectionInitializedDeferred) {
                connectionInitializedDeferred = new Deferred();
                let uid = Array.isArray(session.user_id) ? session.user_id[0] : user.userId;
                if (!uid && uid !== undefined) {
                    uid = false;
                }
                await workerService.ensureWorkerStarted();
                await workerService.registerHandler(handleMessage);
                workerService.send("BUS:INITIALIZE_CONNECTION", {
                    websocketURL: `${params.serverURL.replace("http", "ws")}/websocket?version=${
                        session.websocket_worker_version
                    }`,
                    db: session.db,
                    debug: odoo.debug,
                    lastNotificationId: legacyMultiTab.getSharedValue("last_notification_id", 0),
                    uid,
                    startTs: startedAt.valueOf(),
                });
            }
            await connectionInitializedDeferred;
        }

        browser.addEventListener("pagehide", ({ persisted }) => {
            if (!persisted) {
                // Page is gonna be unloaded, disconnect this client
                // from the worker.
                workerService.send("BUS:LEAVE");
            }
        });
        browser.addEventListener(
            "online",
            () => {
                backOnlineTimeout = browser.setTimeout(() => {
                    if (state.isActive) {
                        workerService.send("BUS:START");
                    }
                }, BACK_ONLINE_RECONNECT_DELAY);
            },
            { capture: true }
        );
        browser.addEventListener(
            "offline",
            () => {
                clearTimeout(backOnlineTimeout);
                workerService.send("BUS:STOP");
            },
            {
                capture: true,
            }
        );
        const state = reactive({
            addEventListener: bus.addEventListener.bind(bus),
            addChannel: async (channel) => {
                await ensureWorkerStarted();
                workerService.send("BUS:ADD_CHANNEL", channel);
                workerService.send("BUS:START");
                state.isActive = true;
            },
            deleteChannel: (channel) => {
                workerService.send("BUS:DELETE_CHANNEL", channel);
            },
            setLoggingEnabled: (isEnabled) =>
                workerService.send("BUS:SET_LOGGING_ENABLED", isEnabled),
            downloadLogs: () => workerService.send("BUS:REQUEST_LOGS"),
            forceUpdateChannels: () => workerService.send("BUS:FORCE_UPDATE_CHANNELS"),
            trigger: bus.trigger.bind(bus),
            removeEventListener: bus.removeEventListener.bind(bus),
            send: (eventName, data) =>
                workerService.send("BUS:SEND", { event_name: eventName, data }),
            start: async () => {
                await ensureWorkerStarted();
                workerService.send("BUS:START");
                state.isActive = true;
            },
            stop: () => {
                workerService.send("BUS:LEAVE");
                state.isActive = false;
            },
            isActive: false,
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
                subscribeFnToWrapper.set(callback, wrapper);
                notificationBus.addEventListener(notificationType, wrapper);
            },
            /**
             * Unsubscribe from a single notification type.
             *
             * @param {string} notificationType
             * @param {function} callback
             */
            unsubscribe(notificationType, callback) {
                notificationBus.removeEventListener(
                    notificationType,
                    subscribeFnToWrapper.get(callback)
                );
                subscribeFnToWrapper.delete(callback);
            },
            startedAt,
            workerState: null,
            /** The id of the last notification received by this tab. */
            lastNotificationId: null,
        });
        return state;
    },
    /** Overriden to provide logs in tests. Use subscribe() in production. */
    _onMessage(env, id, type, payload) {},
};
registry.category("services").add("bus_service", busService);
