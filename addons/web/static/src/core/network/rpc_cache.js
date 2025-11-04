import { Deferred } from "@web/core/utils/concurrency";
import { IndexedDB } from "@web/core/utils/indexed_db";
import { deepCopy } from "../utils/objects";

/**
 * @typedef {{
 * callback?: function;
 * type?: "ram" | "disk";
 * update?: "once" | "always";
 * }} RPCCacheSettings
 */

function jsonEqual(v1, v2) {
    return JSON.stringify(v1) === JSON.stringify(v2);
}

function validateSettings({ type, update }) {
    if (!["ram", "disk"].includes(type)) {
        throw new Error(`Invalid "type" settings provided to RPCCache: ${type}`);
    }
    if (!["always", "once"].includes(update)) {
        throw new Error(`Invalid "update" settings provided to RPCCache: ${update}`);
    }
}

const CRYPTO_ALGO = "AES-GCM";

class Crypto {
    constructor(secret) {
        this._cryptoKey = null;
        this._ready = window.crypto.subtle
            .importKey(
                "raw",
                new Uint8Array(secret.match(/../g).map((h) => parseInt(h, 16))).buffer,
                CRYPTO_ALGO,
                false,
                ["encrypt", "decrypt"]
            )
            .then((encryptedKey) => {
                this._cryptoKey = encryptedKey;
            });
    }

    async encrypt(value) {
        await this._ready;
        // The iv must never be reused with a given key.
        const iv = window.crypto.getRandomValues(new Uint8Array(12));
        const ciphertext = await window.crypto.subtle.encrypt(
            {
                name: CRYPTO_ALGO,
                iv,
                length: 64, // length of the counter in bits
            },
            this._cryptoKey,
            new TextEncoder().encode(JSON.stringify(value)) // encoded Data
        );
        return { ciphertext, iv };
    }

    async decrypt({ ciphertext, iv }) {
        await this._ready;
        const decrypted = await window.crypto.subtle.decrypt(
            {
                name: CRYPTO_ALGO,
                iv,
                length: 64,
            },
            this._cryptoKey,
            ciphertext
        );
        return JSON.parse(new TextDecoder().decode(decrypted));
    }
}

class RamCache {
    constructor() {
        this.ram = {};
    }

    write(table, key, value) {
        if (!(table in this.ram)) {
            this.ram[table] = {};
        }
        this.ram[table][key] = value;
    }

    read(table, key) {
        return this.ram[table]?.[key];
    }

    delete(table, key) {
        delete this.ram[table]?.[key];
    }

    invalidate(tables = null) {
        if (tables) {
            tables = typeof tables === "string" ? [tables] : tables;
            for (const table of tables) {
                if (table in this.ram) {
                    this.ram[table] = {};
                }
            }
        } else {
            this.ram = {};
        }
    }
}

export class RPCCache {
    constructor(name, version, secret) {
        this.crypto = new Crypto(secret);
        this.indexedDB = new IndexedDB(name, version + CRYPTO_ALGO);
        this.ramCache = new RamCache();
        this.pendingRequests = {};
    }

    /**
     * @param {string} table
     * @param {string} key
     * @param {function} fallback
     * @param {RPCCacheSettings} settings
     */
    read(table, key, fallback, { callback = () => {}, type = "ram", update = "once" } = {}) {
        validateSettings({ type, update });

        let ramValue = this.ramCache.read(table, key);

        const requestKey = `${table}/${key}`;
        const hasPendingRequest = requestKey in this.pendingRequests;
        if (hasPendingRequest) {
            // never do the same call multiple times in parallel => return the same value for all
            // those calls, but store their callback to call them when/if the real value is obtained
            this.pendingRequests[requestKey].callbacks.push(callback);
            return ramValue.then((result) => deepCopy(result));
        }

        if (!ramValue || update === "always") {
            const request = { callbacks: [callback], invalidated: false };
            this.pendingRequests[requestKey] = request;

            // execute the fallback and write the result in the caches
            const prom = new Promise((resolve, reject) => {
                const fromCache = new Deferred();
                let fromCacheValue;
                const onFullfilled = (result) => {
                    resolve(result);
                    // call the pending request callbacks with the result
                    const hasChanged = !!fromCacheValue && !jsonEqual(fromCacheValue, result);
                    request.callbacks.forEach((cb) => cb(deepCopy(result), hasChanged));
                    if (request.invalidated) {
                        return result;
                    }
                    delete this.pendingRequests[requestKey];
                    // update the ram and optionally the disk caches with the latest data
                    this.ramCache.write(table, key, Promise.resolve(result));
                    if (type === "disk") {
                        this.crypto.encrypt(result).then((encryptedResult) => {
                            this.indexedDB.write(table, key, encryptedResult);
                        });
                    }
                    return result;
                };
                const onRejected = async (error) => {
                    await fromCache;
                    if (!request.invalidated) {
                        delete this.pendingRequests[requestKey];
                        if (!fromCacheValue) {
                            this.ramCache.delete(table, key); // remove rejected prom from ram cache
                        }
                    }
                    if (fromCacheValue) {
                        // promise has already been fullfilled with the cached value
                        throw error;
                    }
                    reject(error);
                };
                fallback().then(onFullfilled, onRejected);

                // speed up the request by using the caches
                if (ramValue) {
                    // ramValue is always already resolved here, as it can't be pending (otherwise
                    // we would have early returned because of `pendingRequests`) and it would have
                    // been removed from the ram cache if it had been rejected
                    // => no need to define a `catch` callback.
                    ramValue.then((value) => {
                        resolve(value);
                        fromCacheValue = value;
                        fromCache.resolve();
                    });
                } else if (type === "disk") {
                    this.indexedDB
                        .read(table, key)
                        .then(async (result) => {
                            if (result) {
                                let decrypted;
                                try {
                                    decrypted = await this.crypto.decrypt(result);
                                } catch {
                                    // Do nothing ! The cryptoKey is probably different.
                                    // The data will be updated with the new cryptoKey.
                                    return;
                                }
                                resolve(decrypted);
                                fromCacheValue = decrypted;
                            }
                        })
                        .finally(() => fromCache.resolve());
                } else {
                    fromCache.resolve(); // fromCacheValue will remain undefined
                }
            });
            this.ramCache.write(table, key, prom);
            ramValue = prom;
        }

        return ramValue.then((result) => deepCopy(result));
    }

    invalidate(tables) {
        this.indexedDB.invalidate(tables);
        this.ramCache.invalidate(tables);
        // flag the pending requests as invalidated s.t. we don't write their results in caches
        for (const key in this.pendingRequests) {
            this.pendingRequests[key].invalidated = true;
        }
        this.pendingRequests = {};
    }
}
