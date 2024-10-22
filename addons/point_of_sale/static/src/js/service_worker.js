// @odoo-module ignore

/* eslint-disable no-restricted-globals */
const cacheName = "pos-sw-cache";
const dbName = "posDataDB";
const storeName = "loadDataStore";
const offlinePageRequest = ["/odoo/offline"];
const closeSessionUrl = "/web/dataset/call_kw/pos.session/delete_opening_control_session";

self.addEventListener("install", (event) => {
    event.waitUntil(caches.open(cacheName).then((cache) => cache.addAll(offlinePageRequest)));
    event.waitUntil(initIndexedDB());
});

const initIndexedDB = () => {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(dbName, 1);
        request.onupgradeneeded = (event) => {
            const db = event.target.result;
            db.createObjectStore(storeName, { keyPath: "id" });
        };
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
};

const saveToIndexedDB = async (keyName, data) => {
    const db = await initIndexedDB();
    const transaction = db.transaction(storeName, "readwrite");
    const store = transaction.objectStore(storeName);
    store.put({ id: keyName, data });
};

const getFromIndexedDB = async (keyName) => {
    const db = await initIndexedDB();
    return new Promise((resolve, reject) => {
        const transaction = db.transaction(storeName, "readonly");
        const store = transaction.objectStore(storeName);
        const request = store.get(keyName);
        request.onsuccess = () => resolve(request.result ? request.result.data : null);
        request.onerror = () => reject(request.error);
    });
};

const clearAllData = async () => {
    // Clear cache
    const cache = await caches.open(cacheName);
    await cache.keys().then((keys) => Promise.all(keys.map((key) => cache.delete(key))));

    // Clear IndexedDB
    const db = await initIndexedDB();
    const transaction = db.transaction(storeName, "readwrite");
    transaction.objectStore(storeName).clear();
};

self.addEventListener("fetch", (event) => {
    const { request } = event;
    // To clear indexeddb and cache when session is closed , note - it will only clear when we close the session
    if (request.url.includes(closeSessionUrl)) {
        event.waitUntil(clearAllData());
        return;
    }

    if (request.method === "POST") {
        event.respondWith(handlePostRequest(request));
    } else if (request.method === "GET" && !request.url.startsWith("chrome-extension://")) {
        event.respondWith(handleGetRequest(request));
    } else {
        event.respondWith(fetch(request).catch(() => caches.match("/odoo/offline")));
    }
});

const generateCompositeKey = (requestPayload) => {
    const { params } = requestPayload;
    const model = params?.model || "";
    const method = params?.method || "";
    const context = params?.kwargs?.context || {};
    const companyIds = context.allowed_company_ids || [];

    const keyParts = [
        model,
        method,
        JSON.stringify(params?.args || []),
        JSON.stringify(params?.kwargs?.domain || []),
        companyIds.join("-"),
    ];

    return keyParts.join("-");
};

const handlePostRequest = async (request) => {
    const requestClone = request.clone();
    const payload = await requestClone.json();
    const keyName = generateCompositeKey(payload);
    try {
        const response = await fetch(request);
        const responseData = await response.clone().json();
        await saveToIndexedDB(keyName, responseData);
        return response;
    } catch {
        const cachedData = await getFromIndexedDB(keyName);
        if (cachedData) {
            return new Response(JSON.stringify(cachedData), {
                headers: { "Content-Type": "application/json" },
            });
        }

        const offlineResponse = await caches.match("/odoo/offline");
        return offlineResponse || new Response("Offline", { status: 503 });
    }
};

const refactorURl = (url) => {
    const urlObj = new URL(url);
    if (urlObj.pathname === "/pos/ui" && urlObj.searchParams.has("from_backend")) {
        urlObj.searchParams.delete("from_backend");
    }
    return urlObj.toString();
};

const handleGetRequest = async (request) => {
    const cache = await caches.open(cacheName);
    const posURL = refactorURl(request.url);
    try {
        const networkResponse = await fetch(request);
        cache.put(posURL, networkResponse.clone());
        return networkResponse;
    } catch {
        const cachedResponse = await cache.match(posURL);
        if (cachedResponse) {
            return cachedResponse;
        }

        const offlineResponse = await caches.match("/odoo/offline");
        return offlineResponse || new Response("Offline", { status: 503 });
    }
};
