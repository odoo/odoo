importScripts("/website_event_track_online/static/lib/idb-keyval/idb-keyval.js");

const { Store, set, get } = idbKeyval;

const PREFIX = "odoo-event";
const syncStore = new Store(`${PREFIX}-db`, `${PREFIX}-sync-store`);

const isGET = (request) => request.method === "GET";
const matchRoute = (url, route) => new URL(url).pathname === route;
const queueRequests = (queue, request) => queue.then(fetch(request));

self.addEventListener("fetch", (event) => {
    event.respondWith(
        caches.open(`${PREFIX}-cache`).then(async (cache) => {
            const { request } = event;
            let response;
            try {
                response = await fetch(request);
                if (isGET(request)) {
                    await cache.put(request, response.clone());
                }
            } catch (err) {
                if (isGET(request)) {
                    response = await cache.match(request);
                } else {
                    const registration = await navigator.serviceWorker.ready;
                    if (registration.sync && matchRoute(request.url, "/event/track/toggle_wishlist")) {
                        const tag = "toggleWishlist";
                        const pending = get(tag, syncStore) || [];
                        set(tag, pending.concat(request.clone()), syncStore);
                        registration.sync.register(tag);
                        return;
                    } else {
                        console.warn(`Offline ${request.method} request currently not supported`, request);
                    }
                }
                if (!response) {
                    throw err;
                }
            }
            return response;
        })
    );
});

self.addEventListener("sync", (event) => {
    console.info(`Syncing ${event.tag}...`);
    event.waitUntil(
        get(event.tag, syncStore).then(async (pendingRequests = []) => {
            if (!pendingRequests.length) {
                console.info("Nothing to sync!");
                return;
            }
            let request;
            while ((request = pendingRequests.shift())) {
                try {
                    await fetch(request);
                    await set(event.tag, pendingRequests, syncStore);
                } catch (err) {
                    console.error(`Sync request failed`, err);
                    return;
                }
            }
        })
    );
});
