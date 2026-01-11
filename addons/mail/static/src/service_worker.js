/* eslint-env serviceworker */
/* eslint-disable no-restricted-globals */
/* global idbKeyval */
importScripts("/mail/static/lib/idb-keyval/idb-keyval.js");

const MESSAGE_TYPE = {
    UNEXPECTED_CALL_TERMINATION: "UNEXPECTED_CALL_TERMINATION", // deprecated
    POST_RTC_LOGS: "POST_RTC_LOGS",
};
const PUSH_NOTIFICATION_TYPE = {
    CALL: "CALL",
    CANCEL: "CANCEL",
};
const PUSH_NOTIFICATION_ACTION = {
    ACCEPT: "ACCEPT",
    DECLINE: "DECLINE",
};

const { Store, set, get } = idbKeyval;
const LOG_AGE_LIMIT = 24 * 60 * 60 * 1000; // 24h
let db;
const unread_store = new Store("odoo-mail-unread-db", "odoo-mail-unread-store");
let interactionSinceCleanupCount = 0;

async function openDatabase() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open("RtcLogsDB", 1);
        request.onupgradeneeded = function (event) {
            const db = event.target.result;
            if (!db.objectStoreNames.contains("logs")) {
                const store = db.createObjectStore("logs", { keyPath: "id", autoIncrement: true });
                store.createIndex("timestamp", "timestamp", { unique: false });
            }
        };
        request.onsuccess = async function (event) {
            db = event.target.result;
            try {
                await cleanupLogs(db);
            } catch (error) {
                console.error("Error cleaning up logs:", error);
            }
            resolve(db);
        };
        request.onerror = function (event) {
            reject(event.target.error);
        };
    });
}

self.addEventListener("activate", (event) => {
    event.waitUntil(openDatabase());
});

async function cleanupLogs(dataBase) {
    const cutoffTime = Date.now() - LOG_AGE_LIMIT;
    return new Promise((resolve, reject) => {
        const tx = dataBase.transaction("logs", "readwrite");
        const store = tx.objectStore("logs");
        const index = store.index("timestamp");
        const range = IDBKeyRange.upperBound(cutoffTime);
        const request = index.openCursor(range);
        request.onsuccess = (event) => {
            const cursor = event.target.result;
            if (cursor) {
                cursor.delete();
                cursor.continue();
            }
        };
        request.onerror = (event) => reject(event.target.error);
        tx.oncomplete = () => resolve();
        tx.onerror = (event) => reject(event.target.error);
    });
}

async function storeLogs(logs, { download = false } = {}) {
    if (!db) {
        await openDatabase();
    }
    if (interactionSinceCleanupCount > 30) {
        // cleanup logs in case the service worker lives for a long time
        interactionSinceCleanupCount = 0;
        await cleanupLogs(db);
    }
    interactionSinceCleanupCount++;
    return new Promise((resolve, reject) => {
        let output;
        const tx = db.transaction("logs", "readwrite");
        const store = tx.objectStore("logs");
        for (const log of logs) {
            if (!log) {
                continue;
            }
            const { type, entry, value } = log;
            const request = store.add({
                type: type,
                entry: entry,
                value: value,
                timestamp: Date.now(),
            });
            request.onerror = (event) => reject(event.target.error);
        }
        if (download) {
            const request = store.getAll();
            request.onsuccess = () => {
                const allLogs = request.result;
                const timelines = {};
                const snapshots = {};
                allLogs.forEach((log) => {
                    if (log.type === "timeline") {
                        timelines[log.entry] = log.value;
                    } else if (log.type === "snapshot") {
                        snapshots[log.entry] = log.value;
                    }
                });
                request.onerror = (event) => reject(event.target.error);
                output = { timelines, snapshots };
            };
        }
        tx.oncomplete = () => resolve(output);
        tx.onerror = (event) => reject(event.target.error);
    });
}

/**
 * @param {number} channelId id of the mail discuss channel
 * @param {Object} param1
 * @param {string} [param1.action] odoo client action
 * @param {boolean} [param1.joinCall] whether we want to join a call on that channel
 * @param {Client | ServiceWorker | MessagePort} [source] if set, will not open the channel on the source
 */
async function openDiscussChannel(channelId, { action, joinCall = false, source } = {}) {
    const discussURLRegexes = [new RegExp("/odoo/discuss")];
    if (action) {
        discussURLRegexes.push(
            new RegExp(`/odoo/\\d+/action-${action}`),
            new RegExp(`/odoo/action-${action}`)
        );
    }
    let targetClient;
    for (const client of await self.clients.matchAll({
        type: "window",
        includeUncontrolled: true,
    })) {
        if (source && source.id === client.id) {
            continue;
        }
        if (!targetClient || discussURLRegexes.some((r) => r.test(new URL(client.url).pathname))) {
            targetClient = client;
        }
    }
    if (targetClient) {
        targetClient.postMessage({ action: "OPEN_CHANNEL", data: { id: channelId, joinCall } });
        targetClient.focus().catch();
        return;
    }
    if (action) {
        const url = new URL(`/odoo/action-${action}`, location.origin);
        url.searchParams.set("active_id", `discuss.channel_${channelId}`);
        if (joinCall) {
            url.searchParams.set("call", "accept");
        }
        await self.clients.openWindow(url.toString());
    }
}

self.addEventListener("notificationclick", (event) => {
    event.notification.close();
    if (event.notification.data) {
        const { action, model, res_id } = event.notification.data;
        if (model === "discuss.channel") {
            if (event.action === PUSH_NOTIFICATION_ACTION.DECLINE) {
                event.waitUntil(
                    fetch("/mail/rtc/channel/leave_call", {
                        headers: { "Content-type": "application/json" },
                        body: JSON.stringify({
                            id: 1,
                            jsonrpc: "2.0",
                            method: "call",
                            params: { channel_id: res_id },
                        }),
                        method: "POST",
                        mode: "cors",
                        credentials: "include",
                    })
                );
                return;
            }
            event.waitUntil(
                openDiscussChannel(res_id, {
                    action,
                    joinCall: event.action === PUSH_NOTIFICATION_ACTION.ACCEPT,
                })
            );
        } else {
            const modelPath = model.includes(".") ? model : `m-${model}`;
            event.waitUntil(clients.openWindow(`/odoo/${modelPath}/${res_id}`));
        }
    }
});
self.addEventListener("push", async (event) => {
    const notification = event.data.json();
    switch (notification.options?.data?.type) {
        case PUSH_NOTIFICATION_TYPE.CALL:
            if (notification.options.actions && navigator.userAgent.includes("Android")) {
                // action "accept" is disabled on mobile until: https://issues.chromium.org/issues/40286493 is fixed.
                delete notification.options.actions.accept;
            }
            event.waitUntil(
                self.registration.showNotification(notification.title, notification.options || {})
            );
            return;
        case PUSH_NOTIFICATION_TYPE.CANCEL: {
            const notifications = await self.registration.getNotifications({
                tag: notification.options?.tag,
            });
            for (const notification of notifications) {
                notification.close();
            }
            return;
        }
    }
    event.waitUntil(handlePushEvent(notification));
});

/** @type {Map<string, Function>} string is correlationId and Function is handler */
self.handlePushEventMessageFns = new Map();

self.addEventListener("message", ({ data }) => {
    const { type, payload } = data;
    if (type === "notification-display-response") {
        const fn = self.handlePushEventMessageFns.get(payload.correlationId);
        if (fn) {
            self.handlePushEventMessageFns.delete(payload.correlationId);
            fn({ data });
        }
    }
});

async function incrementUnread() {
    const oldCounter = (await get("unread", unread_store)) ?? 0;
    const newCounter = oldCounter + 1;
    set("unread", newCounter, unread_store);
    navigator.setAppBadge?.(newCounter);
}

async function handlePushEvent(notification) {
    const { model, res_id } = notification.options?.data || {};
    const correlationId = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    let timeoutId;
    let promResolve;
    const onHandlePushEventMessage = ({ data = {} }) => {
        const { type, payload } = data;
        if (type === "notification-display-response" && payload.correlationId === correlationId) {
            clearTimeout(timeoutId);
            promResolve?.();
        }
    };
    return new Promise((resolve) => {
        promResolve = resolve;
        self.handlePushEventMessageFns.set(correlationId, onHandlePushEventMessage);
        self.clients.matchAll({ includeUncontrolled: true, type: "window" }).then((clients) => {
            clients.forEach((client) =>
                client.postMessage({
                    type: "notification-display-request",
                    payload: { correlationId, model, res_id },
                })
            );
        });
        timeoutId = setTimeout(async () => {
            await incrementUnread();
            self.clients.matchAll({ includeUncontrolled: true, type: "window" }).then((clients) => {
                clients.forEach((client) =>
                    client.postMessage({
                        type: "notification-displayed",
                        payload: { model, res_id },
                    })
                );
            });
            resolve(self.registration.showNotification(notification.title, notification.options));
        }, 500);
    });
}
self.addEventListener("pushsubscriptionchange", async (event) => {
    if (!event.oldSubscription) {
        return;
    }
    const subscription = await self.registration.pushManager.subscribe(
        event.oldSubscription.options
    );
    await fetch("/web/dataset/call_kw/mail.push.device/register_devices", {
        headers: {
            "Content-type": "application/json",
        },
        body: JSON.stringify({
            id: 1,
            jsonrpc: "2.0",
            method: "call",
            params: {
                model: "mail.push.device",
                method: "register_devices",
                args: [],
                kwargs: {
                    ...subscription.toJSON(),
                    previousEndpoint: event.oldSubscription.endpoint,
                },
                context: {},
            },
        }),
        method: "POST",
        mode: "cors",
        credentials: "include",
    });
});
self.addEventListener("message", async ({ data, source }) => {
    switch (data.name) {
        case MESSAGE_TYPE.UNEXPECTED_CALL_TERMINATION:
            // deprecated
            openDiscussChannel(data.channelId, { joinCall: true, source });
            break;
        case MESSAGE_TYPE.POST_RTC_LOGS: {
            const { logs, download } = data;
            try {
                const data = await storeLogs(logs, { download });
                if (download) {
                    source.postMessage({
                        action: "POST_RTC_LOGS",
                        data,
                    });
                }
            } catch (error) {
                console.error("Error storing log:", error);
            }
            break;
        }
    }
});
