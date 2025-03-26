const DB = window.indexedDB || window.mozIndexedDB || window.webkitIndexedDB || window.msIndexedDB;

export class IndexedDBWrapper {
    /**
     * Helper to get the function to be called when the spreadsheet is opened
     * in order to insert the link.
     *
     * @param {string} dbName - The unique name of the database.
     * @param {Array<[id, name]>} dbStores - An array of tuples where each tuple contains an id and table name.
     * @param {Function} whenReady - A callback function to execute when the database is ready.
     */
    constructor(dbName, dbStores, whenReady) {
        this.db = null;
        this.dbName = dbName;
        this.dbStores = dbStores;
        this.whenReady = whenReady;

        if (!DB) {
            console.error("Warning: Your browser doesn't support IndexedDB");
            return;
        }

        this.open();
    }

    /**
     * Get all records from all stores.
     *
     * @param {Array} storeNames - (Optional) Array of store names to get data from.
     **/
    getData(storeNames = []) {
        if (!storeNames.length) {
            storeNames = this.dbStores.map(([_, name]) => name);
        }

        return new Promise((resolve, reject) => {
            try {
                const transaction = this.db.transaction(storeNames, "readonly");
                const data = {};
                storeNames.forEach((storeName) => {
                    const store = transaction.objectStore(storeName);
                    const request = store.getAll();
                    request.onsuccess = (event) => {
                        data[storeName] = event.target.result;
                    };
                });
                this.resolver(transaction, resolve, reject);
            } catch (error) {
                resolve(error);
            }
        });
    }

    /**
     * Get all the records from a store.
     *
     * @param {string} storeName - Store name.
     **/
    getStoreData(storeName) {
        return new Promise((resolve, reject) => {
            try {
                const transaction = this.db.transaction(storeName, "readonly");
                const store = transaction.objectStore(storeName);
                const request = store.getAll();
                this.resolver(request, resolve, reject);
            } catch (error) {
                resolve(error);
            }
        });
    }

    /**
     * Get a record by its id.
     *
     * @param {string} storeName - Store name.
     * @param {string} id - Record id.
     **/
    getById(storeName, id) {
        return new Promise((resolve, reject) => {
            try {
                const transaction = this.db.transaction(storeName, "readonly");
                const store = transaction.objectStore(storeName);
                const request = store.get(id);
                this.resolver(request, resolve, reject);
            } catch (error) {
                resolve(error);
            }
        });
    }

    /**
     * Update several records in a store.
     *
     * @param {string} storeName - Store name.
     * @param {Array} data - Array of records to update.
     **/
    put(storeName, data) {
        return new Promise((resolve, reject) => {
            try {
                const transaction = this.db.transaction(storeName, "readwrite");
                const store = transaction.objectStore(storeName);
                data.forEach((item) => {
                    const data = this.dataSanityCheck(store.keyPath, item);
                    store.put(data);
                });
                this.resolver(transaction, resolve, reject);
            } catch (error) {
                resolve(error);
            }
        });
    }

    /**
     * Delete a record by its id.
     *
     * @param {string} storeName - Store name.
     * @param {Array} id - Array of record ids to delete.
     **/
    delete(storeName, id) {
        return new Promise((resolve, reject) => {
            try {
                const transaction = this.db.transaction(storeName, "readwrite");
                const store = transaction.objectStore(storeName);
                id.forEach((item) => {
                    store.delete(item);
                });
                this.resolver(transaction, resolve, reject);
            } catch (error) {
                resolve(error);
            }
        });
    }

    /**
     * Wrapper for the onsuccess and onerror events of the IDBRequest object.
     * This method is used to resolve or reject a promise based on the result
     *
     * @param {IDBRequest} instance - The IDBRequest instance.
     * @param {Function} resolve - The resolve function of the promise.
     * @param {Function} reject - The reject function of the promise.
     **/
    resolver(instance, resolve, reject) {
        instance.oncomplete = (event) => {
            resolve(event.target.result);
        };
        instance.onsuccess = (event) => {
            resolve(event.target.result);
        };
        instance.onerror = (event) => {
            reject(event.target.error);
        };
    }

    /**
     * This method ensure that the data that will be inserted in the database
     * is clonable and has the correct structure.
     *
     * @param {string} keyPath - The keyPath of the object store.
     * @param {Object} data - The data to be inserted in the database.
     **/
    dataSanityCheck(keyPath, data) {
        if (!data || typeof data !== "object") {
            throw new Error("Data must be an object");
        }

        if (!data[keyPath]) {
            throw new Error("Data must have a valid keyPath");
        }

        return JSON.parse(JSON.stringify(data));
    }

    /**
     * Open the database and create the object stores if they don't exist.
     *
     * If a change in the schema is detected, the database is closed and reopened
     * with its version incremented by 1, that way the onupgradeneeded event is
     * triggered and the schema is updated.
     *
     * The version system is automatically handled by the checkSchemaChange method,
     * so we don't need to worry about it.
     */
    open(version = false) {
        const instance = version ? DB.open(this.dbName, version) : DB.open(this.dbName);

        instance.onerror = (event) => {
            console.error("Database error: " + event.target.errorCode);
        };

        instance.onsuccess = (event) => {
            this.db = event.target.result;
            const upgradeNeeded = this.checkSchemaChange();

            if (upgradeNeeded) {
                console.warn("Database schema changed, upgrading...");
                this.db.close();
                this.open(this.db.version + 1);
                return;
            }

            this.whenReady();
        };

        instance.onupgradeneeded = (event) => {
            const db = event.target.result;
            const transaciton = event.target.transaction;
            const stores = Object.values(db.objectStoreNames);

            for (const [id, storeName] of this.dbStores) {
                if (!stores.includes(storeName)) {
                    db.createObjectStore(storeName, { keyPath: id });
                    continue;
                }

                const IDBStore = transaciton.objectStore(storeName);
                if (IDBStore.keyPath !== id) {
                    db.deleteObjectStore(storeName);
                    db.createObjectStore(storeName, { keyPath: id });
                }
            }

            // Check if there are any object stores that need to be removed
            for (const store of stores) {
                if (!this.dbStores.some(([_, name]) => name === store)) {
                    db.deleteObjectStore(store);
                }
            }
        };
    }

    /**
     * Check if the schema of the database has changed.
     * This is done by comparing the keyPath of each object store with the
     * keyPath of the model.
     **/
    checkSchemaChange() {
        const stores = Object.values(this.db.objectStoreNames);
        const dbStoreKeyPathByModel = this.dbStores.reduce((acc, [id, name]) => {
            acc[name] = id;
            return acc;
        }, {});

        const upgradeNeeded =
            stores.some((store) => {
                const IDBStore = this.db.transaction(store, "readwrite").objectStore(store);
                const keyPath = IDBStore.keyPath;
                const name = IDBStore.name;
                return keyPath !== dbStoreKeyPathByModel[name];
            }) || this.dbStores.some(([id, name]) => !stores.includes(name));

        return upgradeNeeded;
    }
}
