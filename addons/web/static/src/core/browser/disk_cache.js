// a connection must always be closed right away, otherwise there's a multi tab
// issue when version is incremented: callbacks never called
// https://stackoverflow.com/questions/40121865/indexed-db-open-not-trigger-any-callback

// TODO
// prob: new db, table version 1, new db, still table version 1 => not cleared
// filters don't invalidate cache? python side, it should change the views (templates) hash

export class DiskCache {
    constructor(name) {
        this.name = name;
        this._tables = new Set();
        this._getDataCallbacks = {};
        this._getKeyCallbacks = {};
        this._version = undefined;
        // the RAM cache allows to store promises, which helps with concurrent requests, e.g.
        //  - incoming request does a cache miss -> getData is called
        //  - another identical request during the getData -> we want to get the same promise
        //  -> store the promise in the cache directly, s.t. the second request is a cache hit
        this._ramCache = {};
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
     * @param {Function} getData the callback to obtain the data to store in the table, called on
     *  cache misses
     * @param {Function} getKey the callback to generate the keys of the table
     * @returns Promise
     */
    async defineTable(name, version, getData, getKey) {
        this._tables.add(name);
        this._ramCache[name] = {};
        this._getDataCallbacks[name] = getData;
        this._getKeyCallbacks[name] = getKey;
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
     * @param  {...any} args arguments given to the getData and getKey callbacks of that table
     * @returns Promise<any>
     */
    async read(table, ...args) {
        const key = this._getKeyCallbacks[table](...args);
        if (!(key in this._ramCache[table])) {
            this._ramCache[table][key] = this._execute((db) => {
                if (!db) {
                    return this._getDataCallbacks[table](...args).catch((e) => {
                        delete this._ramCache[table][key];
                        throw e;
                    });
                }
                return new Promise((resolve, reject) => {
                    this._read(db, table, key).then((result) => {
                        if (!result) {
                            Promise.resolve(this._getDataCallbacks[table](...args))
                                .then((result) => {
                                    this._insert(db, table, result, key);
                                    resolve(result);
                                })
                                .catch((error) => {
                                    delete this._ramCache[table][key];
                                    reject(error);
                                });
                        } else {
                            resolve(result);
                        }
                    });
                });
            });
        }
        return this._ramCache[table][key];
    }

    /**
     * Invalidates a table, or the whole cache.
     *
     * @param {string} [table] if not given, the whole cache is invalidated
     * @returns Promise
     */
    async invalidate(table = null) {
        const tables = table ? [table] : Object.keys(this._ramCache);
        for (const table of tables) {
            this._ramCache[table] = {};
        }
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
            const request = objectStore.add(record, key);
            request.onsuccess = resolve;
            transaction.onerror = () => reject(transaction.error);
        });
    }

    async _invalidate(db, table) {
        return new Promise((resolve, reject) => {
            const tables = table ? [table] : [...db.objectStoreNames];
            const transaction = db.transaction(tables, "readwrite");
            const proms = tables.map((table) => {
                return new Promise((resolve) => {
                    const objectStore = transaction.objectStore(table);
                    const request = objectStore.clear();
                    request.onsuccess = resolve;
                });
            });
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
