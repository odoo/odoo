// @odoo-module ignore
/* eslint-disable no-restricted-globals */
/* eslint-disable no-undef */

const cacheName = "odoo-pos-cache-v2-user-safe";

const isPosNavigationRequest = (request) => {
    if (request.mode !== "navigate") {
        return false;
    }
    try {
        const parsedUrl = new URL(request.url);
        return /\/pos\/ui\/\d+/.test(parsedUrl.pathname);
    } catch {
        return false;
    }
};

const getPosShellFallback = async (cache, requestUrl) => {
    try {
        const parsedUrl = new URL(requestUrl);
        const posMatch = parsedUrl.pathname.match(/\/pos\/ui\/(\d+)/);
        if (!posMatch) {
            return null;
        }

        const configId = posMatch[1];
        const candidates = [
            `${parsedUrl.origin}/pos/ui/${configId}`,
            `${parsedUrl.origin}/pos/ui/${configId}?from_backend=True`,
        ];

        for (const candidate of candidates) {
            const response = await cache.match(candidate);
            if (response) {
                return response;
            }
        }
    } catch {
        // Ignore URL parsing failures.
    }

    return null;
};

const fetchCacheRespond = async (event) => {
    // Shared-device safety: never serve cached POS HTML for navigation.
    // A cached shell can bootstrap with stale route/user context.
    if (isPosNavigationRequest(event.request)) {
        try {
            return await fetch(event.request, { cache: "no-store" });
        } catch {
            return new Response("", { status: 503, statusText: "Service Unavailable" });
        }
    }

    const cache = await caches.open(cacheName);

    let response;
    try {
        response = await fetch(event.request);
    } catch {
        const cachedResponse =
            (await cache.match(event.request)) ||
            (await cache.match(event.request, { ignoreSearch: true }));

        if (cachedResponse) {
            return cachedResponse;
        }

        if (event.request.mode === "navigate") {
            const fallbackShell = await getPosShellFallback(cache, event.request.url);
            if (fallbackShell) {
                return fallbackShell;
            }
        }

        return new Response("", { status: 503, statusText: "Service Unavailable" });
    }

    try {
        await cache.put(event.request, response.clone());
    } catch (error) {
        console.info("Failed to cache response", event.request.url, error);
    }

    return response;
};

const cacheResources = async (event) => {
    const url = event.request.url;

    try {
        const cache = await caches.open(cacheName);
        await cache.add(url);
    } catch (error) {
        console.info("Failed to cache resource", url, error);
    }
};

self.addEventListener("fetch", (event) => {
    const url = event.request.url;

    // Ignore Chrome extensions and dataset. Dataset will be cached in indexedDB.
    if (
        url.includes("extension") ||
        url.includes("web/dataset") ||
        url.includes("hw_proxy/hello") ||
        url.includes("Cashdro3WS/index3.php") ||
        event.request.method !== "GET"
    ) {
        return;
    }

    event.respondWith(fetchCacheRespond(event));
});

self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(
                keys
                    .filter((key) => key.startsWith("odoo-pos-cache") && key !== cacheName)
                    .map((key) => caches.delete(key))
            )
        )
    );
});

// Handle notification
self.addEventListener("message", (event) => {
    const data = event.data;
    if (data.urlsToCache && navigator.onLine) {
        for (const url of data.urlsToCache) {
            cacheResources({ request: { url } });
        }
    }
});
