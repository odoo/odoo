import { logPosMessage } from "@point_of_sale/app/utils/pretty_console_log";

const BATCH_SIZE = 500; // Can be adjusted based on performance testing
const TRANSACTION_TIMEOUT = 5000; // 5 seconds timeout for transactions
const CONSOLE_COLOR = "#3ba9ff";
const INITIALIZATION_TIMEOUT = 20000; // 20 seconds timeout for initialization
const MAX_OPEN_RETRIES = 3; // Maximum retries for opening the database

class IDBError extends Error {
    constructor(type, message) {
        super(message);
        this.name = "IDBError";
        this.type = type;
    }
}

export default class IndexedDB {
    constructor(dbName, dbVersion, dbStores, whenReady) {
        this.db = null;
        this.dbName = dbName;
        this.dbStores = dbStores;
        this.dbInstance =
            window.indexedDB || window.mozIndexedDB || window.webkitIndexedDB || window.msIndexedDB;
        this.activeTransactions = new Set();
        this.databaseEventListener(whenReady);
    }

    async databaseEventListener(whenReady) {
        if (!this.dbInstance) {
            whenReady({ success: false, instance: this });
            return false;
        }

        let isInitialized = false;
        const timeout = setTimeout(() => {
            if (!isInitialized) {
                whenReady({ success: false, instance: this, timeout: true });
            }
        }, INITIALIZATION_TIMEOUT);
        let error = null;
        try {
            this.db = await this.openDatabase();
        } catch (err) {
            this.db = null;
            error = err;
            logPosMessage(
                "IndexedDB",
                "method",
                `Failed to open database: ${err.message}`,
                CONSOLE_COLOR,
                [err]
            );
        } finally {
            isInitialized = true;
            clearTimeout(timeout);
            whenReady({ success: Boolean(this.db), instance: this, error });
        }
    }

    async openDatabase(version, retryCount = 0) {
        if (retryCount >= MAX_OPEN_RETRIES) {
            throw new IDBError(
                "OpenError",
                "Failed to open database: max upgrade retries exceeded"
            );
        }

        const indexedDB = this.dbInstance;
        const name = this.dbName;
        const request = version != null ? indexedDB.open(name, version) : indexedDB.open(name);
        return new Promise((resolve, reject) => {
            let settled = false;
            const safeReject = (error) => {
                if (!settled) {
                    settled = true;
                    reject(error);
                }
            };

            request.onsuccess = (event) => {
                const db = event.target.result;
                db.onversionchange = () => {
                    logPosMessage(
                        "IndexedDB",
                        "onversionchange",
                        "Database upgrade requested by another tab",
                        CONSOLE_COLOR
                    );
                    db.close();
                };

                const storeNames = Array.from(db.objectStoreNames);
                const expectedStoreNames = this.dbStores.map((store) => store[1]);
                const storesMismatch =
                    storeNames.length !== expectedStoreNames.length ||
                    !expectedStoreNames.every((name) => storeNames.includes(name)) ||
                    !storeNames.every((name) => expectedStoreNames.includes(name));

                if (storesMismatch) {
                    const dbVersion = db.version;
                    db.close();
                    resolve(this.openDatabase(dbVersion + 1, retryCount + 1));
                    return;
                }

                settled = true;
                resolve(db);
            };

            request.onerror = (event) => {
                const error = event.target.error;
                safeReject(
                    new IDBError("RequestError", error?.message || "Database request failed")
                );
            };

            request.onblocked = () => {
                safeReject(
                    new IDBError(
                        "BlockedError",
                        "Database upgrade blocked by another open connection"
                    )
                );
            };

            request.onupgradeneeded = (event) => {
                const { oldVersion, newVersion } = event;
                logPosMessage(
                    "IndexedDB",
                    "onupgradeneeded",
                    `Upgrading database from version ${oldVersion} to ${newVersion}`,
                    CONSOLE_COLOR
                );

                const db = event.target.result;
                const tx = event.target.transaction;

                tx.onabort = () =>
                    safeReject(new IDBError("AbortError", tx.error?.message || "Upgrade aborted"));

                const allNames = new Set();
                for (const [id, storeName] of this.dbStores) {
                    allNames.add(storeName);
                    if (!db.objectStoreNames.contains(storeName)) {
                        db.createObjectStore(storeName, { keyPath: id });
                    }
                }

                for (const name of db.objectStoreNames) {
                    if (!allNames.has(name)) {
                        db.deleteObjectStore(name);
                    }
                }
            };
        });
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
            const transaction = await this.getNewTransaction([storeName], "readwrite");

            if (!transaction) {
                logPosMessage(
                    "IndexedDB",
                    method,
                    `Failed to create transaction for store ${storeName}`,
                    CONSOLE_COLOR
                );
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
                            doneMethod();
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
                    const onRequestError = (error) => {
                        hasError = true;
                        clearTimeout(timeoutId);
                        logPosMessage(
                            "IndexedDB",
                            method,
                            `Error processing ${method} for ${storeName}: ${error.message}`,
                            CONSOLE_COLOR
                        );
                        reject(error || "Unknown error");
                    };

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
                            onRequestError(event.target?.error);
                            hasError = true;
                        };
                    } catch {
                        onRequestError(new Error("Invalid data format"));
                    }
                }
            });

            const result = await batchPromise
                .then(() => ({ status: "fulfilled" }))
                .catch((err) => ({ status: "rejected", reason: err }));
            results.push(result);
        }

        return results;
    }

    async getNewTransaction(dbStore, mode = "readwrite") {
        try {
            if (!this.db) {
                return false;
            }

            const transaction = this.db.transaction(dbStore, mode);
            this.activeTransactions.add(transaction);
            return transaction;
        } catch (e) {
            logPosMessage(
                "IndexedDB",
                "getNewTransaction",
                `Error creating transaction: ${e.message}`,
                CONSOLE_COLOR,
                [e]
            );
            return false;
        }
    }

    async reset() {
        if (!this.dbInstance) {
            return false;
        }

        // Close existing connection
        if (this.db) {
            this.db.close();
            this.db = null;
        }

        return new Promise((resolve) => {
            const request = this.dbInstance.deleteDatabase(this.dbName);

            request.onsuccess = () => {
                logPosMessage(
                    "IndexedDB",
                    "reset",
                    `Database ${this.dbName} deleted successfully`,
                    CONSOLE_COLOR
                );
                resolve(true);
            };

            request.onerror = (event) => {
                logPosMessage(
                    "IndexedDB",
                    "reset",
                    `Failed to delete database: ${event.target.error}`,
                    CONSOLE_COLOR
                );
                resolve(false);
            };

            request.onblocked = () => {
                logPosMessage(
                    "IndexedDB",
                    "reset",
                    "Database deletion blocked by open connections",
                    CONSOLE_COLOR
                );
            };
        });
    }

    create(storeName, arrData) {
        if (!arrData?.length) {
            return;
        }
        return this.promises(storeName, arrData, "put");
    }

    async readAll(store = [], retry = 0) {
        const storeNames = store.length > 0 ? store : this.dbStores.map((store) => store[1]);
        const transaction = await this.getNewTransaction(storeNames, "readonly");

        if (!transaction && retry < 5) {
            await new Promise((r) => setTimeout(r, 100));
            return this.readAll(store, retry + 1);
        } else if (!transaction) {
            return false;
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
