import { Mutex } from "./concurrency";

export const VERSION_TABLE = "__DBVersion__";
export const VERSION_KEY = "__version__";

const BATCH_SIZE = 2000;

export class IDBQuotaExceededError extends Error {}

function formatStorageSize(size) {
    const units = ["b", "Kb", "Mb", "Gb"];
    while (size >= 1000 && units.length > 1) {
        size /= 1000;
        units.splice(0, 1);
    }
    return `${size.toFixed(2)}${units[0]}`;
}

export class IndexedDB {
    constructor(name, version) {
        this.name = name;
        this._tables = new Set([VERSION_TABLE]);
        this.mutex = new Mutex();
        this.mutex.exec(() => this._checkVersion(version));
    }

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------

    /**
     * Reads data from a given table.
     *
     * @param {string} table
     * @param {string|Array} keys
     * @returns {Promise<any>}
     */
    async read(table, keys) {
        this._tables.add(table);
        return this.mutex.exec(() =>
            this._execute(async (db) => {
                if (db) {
                    return new Promise((resolve, reject) => {
                        this._read(db, table, [].concat(keys))
                            .then((res) => {
                                if (Array.isArray(keys)) {
                                    return resolve(res);
                                } else {
                                    return resolve(res?.[0].value);
                                }
                            })
                            .catch((error) => reject(error));
                    });
                }
            })
        );
    }

    /**
     * Search data from a given term.
     *
     * @param {string} table The name of the table to search.
     * @param {Function} searchFn The function used to match records (async).
     * @param {number} limit The maximum number of results to return.
     * @returns {Promise<any>} The matching records.
     */
    async search(table, searchFn, limit = 8) {
        this._tables.add(table);
        return this.mutex.exec(() =>
            this._execute((db) => {
                if (db) {
                    return this._search(db, table, searchFn, limit);
                }
            })
        );
    }

    async getAllEntries(table) {
        this._tables.add(table);
        return this.mutex.exec(() =>
            this._execute((db) => {
                if (db) {
                    return this._getAllEntries(db, table);
                }
            })
        );
    }

    /**
     * Reads all keys from a given table.
     *
     * @param {string} table
     * @returns {Promise<string>}
     */
    async getAllKeys(table) {
        this._tables.add(table);
        return this.mutex.exec(() =>
            this._execute(async (db) => {
                if (db) {
                    return this._getAllKeys(db, table);
                }
            })
        );
    }

    /**
     * Write data or multiple data into the given table in the same transaction
     *
     * @param {string} table
     * @param {string|Array} key : string|Array if it's an Array, it's an Array of object with key/values
     * @param  {any} value
     * @returns {Promise}
     */
    async write(table, key, value) {
        this._tables.add(table);
        return this.mutex.exec(() =>
            this._execute((db) => {
                if (db) {
                    const items = Array.isArray(key) ? key : [{ key, value }];
                    return this._write(db, table, items);
                }
            })
        );
    }

    /**
     * Delete data from the given table
     *
     * @param {string} table
     * @param {string} key
     * @returns {Promise}
     */
    async delete(table, key) {
        this._tables.add(table);
        return this.mutex.exec(() =>
            this._execute((db) => {
                if (db) {
                    return this._delete(db, table, key);
                }
            })
        );
    }

    /**
     * Invalidates a table, or the whole database.
     *
     * @param {string|RegExp|Array} [table=null] if not given, the whole database is invalidated
                                    if it's a string it need to be the exact table name.
                                    if it's a RegExp it will be evalutated.
     * @returns {Promise}
     */
    async invalidate(tables = null) {
        return this.mutex.exec(() =>
            this._execute((db) => {
                if (db) {
                    return this._invalidate(db, typeof tables === "string" ? [tables] : tables);
                }
            })
        );
    }

    /**
     * Delete the whole database
     *
     * @returns {Promise}
     */
    async deleteDatabase() {
        return this.mutex.exec(() => this._deleteDatabase(() => {}));
    }

    // -------------------------------------------------------------------------
    // Protected
    // -------------------------------------------------------------------------

    async _deleteDatabase(callback) {
        return new Promise((resolve) => {
            const request = indexedDB.deleteDatabase(this.name);
            request.onsuccess = () => {
                Promise.resolve(callback()).then(resolve);
            };
            request.onerror = (event) => {
                console.error(`IndexedDB delete error: ${event.target.error?.message}`);
                Promise.resolve(callback()).then(resolve);
            };
        });
    }

    async _checkVersion(version) {
        return new Promise((resolve) => {
            this._execute(async (db) => {
                if (db) {
                    return new Promise((resolve, reject) => {
                        this._read(db, VERSION_TABLE, [VERSION_KEY])
                            .then((res) => resolve(res?.[0].value))
                            .catch((error) => reject(error));
                    });
                }
            }).then((currentVersion) => {
                if (!currentVersion) {
                    this._execute((db) => {
                        if (db) {
                            this._write(db, VERSION_TABLE, [{ key: VERSION_KEY, value: version }]);
                        }
                    }).then(resolve);
                } else if (currentVersion !== version) {
                    this._deleteDatabase(() => {
                        this._execute((db) => {
                            if (db) {
                                this._write(db, VERSION_TABLE, [
                                    { key: VERSION_KEY, value: version },
                                ]);
                            }
                        });
                    }).then(resolve);
                } else {
                    resolve();
                }
            });
        });
    }

    async _execute(callback, idbVersion) {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.name, idbVersion);
            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                const dbTables = new Set(db.objectStoreNames);
                const newTables = this._tables.difference(dbTables);
                newTables.forEach((table) => db.createObjectStore(table));
            };
            request.onsuccess = (event) => {
                const db = event.target.result;
                const dbTables = new Set(db.objectStoreNames);
                const newTables = this._tables.difference(dbTables);
                if (newTables.size !== 0) {
                    db.close();
                    const version = db.version + 1;
                    return this._execute(callback, version).then(resolve);
                }
                Promise.resolve(callback(db))
                    .then(resolve)
                    .catch(async (e) => {
                        if (e.name === "QuotaExceededError") {
                            const { quota, usage } = await navigator.storage.estimate();
                            console.error(
                                `IndexedDB error: Quota Exceeded (${formatStorageSize(
                                    usage
                                )} out of ${formatStorageSize(quota)} used)`
                            );
                            reject(new IDBQuotaExceededError());
                        } else {
                            reject(e);
                        }
                    })
                    .finally(() => db.close());
            };
            request.onerror = (event) => {
                console.error(`IndexedDB error: ${event.target.error?.message}`);
                Promise.resolve(callback()).then(resolve);
            };
        });
    }

    async _write(db, table, items) {
        return new Promise((resolve, reject) => {
            // AAB: do we care about write performance?
            // Relaxed durability improves the write performances
            // https://nolanlawson.com/2021/08/22/speeding-up-indexeddb-reads-and-writes/
            // https://developer.mozilla.org/en-US/docs/Web/API/IDBTransaction/durability
            const transaction = db.transaction(table, "readwrite", { durability: "relaxed" });
            const store = transaction.objectStore(table);

            for (const item of items) {
                store.put(item.value, item.key); // put to allow updates
            }

            transaction.onerror = (ev) => reject(ev.target.error); // firefox (DOMException)
            transaction.onabort = (ev) => reject(ev.target.error); // chrome (QuotaExceededError)
            transaction.oncomplete = resolve;

            // Force the changes to be committed to the database asap
            // https://developer.mozilla.org/en-US/docs/Web/API/IDBTransaction/commit
            transaction.commit();
        });
    }

    async _delete(db, table, key) {
        return new Promise((resolve, reject) => {
            const transaction = db.transaction(table, "readwrite");
            transaction.objectStore(table).delete(key);
            transaction.onerror = (ev) => reject(ev.target.error);
            transaction.onabort = (ev) => reject(ev.target.error);
            transaction.oncomplete = resolve;

            // Force the changes to be committed to the database asap
            // https://developer.mozilla.org/en-US/docs/Web/API/IDBTransaction/commit
            transaction.commit();
        });
    }

    async _invalidate(db, matchers) {
        return new Promise((resolve, reject) => {
            const existingTableNames = [...db.objectStoreNames].filter(
                (table) => table !== VERSION_TABLE
            );
            let tablesToInvalidate = [];

            if (matchers && matchers.length) {
                tablesToInvalidate = existingTableNames.filter((item) =>
                    matchers.some((query) => {
                        if (query instanceof RegExp) {
                            return query.test(item);
                        }
                        return item === query;
                    })
                );
            } else {
                tablesToInvalidate = existingTableNames;
            }

            if (tablesToInvalidate.length === 0) {
                return resolve();
            }
            // Relaxed durability improves the write performances
            // https://nolanlawson.com/2021/08/22/speeding-up-indexeddb-reads-and-writes/
            // https://developer.mozilla.org/en-US/docs/Web/API/IDBTransaction/durability
            const transaction = db.transaction(tablesToInvalidate, "readwrite", {
                durability: "relaxed",
            });
            const proms = tablesToInvalidate.map(
                (table) =>
                    new Promise((resolve) => {
                        const objectStore = transaction.objectStore(table);
                        const request = objectStore.clear();
                        request.onsuccess = resolve;
                    })
            );
            Promise.all(proms).then(resolve);
            transaction.onerror = (ev) => reject(ev.target.error);
            transaction.onabort = (ev) => reject(ev.target.error);

            // Force the changes to be committed to the database asap
            // https://developer.mozilla.org/en-US/docs/Web/API/IDBTransaction/commit
            transaction.commit();
        });
    }

    async _read(db, table, keys) {
        return new Promise((resolve, reject) => {
            const transaction = db.transaction(table, "readonly");
            const objectStore = transaction.objectStore(table);

            const results = new Array(keys.length);
            keys.forEach((key, index) => {
                const request = objectStore.get(key);

                request.onsuccess = () => {
                    results[index] = { key: key, value: request.result };
                };
            });
            transaction.oncomplete = () => resolve(results);

            transaction.onerror = (ev) => reject(ev.target.error);
            transaction.onabort = (ev) => reject(ev.target.error);
        });
    }

    async _search(db, table, searchFn, limit) {
        const results = [];
        let query = null; // Start with no range (fetch from the beginning)

        // Start first I/O fetch immediately
        let nextBatchPromise = this._getAllEntries(db, table, query, BATCH_SIZE);

        // eslint-disable-next-line no-constant-condition
        while (true) {
            const records = await nextBatchPromise;

            // Pre-fetch next batch while CPU processes current one (Pipeline)
            if (records.length === BATCH_SIZE) {
                query = IDBKeyRange.lowerBound(records.at(-1).key, true);
                nextBatchPromise = this._getAllEntries(db, table, query, BATCH_SIZE);
            } else {
                nextBatchPromise = Promise.resolve([]);
            }

            for (const record of records) {
                if (await searchFn(record.value)) {
                    results.push(record);
                    if (results.length === limit) {
                        return results;
                    }
                }
            }

            // Stop if we reached the end of the table
            if (records.length < BATCH_SIZE) {
                return results;
            }
        }
    }

    async _getAllEntries(db, table, query, count) {
        return new Promise((resolve, reject) => {
            const transaction = db.transaction(table, "readonly");
            const store = transaction.objectStore(table);
            if ("getAllRecords" in store) {
                // This is faster but it's not suported by all browsers!
                const r = store.getAllRecords({ query, count });
                r.onsuccess = () => resolve(r.result.map(({ key, value }) => ({ key, value })));
            } else {
                const keysReq = store.getAllKeys(query, count);
                const valuesReq = store.getAll(query, count);
                transaction.oncomplete = () => {
                    const keys = keysReq.result;
                    const values = valuesReq.result;
                    resolve(keys.map((key, i) => ({ key, value: values[i] })));
                };
            }
            transaction.onerror = (ev) => reject(ev.target.error);
            transaction.onabort = (ev) => reject(ev.target.error);
        });
    }

    async _getAllKeys(db, table) {
        return new Promise((resolve, reject) => {
            const transaction = db.transaction(table, "readonly");
            const objectStore = transaction.objectStore(table);
            const r = objectStore.getAllKeys();
            r.onsuccess = () => resolve(r.result);
            transaction.onerror = (ev) => reject(ev.target.error);
            transaction.onabort = (ev) => reject(ev.target.error);
        });
    }
}
