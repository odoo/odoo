import { logPosMessage } from "@point_of_sale/app/utils/pretty_console_log";

const BATCH_SIZE = 500; // Can be adjusted based on performance testing
const TRANSACTION_TIMEOUT = 5000; // 5 seconds timeout for transactions
const CONSOLE_COLOR = "#3ba9ff";

export default class IndexedDB {
    constructor(dbName, dbVersion, dbStores, whenReady) {
        this.db = null;
        this.dbName = dbName;
        this.dbVersion = dbVersion;
        this.dbStores = dbStores;
        this.dbInstance = null;
        this.activeTransactions = new Set();
        this.databaseEventListener(whenReady);
    }

    databaseEventListener(whenReady) {
        const indexedDB =
            window.indexedDB || window.mozIndexedDB || window.webkitIndexedDB || window.msIndexedDB;

        if (!indexedDB) {
            logPosMessage(
                "IndexedDB",
                "databaseEventListener",
                "Your browser does not support IndexedDB. Data will not be saved.",
                CONSOLE_COLOR
            );
        }

        this.dbInstance = indexedDB;
        const dbInstance = indexedDB.open(this.dbName, this.dbVersion);
        dbInstance.onerror = (event) => {
            logPosMessage(
                "IndexedDB",
                "databaseEventListener",
                `Error opening IndexedDB: ${event.target.errorCode}`,
                CONSOLE_COLOR
            );
        };
        dbInstance.onsuccess = (event) => {
            this.db = event.target.result;
            logPosMessage(
                "IndexedDB",
                "databaseEventListener",
                `IndexedDB ${this.dbVersion} Ready`,
                CONSOLE_COLOR
            );
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
            let timeoutId;
            let finished = false;

            const batch = arrData.slice(i, i + BATCH_SIZE);
            const transaction = this.getNewTransaction([storeName], "readwrite");

            if (!transaction) {
                results.push(Promise.reject("Transaction could not be created"));
                continue;
            }

            const doneMethod = () => {
                finished = true;
                clearTimeout(timeoutId);
                this.activeTransactions.delete(transaction);
            };

            // Mark transaction as finished in all cases
            transaction.oncomplete = doneMethod;
            transaction.onabort = doneMethod;
            transaction.onerror = doneMethod;
            transaction.onsuccess = doneMethod;

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
                            logPosMessage(
                                "IndexedDB",
                                method,
                                `Error aborting transaction: ${e.message}`,
                                CONSOLE_COLOR
                            );
                        }
                    }
                }, TRANSACTION_TIMEOUT);

                logPosMessage(
                    "IndexedDB",
                    method,
                    `Processing ${batch.length} items in store ${storeName}`,
                    CONSOLE_COLOR
                );

                for (const data of batch) {
                    try {
                        const deepCloned = JSON.parse(JSON.stringify(data));
                        const request = store[method](deepCloned);

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
                            logPosMessage(
                                "IndexedDB",
                                method,
                                `Error processing ${method} for ${storeName}: ${event.target?.error}`,
                                CONSOLE_COLOR
                            );
                            reject(event.target?.error || "Unknown error");
                        };
                    } catch {
                        logPosMessage(
                            "IndexedDB",
                            method,
                            `Error processing ${method} for ${storeName}: Invalid data format`,
                            CONSOLE_COLOR
                        );
                    }
                }
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

            const transaction = this.db.transaction(dbStore, "readwrite");
            this.activeTransactions.add(transaction);
            return transaction;
        } catch (e) {
            logPosMessage(
                "IndexedDB",
                "getNewTransaction",
                `Error creating transaction: ${e.message}`,
                CONSOLE_COLOR
            );
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

    readAll(store = [], retry = 0) {
        const storeNames = store.length > 0 ? store : this.dbStores.map((store) => store[1]);
        const transaction = this.getNewTransaction(storeNames, "readonly");

        if (!transaction && retry < 5) {
            return this.readAll(store, retry + 1);
        } else if (!transaction) {
            return new Promise((reject) => reject(false));
        }

        const removeTransaction = () => {
            this.activeTransactions.delete(transaction);
        };

        transaction.oncomplete = removeTransaction;
        transaction.onabort = removeTransaction;
        transaction.onerror = removeTransaction;
        transaction.onsuccess = removeTransaction;

        const promises = storeNames.map(
            (store) =>
                new Promise((resolve, reject) => {
                    const objectStore = transaction.objectStore(store);
                    const request = objectStore.getAll();

                    const errorMethod = (event) => {
                        logPosMessage(
                            "IndexedDB",
                            "readAll",
                            `Error reading data from store ${store}: ${event.target.error}`,
                            CONSOLE_COLOR
                        );
                        reject(event.target.error || "Unknown error");
                    };

                    const successMethod = (event) => {
                        const result = event.target.result;
                        resolve({ [store]: result });
                    };

                    request.onerror = errorMethod;
                    request.onabort = errorMethod;
                    request.onsuccess = successMethod;
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
