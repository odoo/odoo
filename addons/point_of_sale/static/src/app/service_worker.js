// @odoo-module ignore
/* eslint-disable no-restricted-globals */
/* eslint-disable no-undef */

const cacheName = "odoo-pos-cache";

const cacheResources = async (event) => {
    const url = event.request.url;

    try {
        const cache = await caches.open(cacheName);
        await cache.add(url);
    } catch (error) {
        console.info("Failed to cache resource", url, error);
    }
};

const getFromCache = async (key) => {
    const cache = await caches.open(cacheName);
    return cache.match(key);
};

self.addEventListener("fetch", async (event) => {
    const url = event.request.url;

    // Ignore Chrome extensions and dataset. Dataset will be cached in indexedDB.
    if (
        url.includes("extension") ||
        url.includes("web/dataset") ||
        event.request.method !== "GET"
    ) {
        return;
    }

    event.respondWith(
        getFromCache(url).then((response) => {
            if (response && !navigator.onLine) {
                return response;
            }

            if (navigator.onLine) {
                return fetch(url).catch(() => response);
            }
        })
    );

    // Every time we fetch a resource, we try to cache it if we are online
    // This way, we can serve it from the cache if we are offline
    if (navigator.onLine) {
        await cacheResources(event);
    }
});

// Handle notification
self.addEventListener("message", async (event) => {
    const data = event.data;
    if (data.urlsToCache && navigator.onLine) {
        for (const url of data.urlsToCache) {
            cacheResources({ request: { url } });
        }
    }
});
