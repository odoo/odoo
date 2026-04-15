import { logPosMessage } from "@point_of_sale/app/utils/pretty_console_log";

const BATCH_SIZE = 1000; // Optimal balance between throughput and responsiveness
const TRANSACTION_TIMEOUT = 10000; // Increased timeout for larger batches
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
        let dbInstance;
        if (this.dbVersion) {
            dbInstance = indexedDB.open(this.dbName, this.dbVersion);
        } else {
            dbInstance = indexedDB.open(this.dbName);
        }
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

            const actualStoreNames = this.db.objectStoreNames;
            let needsUpgrade = false;

            for (const [, storeName] of this.dbStores) {
                if (!actualStoreNames.contains(storeName)) {
                    logPosMessage(
                        "IndexedDB",
                        "onsuccess",
                        `Schema mismatch: Store '${storeName}' is missing. Triggering upgrade.`,
                        CONSOLE_COLOR
                    );
                    needsUpgrade = true;
                    break;
                }
            }

            if (needsUpgrade) {
                const newVersion = this.db.version + 1;
                this.db.close();
                this.dbVersion = newVersion;

                logPosMessage(
                    "IndexedDB",
                    "onsuccess",
                    `Upgrading from v${newVersion - 1} to v${newVersion}...`,
                    CONSOLE_COLOR
                );

                this.databaseEventListener(whenReady);
                return;
            }

            logPosMessage(
                "IndexedDB",
                "databaseEventListener",
                `IndexedDB v${this.db.version} Ready`,
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

            const batchPromise = new Promise((resolve, reject) => {
                let hasError = false;

                const doneMethod = () => {
                    finished = true;
                    clearTimeout(timeoutId);
                    this.activeTransactions.delete(transaction);
                    if (!hasError) {
                        resolve();
                    }
                };

                const errorMethod = (event) => {
                    finished = true;
                    hasError = true;
                    clearTimeout(timeoutId);
                    this.activeTransactions.delete(transaction);
                    const errorMsg = event.target?.error || event.message || "Transaction failed";
                    logPosMessage(
                        "IndexedDB",
                        method,
                        `Error in transaction for ${storeName}: ${errorMsg}`,
                        CONSOLE_COLOR
                    );
                    reject(errorMsg);
                };

                transaction.oncomplete = doneMethod;
                transaction.onabort = errorMethod;
                transaction.onerror = errorMethod;

                const store = transaction.objectStore(storeName);

                timeoutId = setTimeout(() => {
                    if (!finished) {
                        errorMethod({ target: { error: "IndexedDB transaction timeout" } });
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
                    `Processing ${batch.length} items in store ${storeName}...`,
                    CONSOLE_COLOR
                );

                try {
                    // Deep clone entire batch outside loop to minimize overhead
                    const parsedBatch =
                        method === "delete" ? batch : JSON.parse(JSON.stringify(batch));
                    for (const data of parsedBatch) {
                        store[method](data);
                    }
                } catch {
                    logPosMessage(
                        "IndexedDB",
                        method,
                        `Error processing ${method} for ${storeName}: Invalid data format`,
                        CONSOLE_COLOR
                    );
                    hasError = true;
                    reject("Invalid data format");
                }
            });

            const result = await batchPromise
                .then(() => ({ status: "fulfilled" }))
                .catch((err) => ({ status: "rejected", reason: err }));
            results.push(result);

            // Yield to the main thread between batches to keep the PoS responsive.
            await new Promise((resolve) => setTimeout(resolve, 0));
        }

        return results;
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
        return new Promise((resolve) => {
            if (this.db) {
                this.db.close();
            }

            if (!this.dbInstance) {
                return resolve(true);
            }

            const timeout = setTimeout(() => {
                logPosMessage(
                    "IndexedDB",
                    "reset",
                    "Timeout: Database reset took too long",
                    CONSOLE_COLOR
                );
                resolve(false);
            }, 3000);

            const request = this.dbInstance.deleteDatabase(this.dbName);

            request.onsuccess = () => {
                logPosMessage("IndexedDB", "reset", "Database deleted successfully", CONSOLE_COLOR);
                this.db = null;
                clearTimeout(timeout);
                resolve(true);
            };

            request.onerror = (event) => {
                logPosMessage(
                    "IndexedDB",
                    "reset",
                    `Error deleting DB: ${event.target.error}`,
                    CONSOLE_COLOR
                );
                clearTimeout(timeout);
                resolve(false);
            };

            request.onblocked = () => {
                logPosMessage("IndexedDB", "reset", "Blocked deleting DB", CONSOLE_COLOR);
                clearTimeout(timeout);
                resolve(false);
            };
        });
    }

    create(storeName, arrData) {
        if (!arrData?.length) {
            return;
        }
        return this.promises(storeName, arrData, "put");
    }
    async readAllExceptStores(storeToIgnores = [], options) {
        const allStoreNames = this.dbStores.map((store) => store[1]);
        const storeNames =
            storeToIgnores.length > 0
                ? allStoreNames.filter((s) => !storeToIgnores.includes(s))
                : allStoreNames;
        return this.readAll(storeNames, options);
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
