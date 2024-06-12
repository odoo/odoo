/* eslint-disable no-restricted-globals */
const cacheName = "odoo-sw-cache";
const cachedRequests = ["/web/offline"];

self.addEventListener("install", (event) => {
    event.waitUntil(caches.open(cacheName).then((cache) => cache.addAll(cachedRequests)));
});

const navigateOrDisplayOfflinePage = async (request) => {
    try {
        return await fetch(request);
    } catch (requestError) {
        if (
            request.method === "GET" &&
            ["Failed to fetch", "Load failed"].includes(requestError.message)
        ) {
            if (cachedRequests.includes("/web/offline")) {
                const cache = await caches.open(cacheName);
                const cachedResponse = await cache.match("/web/offline");
                if (cachedResponse) {
                    return cachedResponse;
                }
            }
        }
        throw requestError;
    }
};

self.addEventListener("fetch", (event) => {
    if (
        (event.request.mode === "navigate" && event.request.destination === "document") ||
        // request.mode = navigate isn't supported in all browsers => check for http header accept:text/html
        event.request.headers.get("accept").includes("text/html")
    ) {
        event.respondWith(navigateOrDisplayOfflinePage(event.request));
    }
});
