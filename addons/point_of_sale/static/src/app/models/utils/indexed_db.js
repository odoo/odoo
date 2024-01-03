/** @odoo-module */

import { _t } from "@web/core/l10n/translation";

const { DateTime } = luxon;

export default class IndexedDB {
    constructor(dbName, dbVersion, dbStores) {
        this.db = null;
        this.dbName = dbName;
        this.dbVersion = dbVersion;
        this.dbStores = dbStores;
        this.dbInstance = null;
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
            console.error("Database error: " + event.target.errorCode);
        };
        dbInstance.onsuccess = (event) => {
            this.db = event.target.result;
            console.info(`IndexedDB ${this.dbVersion} Ready`);
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

                    if (!alreadyExists || JSON.stringify(alreadyExists) !== JSON.stringify(data)) {
                        arrData[idx].write_date = DateTime.now().toFormat("yyyy-MM-dd HH:mm:ss");
                    } else {
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
            return new Promise((resolve, reject) => {
                const request = transaction.objectStore(storeName)[method](data);
                request.onsuccess = () => resolve();
                request.onerror = () => reject();
            });
        });

        return Promise.allSettled(promises).then((results) => {
            return results;
        });
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
            return false;
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

        return Promise.allSettled(promises).then((results) => {
            return results.reduce((acc, result) => {
                if (result.status === "fulfilled") {
                    return { ...acc, ...result.value };
                } else {
                    return acc;
                }
            }, {});
        });
    }

    delete(storeName, uuids) {
        return this.promises(storeName, uuids, "delete");
    }
}
