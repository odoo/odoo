// @odoo-module ignore

/* eslint-disable no-restricted-globals */
const cacheName = "odoo-sw-cache";
const homepageURL = "/odoo";
const offLineURL = `${homepageURL}/offline`;

let browserCacheSecret = null;

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

const userLogout = async () => {
    browserCacheSecret = null;
    const cache = await caches.open(cacheName);
    const requests = await cache.keys();
    for (const request of requests) {
        if (!request.url.endsWith(offLineURL)) {
            await cache.delete(request);
        }
    }
};

const extractSessionInfo = (htmlContent) => {
    const match = htmlContent.match(/odoo\.__session_info__\s*=\s*({.*?});/s);
    return match && match[1] ? JSON.parse(match[1]) : {};
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
    const session = extractSessionInfo(htmlBody);
    // store on ram, the crypto key
    browserCacheSecret = session.browser_cache_secret;
    const cache = await caches.open(cacheName);
    return cache.put(
        url.endsWith(offLineURL) ? url : homepageURL,
        new Response(htmlBody.replace(session.browser_cache_secret, "@@@browser_cache_secret@@@"), {
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
    // if you come from /odoo to project the url is now /odoo/project but it doesn't exist in cache so use /odoo instead
    if (!response) {
        return readDataOnCache(homepageURL);
    }
    const htmlBody = await getTextFromResponse(response);
    return new Response(htmlBody.replace("@@@browser_cache_secret@@@", browserCacheSecret), {
        headers: response.headers,
    });
};

const navigateOrDisplayOfflinePage = async (request) => {
    try {
        const response = await fetch(request);
        if (response.ok) {
            storeDataOnCache(request.url, response.clone());
        }
        return response;
    } catch (requestError) {
        if (
            request.method === "GET" &&
            ["Failed to fetch", "Load failed"].includes(requestError.message)
        ) {
            if (
                browserCacheSecret &&
                !new URL(request.url).searchParams.get("debug")?.includes("assets")
            ) {
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
 *
 * @type {Map<String, Function[]>}
 */
const nextMessageMap = new Map();
/**
 *
 * @param message : string
 * @return {Promise}
 */
const waitingMessage = async (message) =>
    new Promise((resolve) => {
        if (!nextMessageMap.has(message)) {
            nextMessageMap.set(message, []);
        }
        nextMessageMap.get(message).push(resolve);
    });

self.addEventListener("message", (event) => {
    const messageNotifiers = nextMessageMap.get(event.data);
    if (messageNotifiers) {
        for (const messageNotified of messageNotifiers) {
            messageNotified();
        }
        nextMessageMap.delete(event.data);
    }
    if (event.data === "user_logout") {
        userLogout();
    }
});
