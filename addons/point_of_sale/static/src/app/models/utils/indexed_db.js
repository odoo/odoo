import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

const BATCH_SIZE = 500; // Can be adjusted based on performance testing
const TRANSACTION_TIMEOUT = 5000; // 5 seconds timeout for transactions

export default class IndexedDB {
    constructor(dbName, dbVersion, dbStores, whenReady, dialog) {
        this.db = null;
        this.dbName = dbName;
        this.dbVersion = dbVersion;
        this.dbStores = dbStores;
        this.dbInstance = null;
        this.activeTransactions = new Set();
        this.dialog = dialog;
        this._isReconnecting = false;
        this._reloadDialogShown = false;
        this.databaseEventListener(whenReady);
    }

    databaseEventListener(whenReady) {
        const indexedDB =
            window.indexedDB || window.mozIndexedDB || window.webkitIndexedDB || window.msIndexedDB;

        if (!indexedDB) {
            console.debug(
                _t(
                    "Warning: Your browser doesn't support IndexedDB. The data won't be saved. Please use a modern browser."
                )
            );
        }

        this.dbInstance = indexedDB;
        const dbInstance = indexedDB.open(this.dbName, this.dbVersion);
        dbInstance.onerror = (event) => {
            const err = event.target.error;
            console.debug("Database error:", err);
            // Known iOS/Safari WebKit bug: the IDB server process was killed by the OS.
            // No reconnect will succeed — only a page reload restores the daemon.
            if (
                err?.name === "UnknownError" &&
                err.message.includes("Connection to Indexed Database server lost")
            ) {
                this._showReloadDialog();
            }
        };
        dbInstance.onsuccess = (event) => {
            this.db = event.target.result;
            console.info(`IndexedDB ${this.dbVersion} Ready`);
            whenReady?.();
            this._setupVisibilityProbe();
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
                            console.debug("Error aborting transaction:", e);
                        }
                    }
                }, TRANSACTION_TIMEOUT);

                if (odoo.debug) {
                    console.debug(
                        `[%cIndexedDB%c]: %c${method} ${batch.length}%c ${storeName}`,
                        "color:lime;",
                        "",
                        "font-weight:bold;color:#e67e22",
                        ""
                    );
                }

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
                            console.debug("IndexedDB error:", event.target?.error);
                            reject(event.target?.error || "Unknown error");
                        };
                    } catch {
                        if (odoo.debug === "assets") {
                            console.debug(
                                `%cIndexedDB: Error processing ${method} for ${storeName}`,
                                "color: #ffb7a8"
                            );
                        }
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
            console.info("DATABASE is not ready yet", e);
            if (e.name === "InvalidStateError") {
                this.db = null;
                this._attemptReconnect();
            }
            return false;
        }
    }

    _attemptReconnect() {
        if (this._isReconnecting) {
            return;
        }
        this._isReconnecting = true;
        setTimeout(() => {
            if (this.db) {
                try {
                    this.db.close();
                } catch {
                    // already closed
                }
                this.db = null;
            }
            this.databaseEventListener();
            this._isReconnecting = false;
        }, 3000);
    }

    _setupVisibilityProbe() {
        if (this._visibilityProbeAttached) {
            return;
        }
        this._visibilityProbeAttached = true;
        document.addEventListener("visibilitychange", () => {
            if (document.visibilityState !== "visible" || !this.db) {
                return;
            }
            try {
                this.db.transaction([this.dbStores[0][1]], "readonly").abort();
            } catch {
                this.db = null;
                this._attemptReconnect();
            }
        });
    }

    _showReloadDialog() {
        if (!this.dialog || this._reloadDialogShown) {
            return;
        }
        this._reloadDialogShown = true;
        this.dialog.add(AlertDialog, {
            title: _t("Database Connection Lost"),
            body: _t(
                "The connection to the local database was lost. Reloading the page will restore it and prevent any loss of unsaved orders."
            ),
            confirmLabel: _t("Reload"),
            confirm: () => window.location.reload(),
        });
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
                        console.debug("Error reading data from the indexed database:", event);
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
