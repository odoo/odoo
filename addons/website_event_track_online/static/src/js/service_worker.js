importScripts("/website_event_track_online/static/lib/idb-keyval/idb-keyval.js");

const PREFIX = "odoo-event";
const SYNCABLE_ROUTES = ["/event/track/toggle_reminder"];
const CACHABLE_ROUTES = ["/web/webclient/version_info"];

const { Store, set, get, del } = idbKeyval;
const pendingRequestsQueueName = `${PREFIX}-pending-requests`;
const cacheName = `${PREFIX}-cache`;
const syncStore = new Store(`${PREFIX}-sync-db`, `${PREFIX}-sync-store`);
const cacheStore = new Store(`${PREFIX}-cache-db`, `${PREFIX}-cache-store`);

/**
 *
 * @param {string} url
 * @returns {string}
 */
const urlPathname = (url) => new URL(url).pathname;

/**
 *
 * @param {Array} whitelist
 * @returns {Function}
 */
const canHandleRoutes = (whitelist) => (url) => whitelist.includes(urlPathname(url));

/**
 *
 * @param {Request} request
 * @returns {boolean}
 */
const isGET = (request) => request.method === "GET";

/**
 *
 * @returns {Function}
 */
const isSyncableURL = canHandleRoutes(SYNCABLE_ROUTES);

/**
 *
 * @returns {Function}
 */
const isCachableURL = canHandleRoutes(CACHABLE_ROUTES);

/**
 *
 * @param {Request} req
 * @returns {Promise<Object>}
 */
const serializeRequest = async (req) => ({
    url: req.url,
    method: req.method,
    headers: Object.fromEntries(req.headers.entries()),
    body: await req.text(),
    mode: req.mode,
    credentials: req.credentials,
    cache: req.cache,
    redirect: req.redirect,
    referrer: req.referrer,
    integrity: req.integrity,
});

/**
 *
 * @param {Object} requestData
 * @returns {Request}
 */
const deserializeRequest = (requestData) => {
    const { url } = requestData;
    delete requestData.url;
    return new Request(url, requestData);
};

/**
 *
 * @param {Response} res
 * @returns {Promise<Object>}
 */
const serializeResponse = async (res) => ({
    body: await res.text(),
    status: res.status,
    statusText: res.statusText,
    headers: Object.fromEntries(res.headers.entries()),
});

/**
 *
 * @param {Object} responseData
 * @returns {Response}
 */
const deserializeResponse = (responseData) => {
    const { body } = responseData;
    delete responseData.body;
    return new Response(body, responseData);
};

/**
 *
 * @param {Object} serializedRequest
 * @returns {string}
 */
const buildCacheKey = ({ url, body: { method, params } }) =>
    JSON.stringify({
        url,
        method,
        params,
    });

/**
 *
 * @returns {int}
 */
const uniqueRequestId = () => Math.floor(Math.random() * 1000 * 1000 * 1000);

/**
 *
 * @returns {Response}
 */
const buildEmptyResponse = () => new Response(JSON.stringify({ jsonrpc: "2.0", id: uniqueRequestId(), result: {} }));

/**
 *
 * @param {Request} request
 * @param {Response} response
 * @returns {Promise}
 */
const cacheRequest = async (request, response) => {
    if (isGET(request)) {
        const cache = await caches.open(cacheName);
        await cache.put(request, response.clone());
    } else if (isCachableURL(request.url)) {
        const serializedRequest = await serializeRequest(request);
        const serializedResponse = await serializeResponse(response.clone());
        await set(buildCacheKey(serializedRequest), serializedResponse, cacheStore);
    }
};

/**
 *
 * @param {Request} request
 * @returns {boolean}
 */
const isCachableRequest = (request) => isGET(request) || isCachableURL(request.url);

/**
 *
 * @param {Request} request
 * @returns {Promise<Response|null>}
 */
const matchCache = async (request) => {
    if (isGET(request)) {
        const cache = await caches.open(cacheName);
        const response = await cache.match(request.url);
        if (response) {
            return deserializeResponse(await serializeResponse(response.clone()));
        }
    }
    if (isCachableURL(request.url)) {
        const serializedRequest = await serializeRequest(request);
        const cachedResponse = await get(buildCacheKey(serializedRequest), cacheStore);
        if (cachedResponse) {
            return deserializeResponse(cachedResponse);
        }
    }
    return null;
};

/**
 *
 * @param {FetchEvent} param0
 * @returns {Promise<Response>}
 */
const processFetchEvent = async ({ request }) => {
    const requestCopy = request.clone();
    let response;
    try {
        response = await fetch(request);
        await cacheRequest(request, response);
    } catch (requestError) {
        if (isCachableRequest(requestCopy)) {
            response = await matchCache(requestCopy);
        } else if (isSyncableURL(requestCopy.url)) {
            const pendingRequests = (await get(pendingRequestsQueueName, syncStore)) || [];
            const serializedRequest = await serializeRequest(requestCopy);
            await set(pendingRequestsQueueName, [...pendingRequests, serializedRequest], syncStore);
            if (self.registration.sync) {
                await self.registration.sync.register(pendingRequestsQueueName).catch((err) => {
                    console.warn("Cannot use BackgroundSync", err);
                    throw requestError;
                });
            }
            return buildEmptyResponse();
        } else {
            console.warn(`Offline ${requestCopy.method} request currently not supported`, requestCopy);
        }

        if (!response) {
            throw requestError;
        }
    }
    return response;
};

/**
 *
 * @returns {Promise}
 */
const processPendingRequests = async () => {
    const pendingRequests = (await get(pendingRequestsQueueName, syncStore)) || [];
    if (!pendingRequests.length) {
        console.info("Nothing to sync!");
        return;
    }
    let pendingRequest;
    while ((pendingRequest = pendingRequests.shift())) {
        const request = deserializeRequest(pendingRequest);
        await fetch(request);
        await set(pendingRequestsQueueName, pendingRequests, syncStore);
    }
};

/**
 * Add given urls to the Cache, skipping the ones already present
 * @param {Array<string>} urls
 */
const prefetchUrls = async (urls = []) => {
    const cache = await caches.open(cacheName);
    let urlsToCache = new Set(urls);
    for (let url of urlsToCache) {
        (await cache.match(url)) ? urlsToCache.delete(url) : undefined;
    }
    return cache.addAll([...urlsToCache]);
};

/**
 * Handle the message sent to the Worker (using the postMessage() method).
 * The message is defined by the name of the action to perform and its associated parameters (optional).
 *
 * Actions:
 * - prefetch-pages: add {Array} urls with their "alternative url" to the Cache (if not already present).
 * - prefetch-assets: add {Array} urls to the Cache (if not already present).
 *
 * @param {Object} data
 * @param {string} data.action action's name
 * @param {*} data.* action's parameter(s)
 * @returns {Promise}
 */
const processMessage = (data) => {
    const { action } = data;
    switch (action) {
        case "prefetch-pages":
            const { urls: pagesUrls } = data;
            // To prevent redirection cached by the browser (cf. 301 Permanently Moved) from breaking the offline cache
            // we also add alternative urls with the following rule:
            // * if original url has a trailing "/", adds url with striped trailing "/"
            // * if original url doesn't end with "/", adds url without the trailing "/"
            const maybeRedirectedUrl = pagesUrls.map((url) => (url.endsWith("/") ? url.slice(0, -1) : url));
            return prefetchUrls([...pagesUrls, ...maybeRedirectedUrl]);
        case "prefetch-assets":
            const { urls: assetsUrls } = data;
            return prefetchUrls(assetsUrls);
    }
    throw new Error(`Action '${action}' not found.`);
};

self.addEventListener("fetch", (event) => {
    event.respondWith(processFetchEvent(event));
});

self.addEventListener("sync", (event) => {
    console.info(`Syncing pending requests...`);
    if (event.tag === pendingRequestsQueueName) {
        event.waitUntil(processPendingRequests());
    }
});

self.addEventListener("message", (event) => {
    event.waitUntil(processMessage(event.data));
});
