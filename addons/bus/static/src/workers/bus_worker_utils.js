/**
 * Copied from "@web/core/utils/timings" as the websocket worker should work with the
 * minimal amount of dependencies.
 *
 * Creates and returns a new debounced version of the passed function (func) which will
 * postpone its execution until after 'delay' milliseconds have elapsed since the last
 * time it was invoked. The debounced function will return a Promise that will be resolved
 * when the function (func) has been fully executed.
 *
 * If both `options.trailing` and `options.leading` are true, the function will only be
 * invoked at the trailing edge if the debounced function was called at least once more
 * during the wait time.
 *
 * @template {Function} T the return type of the original function
 * @param {T} func the function to debounce
 * @param {number} delay
 * @param {boolean} [options] if true, equivalent to exclusive leading. If false,
 * equivalent to exclusive trailing.
 * @param {object} [options]
 * @param {boolean} [options.leading=false] whether the function should be invoked at the
 * leading edge of the timeout
 * @param {boolean} [options.trailing=true] whether the function should be invoked at the
 * trailing edge of the timeout
 * @returns {T & { cancel: () => void }} the debounced function
 */
export function debounce(func, delay, options) {
    let handle;
    const funcName = func.name ? func.name + " (debounce)" : "debounce";
    let lastArgs;
    let leading = false;
    let trailing = true;
    if (typeof options === "boolean") {
        leading = options;
        trailing = !options;
    } else if (options) {
        leading = options.leading ?? leading;
        trailing = options.trailing ?? trailing;
    }

    return Object.assign(
        {
            /** @type {any} */
            [funcName](...args) {
                return new Promise((resolve) => {
                    if (leading && !handle) {
                        Promise.resolve(func.apply(this, args)).then(resolve);
                    } else {
                        lastArgs = args;
                    }
                    clearTimeout(handle);
                    handle = setTimeout(() => {
                        handle = null;
                        if (trailing && lastArgs) {
                            Promise.resolve(func.apply(this, lastArgs)).then(resolve);
                            lastArgs = null;
                        }
                    }, delay);
                });
            },
        }[funcName],
        {
            cancel(execNow = false) {
                clearTimeout(handle);
                if (execNow && lastArgs) {
                    func.apply(this, lastArgs);
                }
            },
        }
    );
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

/**
 * A Set that maintains a maximum size by evicting the oldest entries once the capacity
 * threshold is exceeded.
 */
export class BoundedSet extends Set {
    constructor(maxSize, iterable = null) {
        super(iterable);
        this.maxSize = maxSize;
    }

    add(item) {
        super.add(item);
        if (this.size > this.maxSize) {
            this.delete(this.values().next().value);
        }
        return this;
    }
}
