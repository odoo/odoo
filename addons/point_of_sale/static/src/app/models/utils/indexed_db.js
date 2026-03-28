import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export default class IndexedDB {
    constructor(dbName, dbVersion, dbStores, dialog) {
        this.db = null;
        this.dbName = dbName;
        this.dbVersion = dbVersion;
        this.dbStores = dbStores;
        this.dbInstance = null;
        this.dialog = dialog;
        this._isReconnecting = false;
        this._reloadDialogShown = false;
        this.databaseEventListener();
    }

    databaseEventListener() {
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
            const err = event.target.error;
            console.error("Database error:", err);
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
        if (method !== "delete") {
            const data = await this.readAll([storeName]);
            const storeData = data[storeName];
            if (storeData?.length > 0) {
                for (const idx in arrData) {
                    const data = { ...arrData[idx] };
                    delete data.JSONuiState;
                    delete data.date_order;
                    delete data.write_date;

                    let alreadyExists = storeData.find((item) => item.uuid === data.uuid);
                    if (alreadyExists) {
                        alreadyExists = { ...alreadyExists };
                        delete alreadyExists.JSONuiState;
                        delete alreadyExists.date_order;
                        delete alreadyExists.write_date;
                    }

                    if (alreadyExists && JSON.stringify(alreadyExists) === JSON.stringify(data)) {
                        delete arrData[idx];
                    }
                }
            }
        }

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
            return;
        }
        this.dbInstance.deleteDatabase(this.dbName);
    }

    create(storeName, arrData) {
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
        return this.promises(storeName, uuids, "delete");
    }
}
