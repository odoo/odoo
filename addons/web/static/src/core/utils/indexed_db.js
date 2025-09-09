import { Mutex } from "./concurrency";

const VERSION_TABLE = "__DBVersion__";
const VERSION_KEY = "__version__";

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
     * @param {string} key
     * @returns Promise
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
     * Write data into the given table
     *
     * @param {string} table
     * @param {string} key
     * @param  {any} value
     * @returns Promise
     */
    async write(table, key, value) {
        this._tables.add(table);
        return this.execute((db) => {
            if (db) {
                this._write(db, table, key, value);
            }
        });
    }

    /**
     * Invalidates a table, or the whole database.
     *
     * @param {string|Array} [table=null] if not given, the whole database is invalidated
     * @returns Promise
     */
    async invalidate(tables = null) {
        return this.execute((db) => {
            if (db) {
                return this._invalidate(db, typeof tables === "string" ? [tables] : tables);
            }
        });
    }

    /**
     * Delete the whole database
     *
     * @returns Promise
     */
    async deleteDatabase() {
        return this.mutex.exec(() => this._deleteDatabase(() => {}));
    }

    /**
     * open the database and execute the callback with the db as parameter.
     *
     * @params {Function} callback
     * @returns Promise
     */
    async execute(callback) {
        return this.mutex.exec(() => this._execute(callback));
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
            this._execute((db) => {
                if (db) {
                    return this._read(db, VERSION_TABLE, VERSION_KEY);
                }
            }).then((currentVersion) => {
                if (!currentVersion) {
                    this._execute((db) => {
                        if (db) {
                            this._write(db, VERSION_TABLE, VERSION_KEY, version);
                        }
                    }).then(resolve);
                } else if (currentVersion !== version) {
                    this._deleteDatabase(() => {
                        this._execute((db) => {
                            if (db) {
                                this._write(db, VERSION_TABLE, VERSION_KEY, version);
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
        return new Promise((resolve) => {
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

    async _write(db, table, key, record) {
        return new Promise((resolve, reject) => {
            // Relaxed durability improves the write performances
            // https://nolanlawson.com/2021/08/22/speeding-up-indexeddb-reads-and-writes/
            // https://developer.mozilla.org/en-US/docs/Web/API/IDBTransaction/durability
            const transaction = db.transaction(table, "readwrite", { durability: "relaxed" });
            const objectStore = transaction.objectStore(table);
            const request = objectStore.put(record, key); // put to allow updates
            request.onsuccess = resolve;
            transaction.onerror = () => reject(transaction.error);

            // Force the changes to be committed to the database asap
            // https://developer.mozilla.org/en-US/docs/Web/API/IDBTransaction/commit
            transaction.commit();
        });
    }

    async _invalidate(db, tables) {
        return new Promise((resolve, reject) => {
            const objectStoreNames = [...db.objectStoreNames].filter(
                (table) => table !== VERSION_TABLE
            );
            tables = tables ? objectStoreNames.filter((t) => tables.includes(t)) : objectStoreNames;

            if (tables.length === 0) {
                return resolve();
            }
            // Relaxed durability improves the write performances
            // https://nolanlawson.com/2021/08/22/speeding-up-indexeddb-reads-and-writes/
            // https://developer.mozilla.org/en-US/docs/Web/API/IDBTransaction/durability
            const transaction = db.transaction(tables, "readwrite", { durability: "relaxed" });
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

            // Force the changes to be committed to the database asap
            // https://developer.mozilla.org/en-US/docs/Web/API/IDBTransaction/commit
            transaction.commit();
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
