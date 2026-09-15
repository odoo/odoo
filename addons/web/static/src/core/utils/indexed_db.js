// @ts-check
/** @odoo-module native */

import { browser } from "../browser/browser.js";
import { Mutex } from "./concurrency.js";

const VERSION_TABLE = "__DBVersion__";
const VERSION_KEY = "__version__";
const BLOCKED_DELETE_TIMEOUT = 1000;

export class IDBQuotaExceededError extends Error {}

/**
 * @param {number | undefined} size
 * @returns {string}
 */
function formatStorageSize(size) {
    if (typeof size !== "number" || !Number.isFinite(size)) {
        return "unknown";
    }
    const units = ["B", "KB", "MB", "GB"];
    let i = 0;
    while (size >= 1000 && i < units.length - 1) {
        size /= 1000;
        i++;
    }
    return `${size.toFixed(2)}${units[i]}`;
}

export class IndexedDB {
    constructor(/** @type {string} */ name, /** @type {string} */ version) {
        this.name = name;
        this._tables = new Set([VERSION_TABLE]);
        /** @type {IDBDatabase | null} */
        this._db = null;
        this._degraded = false;
        this.mutex = new Mutex();
        this.mutex
            .exec(() => this._checkVersion(version))
            .catch((error) => {
                this._degraded = true;
                console.warn(
                    `IndexedDB: version check for "${this.name}" failed; ` +
                        `continuing without the disk cache for this session.`,
                    error,
                );
            });
    }

    /**
     * @param {string} table
     * @param {string} key
     */
    async read(table, key) {
        this._tables.add(table);
        return this.execute((db) => {
            if (db) {
                return this._read(db, table, key);
            }
        });
    }

    /**
     * @param {string} table
     * @param {string} key
     * @param {any} value
     */
    async write(table, key, value) {
        this._tables.add(table);
        return this.execute((db) => {
            if (db) {
                return this._write(db, table, key, value);
            }
        });
    }

    /**
     * @param {string} table
     * @returns {Promise<Record<string, any>>} every value of the table by key
     */
    async readAll(table) {
        this._tables.add(table);
        return this.execute((db) => (db ? this._readAll(db, table) : {}));
    }

    /** @param {string|string[]|null} [tables=null] */
    async invalidate(tables = null) {
        return this.execute((db) => {
            if (db) {
                return this._invalidate(
                    db,
                    typeof tables === "string" ? [tables] : tables,
                );
            }
        });
    }

    /**
     * @param {string[]} tables
     * @param {(key: string) => boolean} predicate
     */
    async invalidateWhere(tables, predicate) {
        return this.execute((db) => {
            if (db) {
                return this._invalidateWhere(db, tables, predicate);
            }
        });
    }

    /**
     * @param {string[]} tables
     * @param {string} model
     */
    async invalidateByModel(tables, model) {
        return this.execute((db) => {
            if (db) {
                return this._invalidateByModel(db, tables, model);
            }
        });
    }

    async deleteDatabase() {
        return this.mutex.exec(() => this._deleteDatabase(() => {}));
    }

    /** @param {(db?: IDBDatabase) => any} callback */
    async execute(callback) {
        return this.mutex.exec(() => this._execute(callback));
    }

    _closeCachedDB() {
        if (this._db) {
            this._db.close();
            this._db = null;
        }
    }

    async _deleteDatabase(/** @type {() => any} */ callback) {
        this._closeCachedDB();
        return new Promise((resolve) => {
            let settled = false;
            /** @type {any} */
            let blockedTimeoutId;
            const settle = (/** @type {boolean} */ runCallback) => {
                if (settled) {
                    return;
                }
                settled = true;
                browser.clearTimeout(blockedTimeoutId);
                if (runCallback) {
                    Promise.resolve(callback()).then(resolve, (error) => {
                        console.error(
                            `IndexedDB: work after deleting "${this.name}" failed`,
                            error,
                        );
                        resolve(undefined);
                    });
                } else {
                    resolve(undefined);
                }
            };
            const request = browser.indexedDB.deleteDatabase(this.name);
            request.onsuccess = () => settle(true);
            request.onerror = (event) => {
                console.error(
                    `IndexedDB delete error: ${/** @type {IDBRequest} */ (event.target).error?.message}`,
                );
                settle(true);
            };
            request.onblocked = () => {
                blockedTimeoutId = browser.setTimeout(() => {
                    console.warn(
                        `IndexedDB delete blocked: "${this.name}" is still open in another context ` +
                            `(e.g. a frozen tab); proceeding without cache for this session.`,
                    );
                    this._degraded = true;
                    settle(false);
                }, BLOCKED_DELETE_TIMEOUT);
            };
        });
    }

    async _checkVersion(/** @type {string} */ version) {
        const currentVersion = await this._execute((db) => {
            if (db) {
                return this._read(db, VERSION_TABLE, VERSION_KEY);
            }
        });
        if (!currentVersion) {
            await this._execute((db) => {
                if (db) {
                    return this._write(db, VERSION_TABLE, VERSION_KEY, version);
                }
            });
        } else if (currentVersion !== version) {
            await this._deleteDatabase(() =>
                this._execute((db) => {
                    if (db) {
                        return this._write(db, VERSION_TABLE, VERSION_KEY, version);
                    }
                }),
            );
        }
    }

    /**
     * @param {IDBDatabase} db
     * @param {(db?: IDBDatabase) => any} callback
     */
    async _runCallback(db, callback) {
        try {
            return await callback(db);
        } catch (e) {
            if (e.name === "QuotaExceededError") {
                /** @type {StorageEstimate} */
                let estimate = {};
                try {
                    estimate = (await browser.navigator.storage?.estimate()) ?? {};
                } catch {}
                console.error(
                    `IndexedDB error: Quota Exceeded (${formatStorageSize(
                        estimate.usage,
                    )} out of ${formatStorageSize(estimate.quota)} used)`,
                );
                throw new IDBQuotaExceededError();
            }
            throw e;
        }
    }

    /**
     * @param {(db?: IDBDatabase) => any} callback
     * @param {number} [idbVersion]
     * @returns {Promise<any>}
     */
    async _execute(callback, idbVersion) {
        if (this._degraded) {
            return callback();
        }
        if (this._db && idbVersion === undefined) {
            const db = this._db;
            const dbTables = new Set(db.objectStoreNames);
            if (this._tables.difference(dbTables).size === 0) {
                try {
                    return await this._runCallback(db, callback);
                } catch (e) {
                    if (e?.name === "InvalidStateError") {
                        if (this._db === db) {
                            this._db = null;
                        }
                        return this._execute(callback);
                    }
                    throw e;
                }
            }
            const upgradeVersion = db.version + 1;
            this._closeCachedDB();
            return this._execute(callback, upgradeVersion);
        }
        return new Promise((resolve, reject) => {
            let request;
            let settled = false;
            /** @type {any} */
            let blockedTimeoutId;
            const settle = (/** @type {() => void} */ fn) => {
                if (settled) {
                    return;
                }
                settled = true;
                browser.clearTimeout(blockedTimeoutId);
                fn();
            };
            try {
                request = browser.indexedDB.open(this.name, idbVersion);
            } catch (e) {
                console.warn(`IndexedDB unavailable: ${e?.message}`);
                this._degraded = true;
                Promise.resolve(callback()).then(resolve, reject);
                return;
            }
            request.onupgradeneeded = (event) => {
                const db = /** @type {IDBOpenDBRequest} */ (event.target).result;
                const dbTables = new Set(db.objectStoreNames);
                const newTables = this._tables.difference(dbTables);
                newTables.forEach((table) => db.createObjectStore(table));
            };
            request.onsuccess = (event) => {
                const db = /** @type {IDBOpenDBRequest} */ (event.target).result;
                if (settled) {
                    db.close();
                    return;
                }
                settle(() => {
                    const dbTables = new Set(db.objectStoreNames);
                    const newTables = this._tables.difference(dbTables);
                    if (newTables.size !== 0) {
                        db.close();
                        const version = db.version + 1;
                        this._execute(callback, version).then(resolve, reject);
                        return;
                    }
                    this._db = db;
                    db.onversionchange = () => {
                        db.close();
                        if (this._db === db) {
                            this._db = null;
                        }
                    };
                    db.onclose = () => {
                        if (this._db === db) {
                            this._db = null;
                        }
                    };
                    this._runCallback(db, callback).then(resolve, reject);
                });
            };
            request.onerror = (event) => {
                settle(() => {
                    this._degraded = true;
                    console.error(
                        `IndexedDB error: ${/** @type {IDBRequest} */ (event.target).error?.message}`,
                    );
                    Promise.resolve(callback()).then(resolve, reject);
                });
            };
            request.onblocked = () => {
                blockedTimeoutId = browser.setTimeout(() => {
                    console.warn(
                        `IndexedDB upgrade blocked: "${this.name}" is still open in another context ` +
                            `(e.g. a frozen tab); proceeding without cache for this session.`,
                    );
                    this._degraded = true;
                    settle(() => Promise.resolve(callback()).then(resolve, reject));
                }, BLOCKED_DELETE_TIMEOUT);
            };
        });
    }

    async _write(
        /** @type {IDBDatabase} */ db,
        /** @type {string} */ table,
        /** @type {string} */ key,
        /** @type {any} */ record,
    ) {
        return new Promise((resolve, reject) => {
            const transaction = db.transaction(table, "readwrite", {
                durability: "relaxed",
            });
            transaction.objectStore(table).put(record, key);
            transaction.onerror = (ev) =>
                reject(/** @type {IDBTransaction} */ (ev.target).error);
            transaction.onabort = (ev) =>
                reject(/** @type {IDBTransaction} */ (ev.target).error);
            transaction.oncomplete = resolve;

            transaction.commit();
        });
    }

    async _invalidate(
        /** @type {IDBDatabase} */ db,
        /** @type {string[] | null} */ tables,
    ) {
        return new Promise((resolve, reject) => {
            const objectStoreNames = [...db.objectStoreNames].filter(
                (table) => table !== VERSION_TABLE,
            );
            const requested = tables;
            const targetTables = requested
                ? objectStoreNames.filter((t) => requested.includes(t))
                : objectStoreNames;

            if (!targetTables.length) {
                return resolve(undefined);
            }
            const transaction = db.transaction(targetTables, "readwrite", {
                durability: "relaxed",
            });
            for (const table of targetTables) {
                transaction.objectStore(table).clear();
            }
            transaction.oncomplete = () => resolve(undefined);
            transaction.onerror = () => reject(transaction.error);
            transaction.onabort = () => reject(transaction.error);

            transaction.commit();
        });
    }

    async _read(
        /** @type {IDBDatabase} */ db,
        /** @type {string} */ table,
        /** @type {string} */ key,
    ) {
        return new Promise((resolve, reject) => {
            const transaction = db.transaction(table, "readonly");
            const objectStore = transaction.objectStore(table);
            const r = objectStore.get(key);
            r.onsuccess = () => resolve(r.result);
            transaction.onerror = () => reject(transaction.error);
            transaction.onabort = () => reject(transaction.error);
        });
    }

    async _readAll(/** @type {IDBDatabase} */ db, /** @type {string} */ table) {
        return new Promise((resolve, reject) => {
            const transaction = db.transaction(table, "readonly");
            const objectStore = transaction.objectStore(table);
            const keys = objectStore.getAllKeys();
            const values = objectStore.getAll();
            transaction.oncomplete = () =>
                resolve(
                    Object.fromEntries(
                        keys.result.map((key, index) => [key, values.result[index]]),
                    ),
                );
            transaction.onerror = () => reject(transaction.error);
            transaction.onabort = () => reject(transaction.error);
        });
    }

    /**
     * @param {IDBDatabase} db
     * @param {string[]} tables
     * @param {{
     * needsValue: boolean,
     * shouldDelete: (cursor: IDBCursor | IDBCursorWithValue) => boolean,
     * }} params
     * @returns {Promise<void>}
     */
    async _removeEntries(db, tables, { needsValue, shouldDelete }) {
        return new Promise((resolve, reject) => {
            const objectStoreNames = [...db.objectStoreNames].filter(
                (table) => table !== VERSION_TABLE,
            );
            const targetTables = objectStoreNames.filter((t) => tables.includes(t));
            if (!targetTables.length) {
                return resolve(undefined);
            }
            const transaction = db.transaction(targetTables, "readwrite", {
                durability: "relaxed",
            });
            transaction.oncomplete = () => resolve(undefined);
            transaction.onerror = () => reject(transaction.error);
            transaction.onabort = () => reject(transaction.error);
            for (const table of targetTables) {
                const objectStore = transaction.objectStore(table);
                const request = needsValue
                    ? objectStore.openCursor()
                    : objectStore.openKeyCursor();
                request.onsuccess = (event) => {
                    const cursor = /** @type {IDBCursor | null} */ (
                        /** @type {IDBRequest} */ (event.target).result
                    );
                    if (!cursor) {
                        return;
                    }
                    let doomed = false;
                    try {
                        doomed = shouldDelete(cursor);
                    } catch {}
                    if (doomed) {
                        objectStore.delete(cursor.key);
                    }
                    cursor.continue();
                };
            }
        });
    }

    async _invalidateByModel(
        /** @type {IDBDatabase} */ db,
        /** @type {string[]} */ tables,
        /** @type {string} */ model,
    ) {
        return this._removeEntries(db, tables, {
            needsValue: true,
            shouldDelete: (cursor) =>
                /** @type {IDBCursorWithValue} */ (cursor).value?.model === model,
        });
    }

    async _invalidateWhere(
        /** @type {IDBDatabase} */ db,
        /** @type {string[]} */ tables,
        /** @type {(key: string) => boolean} */ predicate,
    ) {
        return this._removeEntries(db, tables, {
            needsValue: false,
            shouldDelete: (cursor) => predicate(/** @type {string} */ (cursor.key)),
        });
    }
}
