// @odoo-module ignore

/* eslint-disable no-restricted-globals */
const cacheName = "odoo-sw-cache";
const cachedRequests = ["/odoo/offline"];

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
            if (cachedRequests.includes("/odoo/offline")) {
                const cache = await caches.open(cacheName);
                const cachedResponse = await cache.match("/odoo/offline");
                if (cachedResponse) {
                    return cachedResponse;
                }
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
});

class DiskCache {
    constructor(name) {
        this.name = name;
        this._tables = new Set();
        this._version = undefined;
    }

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------

    /**
     * Defines a table to add to the cache.
     *
     * @param {string} name the name of the table
     * @param {string|number} version the version of the table: if the table already exists for a
     *  different version, it will be invalidated
     */
    async defineTable(name, version) {
        this._tables.add(name);
        return this._execute((db) => {
            if (db) {
                return this._checkVersion(db, name, version);
            }
        });
    }

    /**
     * Reads data from a given table.
     *
     * @param {string} table
     * @param {string} key
     * @returns Promise
     */
    async read(table, key) {
        return this._execute((db) => {
            if (db) {
                return this._read(db, table, key);
            }
        });
    }

    /**
     * Inserts data into the given table
     *
     * @param {string} table
     * @param {string} key
     * @param  {any} value
     * @returns Promise
     */
    async insert(table, key, value) {
        return this._execute((db) => {
            if (db) {
                this._insert(db, table, value, key);
            }
        });
    }

    /**
     * Invalidates a table, or the whole cache.
     *
     * @param {string} [table] if not given, the whole cache is invalidated
     * @returns Promise
     */
    async invalidate(table = null) {
        return this._execute((db) => {
            if (db) {
                return this._invalidate(db, table);
            }
        });
    }

    // -------------------------------------------------------------------------
    // Protected
    // -------------------------------------------------------------------------

    async _checkVersion(db, table, version) {
        const currentVersion = await this._read(db, table, "__version__");
        if (version !== currentVersion) {
            await this._invalidate(db, table);
            return this._insert(db, table, version, "__version__");
        }
    }

    async _execute(callback) {
        return new Promise((resolve) => {
            const request = indexedDB.open(this.name, this._version);
            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                const dbTables = new Set(db.objectStoreNames);
                const newTables = this._tables.difference(dbTables);
                newTables.forEach((table) => db.createObjectStore(table));
            };
            request.onsuccess = (event) => {
                const db = event.target.result;
                this._version = db.version;
                const dbTables = new Set(db.objectStoreNames);
                const newTables = this._tables.difference(dbTables);
                if (newTables.size !== 0) {
                    db.close();
                    this._version++;
                    return this._execute(callback).then(resolve);
                }
                Promise.resolve(callback(db)).then((result) => {
                    db.close();
                    resolve(result);
                });
            };
            request.onerror = (event) => {
                console.error(`IndexedDB error: ${event.target.error?.message}`);
                Promise.resolve(callback()).then(resolve);
            };
        });
    }

    async _insert(db, table, record, key) {
        return new Promise((resolve, reject) => {
            const transaction = db.transaction(table, "readwrite");
            const objectStore = transaction.objectStore(table);
            const request = objectStore.put(record, key); // put to allow updates
            request.onsuccess = resolve;
            transaction.onerror = () => reject(transaction.error);
        });
    }

    async _invalidate(db, table) {
        return new Promise((resolve, reject) => {
            const tables = table ? [table] : [...db.objectStoreNames];
            const transaction = db.transaction(tables, "readwrite");
            const proms = tables.map(
                (table) =>
                    new Promise((resolve) => {
                        const objectStore = transaction.objectStore(table);
                        const request = objectStore.clear();
                        request.onsuccess = resolve;
                    })
            );
            transaction.onerror = () => reject(transaction.error);
            Promise.all(proms).then(resolve);
        });
    }

    async _read(db, table, key) {
        return new Promise((resolve, reject) => {
            const transaction = db.transaction(table, "readonly");
            const objectStore = transaction.objectStore(table);
            const r = objectStore.get(key);
            r.onsuccess = () => resolve(r.result);
            transaction.onerror = () => reject(transaction.error);
        });
    }
}
const cache = new DiskCache("odoo");

async function cachedFetch(request, route, clientId) {
    const clonedRequest = request.clone();
    const body = await clonedRequest.text();
    const { id, jsonrpc, params } = JSON.parse(body);
    const key = `${route}(${JSON.stringify(params)})`;
    const fromCache = await cache.read("sw-cache", key);
    console.log(`${route}: load new value`);
    const fetchProm = fetch(request).then((response) => {
        const clonedResponse = response.clone();
        clonedResponse.text().then((body) => {
            console.log(`${route}: parsing response`);
            let result;
            try {
                result = JSON.parse(body).result;
            } catch {
                // pass
            }
            if (result) {
                console.log(`${route}: update cache`);
                cache.insert("sw-cache", key, result);
                if (fromCache) {
                    // FIXME: quid in case of cache miss
                    self.clients.get(clientId).then((client) =>
                        client.postMessage({
                            type: "ACTUAL_RPC_RESULT",
                            id,
                            result,
                        })
                    );
                }
            }
        });
        return response;
    });
    if (fromCache) {
        console.log(`${route}: from cache`);
        const responseBody = JSON.stringify({ id, jsonrpc, cached: true, result: fromCache });
        return new Response(responseBody, { status: 200 });
    } else {
        console.log(`${route}: cache miss`);
        return fetchProm;
    }
}

let cachedRoutes = [];
self.addEventListener("fetch", (event) => {
    const route = new URL(event.request.url).pathname;
    if (cachedRoutes.some((cachedRoute) => route.match(cachedRoute))) {
        event.respondWith(cachedFetch(event.request, route, event.clientId)); // resultingClientId ??
    }
});

self.addEventListener("message", (event) => {
    const { type } = event.data;
    if (type === "INITIALIZE-CACHES") {
        console.log(`Initializing with version ${event.data.version}`);
        cachedRoutes = event.data.cachedRoutes;
        cache.defineTable("sw-cache", event.data.version);
    }
    if (type === "CLEAR-CACHES") {
        cache.invalidate();
    }
});
