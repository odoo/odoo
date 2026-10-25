/**
 * Returns a function, that, as long as it continues to be invoked, will not
 * be triggered. The function will be called after it stops being called for
 * N milliseconds. If `immediate` is passed, trigger the function on the
 * leading edge, instead of the trailing.
 *
 * Inspired by https://davidwalsh.name/javascript-debounce-function
 */
export function debounce(func, wait, immediate) {
    let timeout;
    return function () {
        const context = this;
        const args = arguments;
        function later() {
            timeout = null;
            if (!immediate) {
                func.apply(context, args);
            }
        }
        const callNow = immediate && !timeout;
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
        if (callNow) {
            func.apply(context, args);
        }
    };
}

/**
 * Deferred is basically a resolvable/rejectable extension of Promise.
 */
export class Deferred extends Promise {
    constructor() {
        let resolve;
        let reject;
        const prom = new Promise((res, rej) => {
            resolve = res;
            reject = rej;
        });
        return Object.assign(prom, { resolve, reject });
    }
}

export class Logger {
    static LOG_TTL = 24 * 60 * 60 * 1000; // 24 hours
    static gcInterval = null;
    static instances = [];
    _db;
    _dbPromise;

    static async gcOutdatedLogs() {
        const threshold = Date.now() - Logger.LOG_TTL;
        for (const logger of this.instances) {
            try {
                const transaction = await logger._getTransaction("readwrite");
                await new Promise((res, rej) => {
                    const store = transaction.objectStore("logs");
                    const req = store
                        .index("timestamp")
                        .openCursor(IDBKeyRange.upperBound(threshold));
                    req.onsuccess = (event) => {
                        const cursor = event.target.result;
                        if (cursor) {
                            cursor.delete();
                            cursor.continue();
                        }
                    };
                    req.onerror = (e) => rej(e.target.error);
                    transaction.oncomplete = res;
                    transaction.onerror = (e) => rej(e.target.error);
                });
            } catch (error) {
                console.error(`Failed to clear logs for logger "${logger._name}":`, error);
            }
        }
    }

    constructor(name) {
        this._name = name;
        Logger.instances.push(this);
        Logger.gcOutdatedLogs();
        clearInterval(Logger.gcInterval);
        Logger.gcInterval = setInterval(() => Logger.gcOutdatedLogs(), Logger.LOG_TTL);
    }

    async _ensureDatabaseAvailable() {
        this._dbPromise ||= new Promise((res, rej) => {
            const request = indexedDB.open(this._name, 1);
            request.onsuccess = (event) => {
                const db = event.target.result;
                db.onclose = () => this._resetDatabase(db);
                this._db = db;
                res(db);
            };
            request.onupgradeneeded = (event) => {
                if (!event.target.result.objectStoreNames.contains("logs")) {
                    const store = event.target.result.createObjectStore("logs", {
                        autoIncrement: true,
                    });
                    store.createIndex("timestamp", "timestamp", { unique: false });
                }
            };
            request.onerror = (event) => {
                this._dbPromise = null;
                rej(event);
            };
        });
        return this._dbPromise;
    }

    _resetDatabase(db) {
        if (this._db === db) {
            this._db = null;
            this._dbPromise = null;
        }
    }

    async _getTransaction(mode, retry = true) {
        const db = await this._ensureDatabaseAvailable();
        try {
            return db.transaction("logs", mode);
        } catch (error) {
            if (!retry || error.name !== "InvalidStateError") {
                throw error;
            }
            // The browser may close the connection at any time (e.g. storage pressure).
            this._resetDatabase(db);
            return this._getTransaction(mode, false);
        }
    }

    async log(message) {
        const transaction = await this._getTransaction("readwrite");
        const store = transaction.objectStore("logs");
        const addRequest = store.add({ timestamp: Date.now(), message });
        return new Promise((res, rej) => {
            addRequest.onsuccess = res;
            addRequest.onerror = rej;
        });
    }

    async getLogs() {
        await Logger.gcOutdatedLogs();
        const transaction = await this._getTransaction("readonly");
        const store = transaction.objectStore("logs");
        const request = store.getAll();
        return new Promise((res, rej) => {
            request.onsuccess = (ev) => res(ev.target.result.map(({ message }) => message));
            request.onerror = rej;
        });
    }
}
