// @ts-check
/** @odoo-module native */

import { browser } from "@web/core/browser/browser";
import { reportUncaught } from "@web/core/errors/error_utils";
import { RpcEvent } from "@web/core/events";
import {
    ConnectionAbortedError,
    ConnectionLostError,
    rpcBus,
} from "@web/core/network/rpc";
import { deepCopy, deepEqual } from "@web/core/utils/collections/objects";
import { Deferred } from "@web/core/utils/concurrency";
import { IDBQuotaExceededError, IndexedDB } from "@web/core/utils/indexed_db";
import { LruCache } from "@web/core/utils/lru_cache";

/**
 * @typedef {{
 * callback?: function;
 * type?: "ram" | "disk";
 * update?: "once" | "always";
 * immutable?: boolean;
 * model?: string;
 * silent?: boolean;
 * onRequestIssued?: (request: object) => void;
 * }} RPCCacheSettings
 */

const VERSION_FIELD = "__version";

function shapeDiffers(/** @type {any} */ a, /** @type {any} */ b) {
    if (Array.isArray(a)) {
        return !Array.isArray(b) || a.length !== b.length;
    }
    if (a && typeof a === "object") {
        if (!b || typeof b !== "object" || Array.isArray(b)) {
            return true;
        }
        return Object.keys(a).length !== Object.keys(b).length;
    }
    return false;
}

/**
 * @param {any} fromCacheValue
 * @param {any} result
 * @returns {boolean}
 */
function payloadChanged(fromCacheValue, result) {
    if (fromCacheValue === result) {
        return false;
    }
    if (
        fromCacheValue &&
        result &&
        typeof fromCacheValue === "object" &&
        typeof result === "object" &&
        fromCacheValue[VERSION_FIELD] != null &&
        result[VERSION_FIELD] != null
    ) {
        return fromCacheValue[VERSION_FIELD] !== result[VERSION_FIELD];
    }
    if (shapeDiffers(fromCacheValue, result)) {
        return true;
    }
    return !deepEqual(fromCacheValue, result);
}

function checkSettings(
    /** @type {{ type: string, update: string }} */ { type, update },
) {
    if (!["ram", "disk"].includes(type)) {
        throw new Error(`Invalid "type" settings provided to RPCCache: ${type}`);
    }
    if (!["always", "once"].includes(update)) {
        throw new Error(`Invalid "update" settings provided to RPCCache: ${update}`);
    }
}

/**
 * @template T
 * @param {T} value
 * @param {WeakSet<object>} [seen]
 * @returns {T}
 */
function deepFreeze(value, seen = new WeakSet()) {
    if (value && typeof value === "object" && !Object.isFrozen(value)) {
        if (seen.has(value)) {
            return value;
        }
        seen.add(value);
        const indexable = /** @type {Record<string, unknown>} */ (value);
        for (const key of Object.keys(indexable)) {
            deepFreeze(indexable[key], seen);
        }
        Object.freeze(value);
    }
    return value;
}

const CRYPTO_ALGO = "AES-GCM";
const MAX_STORAGE_SIZE = 2 * 1024 * 1024 * 1024;

export const RAM_CACHE_MAX_ENTRIES = 10000;

class Crypto {
    /** @param {string} secret */
    constructor(secret) {
        const bytes = /** @type {string[]} */ (secret.match(/../g));
        /** @type {Promise<CryptoKey>} */
        this._key = browser.crypto.subtle.importKey(
            "raw",
            new Uint8Array(bytes.map((h) => Number.parseInt(h, 16))).buffer,
            CRYPTO_ALGO,
            false,
            ["encrypt", "decrypt"],
        );
    }

    /** @param {any} value */
    async encrypt(value) {
        const key = await this._key;
        const iv = browser.crypto.getRandomValues(new Uint8Array(12));
        const ciphertext = await browser.crypto.subtle.encrypt(
            {
                name: CRYPTO_ALGO,
                iv,
            },
            key,
            new TextEncoder().encode(JSON.stringify(value)),
        );
        return { ciphertext, iv };
    }

    async decrypt(
        /** @type {{ ciphertext: BufferSource, iv: BufferSource }} */ {
            ciphertext,
            iv,
        },
    ) {
        const key = await this._key;
        const decrypted = await browser.crypto.subtle.decrypt(
            {
                name: CRYPTO_ALGO,
                iv,
            },
            key,
            ciphertext,
        );
        return JSON.parse(new TextDecoder().decode(decrypted));
    }
}

class RamCache {
    constructor() {
        this.ram = Object.create(null);
        this.modelIndex = Object.create(null);
        this.keyModel = Object.create(null);
        this.lru = new LruCache(RAM_CACHE_MAX_ENTRIES, {
            onEvict: (/** @type {string} */ _compositeKey, /** @type {any} */ entry) =>
                this._dropEntry(entry[0], entry[1]),
        });
    }

    /**
     * @param {string} table
     * @param {string} key
     * @returns {string}
     */
    _compositeKey(table, key) {
        return `${table}\x00${key}`;
    }

    /**
     * @param {string} table
     * @param {string} key
     */
    _touchLru(table, key) {
        this.lru.set(this._compositeKey(table, key), [table, key]);
    }

    /**
     * @param {string} table
     * @param {string} key
     */
    _forgetLru(table, key) {
        this.lru.delete(this._compositeKey(table, key));
    }

    /**
     * @param {string} table
     * @param {string} key
     */
    _dropEntry(table, key) {
        delete this.ram[table]?.[key];
        const model = this.keyModel[table]?.[key];
        if (model) {
            const set = this.modelIndex[table]?.get(model);
            set?.delete(key);
            if (set && !set.size) {
                this.modelIndex[table].delete(model);
            }
            delete this.keyModel[table][key];
        }
    }

    /**
     * @param {string} table
     * @param {string} key
     * @param {any} value
     * @param {string} [model]
     */
    write(table, key, value, model) {
        if (!(table in this.ram)) {
            this.ram[table] = Object.create(null);
            this.modelIndex[table] = new Map();
            this.keyModel[table] = Object.create(null);
        }
        const prevModel = this.keyModel[table][key];
        if (prevModel && prevModel !== model) {
            const prevSet = this.modelIndex[table].get(prevModel);
            prevSet?.delete(key);
            if (prevSet && !prevSet.size) {
                this.modelIndex[table].delete(prevModel);
            }
        }
        this.ram[table][key] = value;
        if (model) {
            let set = this.modelIndex[table].get(model);
            if (!set) {
                set = new Set();
                this.modelIndex[table].set(model, set);
            }
            set.add(key);
            this.keyModel[table][key] = model;
        } else if (prevModel) {
            delete this.keyModel[table][key];
        }
        this._touchLru(table, key);
    }

    /**
     * @param {string} table
     * @param {string} key
     */
    read(table, key) {
        const value = this.ram[table]?.[key];
        if (value !== undefined) {
            this._touchLru(table, key);
        }
        return value;
    }

    /**
     * @param {string} table
     * @param {string} key
     */
    delete(table, key) {
        this._dropEntry(table, key);
        this._forgetLru(table, key);
    }

    /** @param {string | string[] | null} [tables] */
    invalidate(tables = null) {
        if (tables) {
            tables = typeof tables === "string" ? [tables] : tables;
            for (const table of tables) {
                if (table in this.ram) {
                    for (const key of Object.keys(this.ram[table])) {
                        this._forgetLru(table, key);
                    }
                    this.ram[table] = Object.create(null);
                    this.modelIndex[table] = new Map();
                    this.keyModel[table] = Object.create(null);
                }
            }
        } else {
            this.ram = Object.create(null);
            this.modelIndex = Object.create(null);
            this.keyModel = Object.create(null);
            this.lru.clear();
        }
    }

    /**
     * @param {string[]} tables
     * @param {string} model
     */
    invalidateByModel(tables, model) {
        for (const table of tables) {
            const keys = this.modelIndex[table]?.get(model);
            if (!keys || !keys.size) {
                continue;
            }
            const tableMap = this.ram[table];
            const keyMap = this.keyModel[table];
            for (const key of keys) {
                delete tableMap[key];
                delete keyMap[key];
                this._forgetLru(table, key);
            }
            this.modelIndex[table].delete(model);
        }
    }
}

export class RPCCache {
    /**
     * @param {string} name
     * @param {string | number} version
     * @param {string | null} [secret]
     */
    constructor(name, version, secret = null) {
        if (secret !== null && !/^(?:[0-9a-fA-F]{2})+$/.test(secret)) {
            throw new Error(
                `RPCCache: the disk-cache secret must be an even-length ` +
                    `hexadecimal string, or null to disable the disk cache`,
            );
        }
        this.diskEnabled = Boolean(secret && browser.crypto?.subtle);
        this.crypto = this.diskEnabled
            ? new Crypto(/** @type {string} */ (secret))
            : null;
        this.indexedDB = this.diskEnabled
            ? new IndexedDB(name, version + CRYPTO_ALGO)
            : null;
        this.ramCache = new RamCache();
        /** @type {Record<string, { callbacks: { callback: Function, shape: Function }[], invalidated: boolean, model?: string, table?: string }>} */
        this.pendingRequests = Object.create(null);
        /** @type {Record<string, number>} */
        this.diskGenerations = Object.create(null);
        this.globalDiskGeneration = 0;
        if (this.diskEnabled) {
            this.checkSize().catch((error) => {
                console.warn("RPC cache: storage size check failed", error);
            });
        }
    }

    /**
     * @param {string} table
     * @returns {number}
     */
    diskGenerationOf(table) {
        return this.globalDiskGeneration + (this.diskGenerations[table] || 0);
    }

    /** @param {string | string[] | null | undefined} tables */
    bumpDiskGeneration(tables) {
        if (tables == null) {
            this.globalDiskGeneration++;
            return;
        }
        if (typeof tables !== "string" && !Array.isArray(tables)) {
            throw new TypeError(
                "bumpDiskGeneration expects a table name, an array of names, or nullish",
            );
        }
        for (const table of typeof tables === "string" ? [tables] : tables) {
            this.diskGenerations[table] = (this.diskGenerations[table] || 0) + 1;
        }
    }

    async checkSize() {
        let estimate;
        try {
            estimate = await browser.navigator.storage.estimate();
        } catch {
            return;
        }
        const idbUsage = /** @type {any} */ (estimate).usageDetails?.indexedDB;
        if (idbUsage !== undefined) {
            if (idbUsage > MAX_STORAGE_SIZE) {
                console.warn(
                    `Deleting indexedDB database as maximum storage size is reached`,
                );
                return this.indexedDB?.deleteDatabase();
            }
            return;
        }
        if ((estimate.usage ?? 0) > MAX_STORAGE_SIZE) {
            console.warn(
                "Origin storage usage exceeds the configured maximum " +
                    "(no per-storage breakdown available); keeping the RPC " +
                    "IndexedDB cache.",
            );
        }
    }

    /**
     * @param {{ crypto: Crypto, indexedDB: IndexedDB }} useDisk
     * @param {string} table
     * @param {string} key
     * @param {any} result
     * @param {{ model?: string, request: { invalidated: boolean } }} context
     */
    _writeToDisk(useDisk, table, key, result, { model, request }) {
        const { crypto, indexedDB } = useDisk;
        const generation = this.diskGenerationOf(table);
        const version = result?.[VERSION_FIELD];
        crypto
            .encrypt(result)
            .then((encryptedResult) => {
                if (
                    request.invalidated ||
                    generation !== this.diskGenerationOf(table)
                ) {
                    return;
                }
                /** @type {Record<string, any>} */
                const stored = { ...encryptedResult };
                if (model) {
                    stored.model = model;
                }
                if (version !== undefined) {
                    stored.version = version;
                }
                indexedDB.write(table, key, stored).catch((e) => {
                    if (e instanceof IDBQuotaExceededError) {
                        indexedDB.deleteDatabase();
                    } else {
                        console.warn("RPC cache: disk write failed", e);
                    }
                });
            })
            .catch(() => {});
    }

    /**
     * @param {any} error
     * @param {boolean} silent
     */
    _reportBackgroundRefreshFailure(error, silent) {
        if (error instanceof ConnectionAbortedError) {
            return;
        }
        if (error instanceof ConnectionLostError) {
            rpcBus.trigger(RpcEvent.BACKGROUND_REFRESH_FAILED, { error });
            if (!silent) {
                reportUncaught(error);
            }
        } else {
            console.warn("RPC cache: background refresh failed", error);
        }
    }

    /**
     * @param {string} table
     * @param {string} key
     * @param {function} fallback
     * @param {{ crypto: Crypto, indexedDB: IndexedDB } | null} useDisk
     * @param {Promise<any> | undefined} ramValue
     * @param {{ callbacks: { callback: Function, shape: Function }[], invalidated: boolean, model?: string, table?: string }} request
     * @param {{ model?: string, silent: boolean }} options
     * @returns {Promise<any>}
     */
    _issue(table, key, fallback, useDisk, ramValue, request, { model, silent }) {
        const requestKey = `${table}/${key}`;
        return new Promise((resolve, reject) => {
            const fromCache = new Deferred();
            /** @type {any} */
            let fromCacheValue;
            let hasCacheValue = false;
            const onFulfilled = (/** @type {any} */ result) => {
                resolve(result);
                const hasChanged =
                    hasCacheValue &&
                    request.callbacks.length > 0 &&
                    payloadChanged(fromCacheValue, result);
                if (
                    !request.invalidated &&
                    this.pendingRequests[requestKey] === request
                ) {
                    delete this.pendingRequests[requestKey];
                    this.ramCache.write(table, key, Promise.resolve(result), model);
                    if (useDisk) {
                        this._writeToDisk(useDisk, table, key, result, {
                            model,
                            request,
                        });
                    }
                }
                for (const subscriber of request.callbacks) {
                    try {
                        subscriber.callback(subscriber.shape(result), hasChanged);
                    } catch (error) {
                        console.error("RPC cache: update callback failed", error);
                    }
                }
                return result;
            };
            const onRejected = async (/** @type {any} */ error) => {
                await fromCache;
                if (
                    !request.invalidated &&
                    this.pendingRequests[requestKey] === request
                ) {
                    delete this.pendingRequests[requestKey];
                    if (!hasCacheValue) {
                        this.ramCache.delete(table, key);
                    }
                }
                if (hasCacheValue) {
                    this._reportBackgroundRefreshFailure(error, silent);
                    return;
                }
                reject(error);
            };
            const adoptCached = (/** @type {any} */ value) => {
                resolve(value);
                fromCacheValue = value;
                hasCacheValue = true;
            };
            if (ramValue) {
                ramValue.then(
                    (/** @type {any} */ value) => {
                        adoptCached(value);
                        fromCache.resolve();
                    },
                    () => {
                        if (this.ramCache.read(table, key) === ramValue) {
                            this.ramCache.delete(table, key);
                        }
                        fromCache.resolve();
                    },
                );
            } else if (useDisk) {
                this._readFromDisk(useDisk, table, key)
                    .then((stored) => {
                        if (stored !== undefined) {
                            adoptCached(stored);
                        }
                    })
                    .finally(() => fromCache.resolve());
            } else {
                fromCache.resolve();
            }

            try {
                fallback(request).then(onFulfilled, onRejected);
            } catch (error) {
                onRejected(error);
            }
        });
    }

    /**
     * @param {{ crypto: Crypto, indexedDB: IndexedDB }} useDisk
     * @param {string} table
     * @param {string} key
     * @returns {Promise<any>}
     */
    async _readFromDisk({ crypto, indexedDB }, table, key) {
        let result;
        try {
            result = await indexedDB.read(table, key);
        } catch {
            return undefined;
        }
        if (!result) {
            return undefined;
        }
        let decrypted;
        try {
            decrypted = await crypto.decrypt(result);
        } catch {
            return undefined;
        }
        if (
            result.version !== undefined &&
            decrypted &&
            typeof decrypted === "object" &&
            decrypted[VERSION_FIELD] === undefined
        ) {
            decrypted[VERSION_FIELD] = result.version;
        }
        return decrypted;
    }

    /**
     * @param {string} table
     * @param {string} key
     * @param {function} fallback
     * @param {RPCCacheSettings} settings
     */
    read(
        table,
        key,
        fallback,
        {
            callback,
            type = "ram",
            update = "once",
            immutable = false,
            model = undefined,
            silent = false,
            onRequestIssued = undefined,
        } = {},
    ) {
        checkSettings({ type, update });
        /** @type {{ crypto: Crypto, indexedDB: IndexedDB } | null} */
        const useDisk =
            type === "disk" && this.crypto && this.indexedDB
                ? { crypto: this.crypto, indexedDB: this.indexedDB }
                : null;

        let ramValue = this.ramCache.read(table, key);

        const shape = immutable ? deepFreeze : deepCopy;

        const requestKey = `${table}/${key}`;
        const hasPendingRequest =
            Object.hasOwn(this.pendingRequests, requestKey) && ramValue !== undefined;
        if (hasPendingRequest) {
            const pending = this.pendingRequests[requestKey];
            if (callback) {
                pending.callbacks.push({ callback, shape });
            }
            return ramValue.then(shape);
        }

        if (!ramValue || update === "always") {
            const request = {
                callbacks: callback ? [{ callback, shape }] : [],
                invalidated: false,
                model,
                table,
            };
            this.pendingRequests[requestKey] = request;
            onRequestIssued?.(request);
            const prom = this._issue(table, key, fallback, useDisk, ramValue, request, {
                model,
                silent,
            });
            this.ramCache.write(table, key, prom, model);
            ramValue = prom;
        }

        return ramValue.then(shape);
    }

    /**
     * @param {string} table
     * @param {string} key
     * @param {object} [request]
     */
    abortPending(table, key, request) {
        const requestKey = `${table}/${key}`;
        if (
            Object.hasOwn(this.pendingRequests, requestKey) &&
            (request === undefined || this.pendingRequests[requestKey] === request)
        ) {
            delete this.pendingRequests[requestKey];
            this.ramCache.delete(table, key);
        }
    }

    /** @param {string | string[] | null} [tables] */
    invalidate(tables) {
        this.bumpDiskGeneration(tables);
        this.indexedDB?.invalidate(tables);
        this.ramCache.invalidate(tables);
        if (tables == null) {
            for (const key of Object.keys(this.pendingRequests)) {
                this.pendingRequests[key].invalidated = true;
            }
            this.pendingRequests = Object.create(null);
            return;
        }
        const tableList = new Set(typeof tables === "string" ? [tables] : tables);
        for (const requestKey of Object.keys(this.pendingRequests)) {
            const { table } = this.pendingRequests[requestKey];
            if (table && tableList.has(table)) {
                this.pendingRequests[requestKey].invalidated = true;
                delete this.pendingRequests[requestKey];
            }
        }
    }

    /**
     * @param {string[]} tables
     * @param {string} model
     */
    invalidateByModel(tables, model) {
        this.bumpDiskGeneration(tables);
        this.ramCache.invalidateByModel(tables, model);
        this.indexedDB?.invalidateByModel(tables, model);
        const tableSet = new Set(tables);
        for (const requestKey of Object.keys(this.pendingRequests)) {
            const request = this.pendingRequests[requestKey];
            if (
                request.model === model &&
                request.table &&
                tableSet.has(request.table)
            ) {
                request.invalidated = true;
                delete this.pendingRequests[requestKey];
            }
        }
    }

    /** @returns {Promise<void>} */
    async removeStorage() {
        await this.indexedDB?.deleteDatabase();
    }
}
