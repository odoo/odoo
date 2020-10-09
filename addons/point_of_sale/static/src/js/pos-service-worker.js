importScripts('/web/static/lib/idb-keyval/idb-keyval.js');
importScripts('/point_of_sale/static/src/js/PosIDB.js');

/**
 * This service worker allows reloading of POS UI without internet connection,
 * provided that it is loaded at least twice. (First load installs this service
 * worker and in the succeeding loads, the service worker caches pos data.)
 * Note we are NOT targetting offline-first functionality here, which means
 * that the priority is still the data fetched from the corresponding odoo
 * server instance.
 *
 * SOME TECHNICAL NOTE:
 * 1. GET requests are cached in `caches` (CacheStorage) with 'POS-ASSETS' as
 *    cache name. Static assets and images are from GET requests.
 * 2. POST requests are cached in IndexedDB. RPCs are POST requests.
 *
 * For 1 and 2, see `cacheTheRequest` and `getResponseFromCache`.
 */

const serializeRequest = async (req) => ({
    url: req.url,
    body: await req.json(),
});

const serializeResponse = async (res) => ({
    body: await res.text(),
    status: res.status,
    statusText: res.statusText,
    headers: Object.fromEntries(res.headers.entries()),
});

const deserializeResponse = (responseData) => {
    const { body } = responseData;
    delete responseData.body;
    return new Response(body, responseData);
};

const buildCacheKey = ({ url, body: { method, params } }) =>
    JSON.stringify({
        url,
        method,
        params,
    });

const isGET = (request) => request.method === 'GET';

const cacheTheRequest = async (request, response) => {
    if (isGET(request)) {
        const cache = await caches.open('POS-ASSETS');
        await cache.put(request.clone(), response.clone());
    } else {
        if (await PosIDB.get('stopCaching')) {
            return;
        }
        const serializedRequest = await serializeRequest(request.clone());
        const serializedResponse = await serializeResponse(response.clone());
        await PosIDB.set(buildCacheKey(serializedRequest), serializedResponse);
    }
};

const getResponseFromCache = async (request) => {
    if (isGET(request)) {
        const cache = await caches.open('POS-ASSETS');
        return await cache.match(request);
    } else {
        const serializedRequest = await serializeRequest(request);
        const cachedResponse = await PosIDB.get(buildCacheKey(serializedRequest));
        if (cachedResponse) {
            return deserializeResponse(cachedResponse);
        } else {
            throw new Error(`Unable to find ${request.url} from (idb) cache.`);
        }
    }
};

const processFetchEvent = async ({ request }) => {
    try {
        const response = await fetch(request.clone());
        await cacheTheRequest(request, response.clone());
        return response;
    } catch (fetchError) {
        try {
            return await getResponseFromCache(request);
        } catch (err) {
            console.error('An error occured when reading the request from cache.', err);
        }
    }
};

self.addEventListener('fetch', (event) => event.respondWith(processFetchEvent(event)));
