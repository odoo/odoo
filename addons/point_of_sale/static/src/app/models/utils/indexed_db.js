import { _t } from "@web/core/l10n/translation";

const BATCH_SIZE = 500; // Can be adjusted based on performance testing
const TRANSACTION_TIMEOUT = 5000; // 5 seconds timeout for transactions

export default class IndexedDB {
    constructor(dbName, dbVersion, dbStores, whenReady) {
        this.db = null;
        this.dbName = dbName;
        this.dbVersion = dbVersion;
        this.dbStores = dbStores;
        this.dbInstance = null;
        this.activeTransactions = 0;
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
        if (!arrData?.length) {
            return;
        }
        // Batch processing for large arrays to avoid performance issues
        // or transaction failures due to large data sets
        const results = [];
        for (let i = 0; i < arrData.length; i += BATCH_SIZE) {
            const batch = arrData.slice(i, i + BATCH_SIZE);
            const transaction = this.getNewTransaction([storeName], "readwrite");

            if (!transaction) {
                results.push(Promise.reject("Transaction could not be created"));
                continue;
            }

            let timeoutId;
            let finished = false;

            const doneMethod = () => {
                finished = true;
                clearTimeout(timeoutId);
            };

            // Mark transaction as finished in all cases
            transaction.oncomplete = doneMethod;
            transaction.onabort = doneMethod;
            transaction.onerror = doneMethod;

            const batchPromise = new Promise((resolve, reject) => {
                const store = transaction.objectStore(storeName);
                let completed = 0;
                let hasError = false;

                timeoutId = setTimeout(() => {
                    if (!finished) {
                        reject(new Error("IndexedDB transaction timeout"));
                        try {
                            transaction.abort();
                        } catch (e) {
                            console.error("Error aborting transaction:", e);
                        }
                    }
                }, TRANSACTION_TIMEOUT);

                if (odoo.debug) {
                    console.debug(
                        `%cIndexedDB: ${method} ${storeName} with ${batch.length} items`,
                        "color: #ffb7a8"
                    );
                }

                batch.forEach((data) => {
                    const request = store[method](data);

                    request.onsuccess = () => {
                        completed++;
                        if (completed === batch.length && !hasError && !finished) {
                            clearTimeout(timeoutId);
                            resolve();
                        }
                    };

                    request.onerror = (event) => {
                        hasError = true;
                        clearTimeout(timeoutId);
                        console.error("IndexedDB error:", event.target?.error);
                        reject(event.target?.error || "Unknown error");
                    };
                });
            });

            results.push(batchPromise);
        }

        return Promise.allSettled(results);
    }

    getNewTransaction(dbStore) {
        try {
            if (!this.db) {
                return false;
            }

            this.activeTransactions++;
            const transaction = this.db.transaction(dbStore, "readwrite");
            transaction.onerror = () => this.activeTransactions--;
            transaction.onabort = () => this.activeTransactions--;
            transaction.oncomplete = () => this.activeTransactions--;
            return transaction;
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
