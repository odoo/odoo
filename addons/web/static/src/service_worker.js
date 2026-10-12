// @odoo-module ignore

/* eslint-disable no-restricted-globals */
const cacheName = "odoo-sw-cache";
const homepageURL = "/odoo";
const offLineURL = `${homepageURL}/offline`;

let sessionInfo = null;

self.addEventListener("install", (event) => {
    event.waitUntil(
        Promise.all([
            // Needed because the sw is register after the initial fetch
            fetch(homepageURL).then((res) => (res.ok ? storeDataOnCache(homepageURL, res) : null)),
            // offLine Page
            caches.open(cacheName).then((cache) => cache.add(offLineURL)),
        ])
    );
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
