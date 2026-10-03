// @odoo-module ignore

/* eslint-disable no-restricted-globals */
const cacheName = "odoo-sw-cache";
const homepageURL = "/odoo";
const offLineURL = `${homepageURL}/offline`;

let sessionInfo = null;

self.addEventListener("install", (event) => {
    self.skipWaiting();
    event.waitUntil(
        Promise.all([
            // Needed because the sw is register after the initial fetch
            fetch(homepageURL).then((res) => (res.ok ? storeDataOnCache(homepageURL, res) : null)),
            // offLine Page
            caches.open(cacheName).then((cache) => cache.add(offLineURL)),
        ])
    );
});

self.addEventListener("activate", (event) => {
    event.waitUntil(self.clients.claim());
});

const extractSessionInfo = (htmlContent) => {
    const match = htmlContent.match(/odoo\.__session_info__\s*=\s*({.*?});/s);
    return match && match[1] ? match[1] : null;
};

const getTextFromResponse = async (response) => {
    const reader = response.clone().body.getReader();
    const decoder = new TextDecoder();
    let result = "";
    async function read() {
        const { value, done } = await reader.read();
        if (done) {
            reader.releaseLock();
            return;
        }
        result += decoder.decode(value, { stream: true });
        await read();
    }
    await read();
    return result;
};

const storeDataOnCache = async (url, response) => {
    const htmlBody = await getTextFromResponse(response);
    // store on ram, the session info
    sessionInfo = extractSessionInfo(htmlBody);
    const cache = await caches.open(cacheName);
    return cache.put(
        url.endsWith(offLineURL) ? url : homepageURL,
        new Response(htmlBody.replace(sessionInfo, "@@@session_info_secret@@@"), {
            headers: response.headers,
        })
    );
};

const readDataOnCache = async (url) => {
    const cache = await caches.open(cacheName);
    const response = await cache.match(url);
    if (url === offLineURL) {
        return response;
    }
    // if you come from /odoo to project the url is now /odoo/project, but it doesn't exist in cache so use /odoo instead
    if (!response) {
        return readDataOnCache(homepageURL);
    }
    const htmlBody = await getTextFromResponse(response);
    return new Response(htmlBody.replaceAll("@@@session_info_secret@@@", sessionInfo), {
        headers: response.headers,
    });
};

const fetchErrorMessages = [
    "Failed to fetch", // Chromium
    "Load failed", // WebKit
    "NetworkError when attempting to fetch resource.", // Firefox
];

const navigateOrDisplayOfflinePage = async (request) => {
    const isDebugAssets = new URL(request.url).searchParams.get("debug")?.includes("assets");
    try {
        const response = await fetch(request);
        if (response.ok && !isDebugAssets) {
            storeDataOnCache(request.url, response.clone());
        }
        return response;
    } catch (requestError) {
        if (
            request.method === "GET" &&
            requestError instanceof TypeError &&
            fetchErrorMessages.includes(requestError.message)
        ) {
            if (sessionInfo?.length && !isDebugAssets) {
                const cachedResponse = await readDataOnCache(request.url);
                if (cachedResponse) {
                    return cachedResponse;
                }
            }
            const offlinePage = await readDataOnCache(offLineURL);
            if (offlinePage) {
                return offlinePage;
            }
        }
        throw requestError;
    }
};

const serveShareTarget = (event) => {
    // Redirect so the user can refresh the page without resending data.
    event.respondWith(Response.redirect("/odoo?share_target=trigger"));
    event.waitUntil(
        (async () => {
            // The page sends this message to tell the service worker it's ready to receive the file.
            await waitingMessage("odoo_share_target");
            const client = await self.clients.get(event.resultingClientId || event.clientId);
            const data = await event.request.formData();
            client.postMessage({
                shared_files: data.getAll("externalMedia") || [],
                action: "odoo_share_target_ack",
            });
        })()
    );
};

self.addEventListener("fetch", (event) => {
    if (
        event.request.method === "POST" &&
        new URL(event.request.url).searchParams.has("share_target")
    ) {
        return serveShareTarget(event);
    }
    if (
        (event.request.mode === "navigate" && event.request.destination === "document") ||
        // request.mode = navigate isn't supported in all browsers => check for http header accept:text/html
        event.request.headers.get("accept").includes("text/html")
    ) {
        event.respondWith(navigateOrDisplayOfflinePage(event.request));
    }
});

/**
 * Resolvers of the pending `waitingMessage` calls, keyed by the id of the
 * client the message is expected from (`false` for any client), then by
 * awaited message.
 *
 * @type {Map<string|false, Map<string, Function[]>>}
 */
const nextMessageMap = new Map();

/**
 * Drop the resolvers waiting for `message` from `clientId`, and the client
 * entry itself once it has no awaited message left.
 *
 * @param {string|false} clientId
 * @param {string} message
 * @param {Function} [resolver] if given, only that resolver is dropped
 */
const forgetMessage = (clientId, message, resolver) => {
    const messageMap = nextMessageMap.get(clientId);
    if (!messageMap) {
        return;
    }
    const resolvers = resolver ? (messageMap.get(message) || []).filter((r) => r !== resolver) : [];
    if (resolvers.length) {
        messageMap.set(message, resolvers);
    } else {
        messageMap.delete(message);
    }
    if (!messageMap.size) {
        nextMessageMap.delete(clientId);
    }
};

/**
 * Wait for a client to post `message` to this service worker.
 *
 * @param {string} message
 * @param {string|false} [clientId] id of the client the message is expected
 *  from, `false` to resolve on the message from any client.
 * @param {Object} [options]
 * @param {AbortSignal} [options.signal] stop waiting when aborted: the
 *  returned promise rejects with the abort reason and the resolver is dropped.
 *  Pass one whenever the message may never come (e.g. the client is closed
 *  before answering), otherwise its resolver is kept for the whole lifetime of
 *  the service worker.
 * @return {Promise<void>}
 */
const waitingMessage = async (message, clientId = false, { signal } = {}) => {
    if (typeof message !== "string") {
        throw new Error("message must be a string");
    }
    if (signal?.aborted) {
        throw signal.reason;
    }
    return new Promise((resolve, reject) => {
        function settle() {
            signal?.removeEventListener("abort", onAbort);
            resolve();
        }
        function onAbort() {
            forgetMessage(clientId, message, settle);
            reject(signal.reason);
        }
        if (!nextMessageMap.has(clientId)) {
            nextMessageMap.set(clientId, new Map());
        }
        if (!nextMessageMap.get(clientId).has(message)) {
            nextMessageMap.get(clientId).set(message, []);
        }
        nextMessageMap.get(clientId).get(message).push(settle);
        signal?.addEventListener("abort", onAbort, { once: true });
    });
};

self.addEventListener("message", (event) => {
    if (typeof event.data !== "string") {
        return;
    }
    // `source` is null for a message that does not come from a client.
    const clientId = event.source?.id;
    const messageNotifiers = [
        ...(nextMessageMap.get(false)?.get(event.data) || []),
        ...(nextMessageMap.get(clientId)?.get(event.data) || []),
    ];
    if (messageNotifiers.length) {
        for (const messageNotified of messageNotifiers) {
            messageNotified();
        }
        forgetMessage(false, event.data);
        forgetMessage(clientId, event.data);
    }
    if (event.data === "user_logout") {
        sessionInfo = null;
    }
});

/**
 * Declarative push notifications.
 *
 * A push carrying `options.data.declarative` describes, as data, both the
 * notification and what clicking it does. Modules sending notifications this
 * way add no code to this script, which then only changes with the framework:
 * a new version is not installed each time a module is.
 *
 * The push is an object `{ title, options }` where `options` are the
 * Notification options (`tag` is required) and `options.data.declarative` is:
 *
 * @typedef {Object} Declarative
 * @property {1} version
 * @property {"show"|"close"} op show the notification, or close the ones
 *  shown with its tag
 * @property {number} [seq] order of the pushes of a tag: a push whose `seq`
 *  is not greater than the last one received for its tag arrived late and is
 *  dropped
 * @property {string} [key] what a shown notification stands for: a "show"
 *  whose key is the one already shown for its tag is dropped, so that
 *  re-sending the same state neither re-alerts nor brings back a
 *  notification the user dismissed
 * @property {Object<string, ClickPlan>} [on_click] what a click does, by
 *  notification action, "default" being a click on the notification itself
 *
 * @typedef {Object} ClickPlan
 * @property {string} [url="/odoo"] the windows the plan is about: the
 *  same-origin windows whose path starts with it
 * @property {ClickPlan} [if_no_window] plan run instead when none of those
 *  windows is open
 * @property {boolean} [focus] focus the most relevant of those windows, or
 *  open `url` when there is none
 * @property {{ url: string, params: Object }} [post] JSON-RPC call to a
 *  same-origin route
 * @property {Delivery} [deliver] message handed to the pages listening to a
 *  channel (see `ServiceWorkerChannelPlugin`)
 *
 * @typedef {Object} Delivery
 * @property {string} channel
 * @property {any} message
 * @property {"all"|"focused"} [to="all"] every listening page, or only the one
 *  focused or opened by the click (the first page to listen when the click
 *  focused none). A delivery is kept until a page acknowledges it, so that a
 *  page still loading receives it once it listens.
 */
(() => {
    // Shared with @web/core/browser/service_worker_channel_plugin
    const CHANNEL_NAME = "service_worker_channel";
    const DELIVER = "service_worker_channel:deliver";
    const READY = "service_worker_channel:ready";
    const ACK = "service_worker_channel:ack";

    const TAG_TTL = 24 * 60 * 60 * 1000;
    const DELIVERY_TTL = 60 * 1000;

    const channel = new BroadcastChannel(CHANNEL_NAME);

    /**
     * The worker is stopped whenever it idles, so what must outlive one event
     * (the last push of each tag, the deliveries not yet acknowledged) is
     * kept in IndexedDB, or in memory where IndexedDB is unavailable.
     *
     * @type {{ tags: Object<string, Object>, deliveries: Object<string, Object> } | null}
     */
    let state = null;
    let dbPromise = null;
    let queue = Promise.resolve();

    function openDb() {
        dbPromise ??= new Promise((resolve, reject) => {
            const request = indexedDB.open("odoo-declarative-push", 1);
            request.onupgradeneeded = () => request.result.createObjectStore("state");
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        }).catch(() => null);
        return dbPromise;
    }

    async function dbRequest(mode, makeRequest) {
        const db = await openDb();
        if (!db) {
            return undefined;
        }
        return new Promise((resolve) => {
            const request = makeRequest(db.transaction("state", mode).objectStore("state"));
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => resolve(undefined);
        });
    }

    /**
     * Run `callback` with the state, one call at a time: events are handled
     * concurrently, and each reads the state before writing it.
     */
    function withState(callback) {
        const result = queue.then(async () => {
            state ??= (await dbRequest("readonly", (store) => store.get("state"))) || {
                tags: {},
                deliveries: {},
            };
            const now = Date.now();
            for (const entries of [state.tags, state.deliveries]) {
                for (const [key, { expires }] of Object.entries(entries)) {
                    if (expires <= now) {
                        delete entries[key];
                    }
                }
            }
            try {
                return await callback(state);
            } finally {
                await dbRequest("readwrite", (store) => store.put(state, "state"));
            }
        });
        queue = result.catch(() => {});
        return result;
    }

    function getDeliveryMessage({ id, channel, message }) {
        return { type: DELIVER, id, channel, message };
    }

    async function onPush({ title, options }, declarative) {
        const tag = options.tag;
        if (declarative.version !== 1 || !tag) {
            if (declarative.op !== "close") {
                await self.registration.showNotification(title, options);
            }
            return;
        }
        await withState(async ({ tags }) => {
            const last = tags[tag];
            if (declarative.seq != null && last?.seq != null && declarative.seq <= last.seq) {
                return;
            }
            const isClose = declarative.op === "close";
            const isRepeat = !isClose && declarative.key != null && declarative.key === last?.key;
            tags[tag] = {
                seq: declarative.seq ?? last?.seq,
                key: isClose ? null : declarative.key,
                expires: Date.now() + TAG_TTL,
            };
            if (isRepeat) {
                return;
            }
            if (isClose) {
                for (const notification of await self.registration.getNotifications({ tag })) {
                    notification.close();
                }
            } else {
                await self.registration.showNotification(title, options);
            }
        });
    }

    /**
     * @param {Declarative} declarative
     * @param {string} action
     * @returns {ClickPlan|null}
     */
    function getClickPlan(declarative, action) {
        if (declarative.version !== 1) {
            return { focus: true };
        }
        const onClick = declarative.on_click || {};
        return onClick[action || "default"] || onClick.default || null;
    }

    /**
     * @param {ClickPlan} plan
     */
    async function runClickPlan(plan) {
        const url = new URL(plan.url || homepageURL, location.origin);
        if (url.origin !== location.origin) {
            return;
        }
        const windows = (
            await self.clients.matchAll({ type: "window", includeUncontrolled: true })
        ).filter((client) => new URL(client.url).pathname.startsWith(url.pathname));
        if (!windows.length && plan.if_no_window) {
            return runClickPlan(plan.if_no_window);
        }
        const focused = plan.focus ? await focusWindow(windows, url) : null;
        if (plan.post) {
            await post(plan.post);
        }
        if (plan.deliver) {
            await deliver(plan.deliver, focused);
        }
    }

    /**
     * @param {WindowClient[]} windows
     * @param {URL} url
     * @returns {Promise<WindowClient|null>}
     */
    async function focusWindow(windows, url) {
        const client = windows.find((c) => c.visibilityState === "visible") || windows[0];
        try {
            return client ? await client.focus() : await self.clients.openWindow(url.href);
        } catch {
            // Focusing or opening is only allowed for a while after the click.
            return client || null;
        }
    }

    async function post({ url, params }) {
        const target = new URL(url, location.origin);
        if (target.origin !== location.origin) {
            return;
        }
        try {
            await fetch(target, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ jsonrpc: "2.0", method: "call", params }),
            });
        } catch {
            // Best effort: nothing can be retried once the click is handled.
        }
    }

    /**
     * @param {Delivery} delivery
     * @param {WindowClient|null} focused
     */
    async function deliver({ channel: channelName, message, to = "all" }, focused) {
        const delivery = {
            id: crypto.randomUUID(),
            channel: channelName,
            message,
            // Page expected to act on it: "all", the focused one, or null
            // for the first page to listen when the click focused none.
            recipient: to === "focused" ? focused?.id ?? null : "all",
            expires: Date.now() + DELIVERY_TTL,
        };
        await withState(({ deliveries }) => {
            deliveries[delivery.id] = delivery;
        });
        // A page still loading misses this message: it gets the delivery
        // again once it announces it listens (see `onReady`).
        if (delivery.recipient === "all") {
            channel.postMessage(getDeliveryMessage(delivery));
        } else if (focused) {
            focused.postMessage(getDeliveryMessage(delivery));
        }
    }

    /**
     * A page started listening to `channelName`: hand it the deliveries it
     * may have missed while loading.
     *
     * @param {string} channelName
     * @param {Client} client
     */
    async function onReady(channelName, client) {
        const missed = await withState(async ({ deliveries }) => {
            const result = [];
            for (const delivery of Object.values(deliveries)) {
                if (delivery.channel !== channelName) {
                    continue;
                }
                if (delivery.recipient !== "all" && delivery.recipient !== client.id) {
                    // Only one page must act: this one, unless the page the
                    // delivery was meant for is still open.
                    if (delivery.recipient && (await self.clients.get(delivery.recipient))) {
                        continue;
                    }
                    delivery.recipient = client.id;
                }
                result.push(delivery);
            }
            return result;
        });
        for (const delivery of missed) {
            client.postMessage(getDeliveryMessage(delivery));
        }
    }

    // These listeners are registered before the ones of the scripts appended
    // to this one (mail): they stop the declarative events from reaching them.
    self.addEventListener("push", (event) => {
        let notification;
        try {
            notification = event.data?.json();
        } catch {
            return;
        }
        const declarative = notification?.options?.data?.declarative;
        if (!declarative) {
            return;
        }
        event.stopImmediatePropagation();
        event.waitUntil(onPush(notification, declarative));
    });

    self.addEventListener("notificationclick", (event) => {
        const declarative = event.notification.data?.declarative;
        if (!declarative) {
            return;
        }
        event.stopImmediatePropagation();
        event.notification.close();
        const plan = getClickPlan(declarative, event.action);
        if (plan) {
            event.waitUntil(runClickPlan(plan));
        }
    });

    self.addEventListener("message", (event) => {
        const { data, source } = event;
        if (data?.type === READY && source) {
            event.waitUntil(onReady(data.channel, source));
        } else if (data?.type === ACK) {
            event.waitUntil(
                withState(({ deliveries }) => {
                    delete deliveries[data.id];
                })
            );
        }
    });
})();
