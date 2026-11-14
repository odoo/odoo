// @odoo-module ignore
/* eslint-disable no-restricted-globals */
/* eslint-disable no-undef */

const cacheName = "odoo-pos-cache";

const fetchCacheRespond = async (event) => {
    const cache = await caches.open(cacheName);
    try {
        const response = await fetch(event.request);
        // A server error (500) or a proxy in front of a stopped server (502, 503)
        // is handled like a network drop: open the cached page, never cache it.
        if (response.status >= 500) {
            return (await cache.match(event.request)) || response;
        }
        if (response.ok) {
            cache.put(event.request, response.clone());
        }
        return response;
    } catch {
        return await cache.match(event.request);
    }
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
        url.includes("Cashdro3WS/index3.php") ||
        event.request.headers.get("X-No-SW-Cache") ||
        event.request.method !== "GET"
    ) {
        return;
    }

    event.respondWith(fetchCacheRespond(event));
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
