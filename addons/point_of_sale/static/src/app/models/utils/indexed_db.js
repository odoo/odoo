import { _t } from "@web/core/l10n/translation";

export default class IndexedDB {
    constructor(dbName, dbVersion, dbStores, whenReady) {
        this.db = null;
        this.dbName = dbName;
        this.dbVersion = dbVersion;
        this.dbStores = dbStores;
        this.dbInstance = null;
        this.databaseEventListener(whenReady);
    }

    databaseEventListener(whenReady) {
        const indexedDB =
            window.indexedDB || window.mozIndexedDB || window.webkitIndexedDB || window.msIndexedDB;

        if (!indexedDB) {
            console.error(
                _t(
                    "Warning: Your browser doesn't support IndexedDB. The data won't be saved. Please use a modern browser."
                )
            );
        }

        this.dbInstance = indexedDB;
        const dbInstance = indexedDB.open(this.dbName, this.dbVersion);
        dbInstance.onerror = (event) => {
            console.error("Database error: " + event.target.errorCode);
        };
        dbInstance.onsuccess = (event) => {
            this.db = event.target.result;
            console.info(`IndexedDB ${this.dbVersion} Ready`);
            whenReady();
        };
        dbInstance.onupgradeneeded = (event) => {
            for (const [id, storeName] of this.dbStores) {
                if (!event.target.result.objectStoreNames.contains(storeName)) {
                    event.target.result.createObjectStore(storeName, { keyPath: id });
                }
            }
        };
    }

    async promises(storeName, arrData, method) {
        const transaction = this.getNewTransaction([storeName], "readwrite");
        if (!transaction) {
            return false;
        }

        const promises = arrData.map((data) => {
            data = JSON.parse(JSON.stringify(data));
            return new Promise((resolve, reject) => {
                const request = transaction.objectStore(storeName)[method](data);
                request.onsuccess = () => resolve();
                request.onerror = () => reject();
            });
        });

        return Promise.allSettled(promises).then((results) => results);
    }
    getNewTransaction(dbStore) {
        try {
            if (!this.db) {
                return false;
            }

            return this.db.transaction(dbStore, "readwrite");
        } catch (e) {
            console.info("DATABASE is not ready yet", e);
            return false;
        }
    }

    reset() {
        if (!this.dbInstance) {
            return false;
        }
        this.dbInstance.deleteDatabase(this.dbName);
        return true;
    }

    create(storeName, arrData) {
        if (!arrData?.length) {
            return;
        }
        return this.promises(storeName, arrData, "put");
    }

    readAll(storeName = [], retry = 0) {
        const storeNames =
            storeName.length > 0 ? storeName : this.dbStores.map((store) => store[1]);
        const transaction = this.getNewTransaction(storeNames, "readonly");

        if (!transaction && retry < 5) {
            return this.readAll(storeName, retry + 1);
        } else if (!transaction) {
            return new Promise((reject) => reject(false));
        }

        const promises = storeNames.map(
            (store) =>
                new Promise((resolve, reject) => {
                    const objectStore = transaction.objectStore(store);
                    const request = objectStore.getAll();

                    request.onerror = () => {
                        console.warn("Internal error reading data from the indexed database.");
                        reject();
                    };
                    request.onsuccess = (event) => {
                        const result = event.target.result;
                        resolve({ [store]: result });
                    };
                })
        );

        return Promise.allSettled(promises).then((results) =>
            results.reduce((acc, result) => {
                if (result.status === "fulfilled") {
                    return { ...acc, ...result.value };
                } else {
                    return acc;
                }
            }, {})
        );
    }

    delete(storeName, uuids) {
        if (!uuids?.length) {
            return;
        }
        return this.promises(storeName, uuids, "delete");
    }
}
