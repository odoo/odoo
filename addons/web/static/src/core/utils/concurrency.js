// @ts-check
/** @odoo-module native */

import { browser } from "@web/core/browser/browser";

/**
 * @param {number} [wait=0]
 * @returns {Promise<void>}
 */
export function delay(wait) {
    return new Promise(function (resolve) {
        browser.setTimeout(resolve, wait);
    });
}

export class SupersededError extends Error {
    constructor(message = "This task was superseded by a newer one") {
        super(message);
        this.name = "SupersededError";
    }
}

/** @template T */
export class KeepLast {
    /**
     * @param {Object} [options]
     * @param {boolean} [options.rejectSuperseded=false]
     */
    constructor({ rejectSuperseded = false } = {}) {
        this._id = 0;
        this._rejectSuperseded = rejectSuperseded;
        /** @type {((reason: unknown) => void) | null} */
        this._rejectPending = null;
        /** @type {(() => void) | null} */
        this._abortPending = null;
    }
    /** @returns {number} */
    get generation() {
        return this._id;
    }
    cancel() {
        this._id++;
        const abort = this._abortPending;
        this._abortPending = null;
        if (abort) {
            try {
                abort();
            } catch (error) {
                console.warn("[KeepLast] abort handler threw", error);
            }
        }
        if (this._rejectPending) {
            this._rejectPending(new SupersededError());
            this._rejectPending = null;
        }
    }
    /**
     * @param {Promise<T>} promise
     * @param {Object} [options]
     * @param {() => void} [options.abort]
     * @returns {Promise<T>}
     */
    add(promise, { abort } = {}) {
        this.cancel();
        const currentId = this._id;
        const ownAbort =
            abort ??
            (typeof (/** @type {any} */ (promise)?.abort) === "function"
                ? () => /** @type {any} */ (promise).abort(true)
                : null);
        this._abortPending = ownAbort;
        return new Promise((resolve, reject) => {
            if (this._rejectSuperseded) {
                this._rejectPending = reject;
            }
            promise.then(
                (value) => {
                    if (this._id === currentId) {
                        this._rejectPending = null;
                        this._abortPending = null;
                        resolve(value);
                    }
                },
                (reason) => {
                    if (this._id === currentId) {
                        this._rejectPending = null;
                        this._abortPending = null;
                        reject(reason);
                    }
                },
            );
        });
    }
}

export class Mutex {
    constructor() {
        /** @type {Promise<any>} */
        this._lock = Promise.resolve();
        /** @type {number} */
        this._queueSize = 0;
        /** @type {Promise<void> | undefined} */
        this._unlockedProm = undefined;
        /** @type {(() => void) | undefined} */
        this._unlock = undefined;
    }
    get locked() {
        return this._queueSize > 0;
    }

    /**
     * @template T
     * @param {() => (T | Promise<T>)} action
     * @returns {Promise<T>}
     */
    async exec(action) {
        this._queueSize++;
        if (!this._unlockedProm) {
            const { promise, resolve } =
                /** @type {{ promise: Promise<void>; resolve: () => void }} */ (
                    Promise.withResolvers()
                );
            this._unlockedProm = promise;
            this._unlock = () => {
                resolve();
                this._unlockedProm = undefined;
            };
        }
        const always = () => {
            let result;
            try {
                result = action();
            } catch (e) {
                result = Promise.reject(e);
            }
            return Promise.resolve(result).finally(() => {
                if (--this._queueSize === 0) {
                    /** @type {() => void} */ (this._unlock)();
                }
            });
        };
        this._lock = this._lock.then(always, always);
        return this._lock;
    }
    /** @returns {Promise<void>} */
    getUnlockedDef() {
        return this._unlockedProm || Promise.resolve();
    }
}

/** @template T */
export class KeepLastByKey {
    /**
     * @param {Object} [options]
     * @param {boolean} [options.rejectSuperseded=false]
     */
    constructor({ rejectSuperseded = false } = {}) {
        /** @type {Map<string, KeepLast<T>>} */
        this._byKey = new Map();
        this._rejectSuperseded = rejectSuperseded;
    }
    /**
     * @param {string} key
     * @returns {KeepLast<T>}
     */
    _for(key) {
        let keepLast = this._byKey.get(key);
        if (!keepLast) {
            keepLast = new KeepLast({ rejectSuperseded: this._rejectSuperseded });
            this._byKey.set(key, keepLast);
        }
        return keepLast;
    }
    /**
     * @param {string} key
     * @param {Promise<T>} promise
     * @param {Object} [options]
     * @param {() => void} [options.abort]
     * @returns {Promise<T>}
     */
    add(key, promise, options) {
        const keepLast = this._for(key);
        const result = keepLast.add(promise, options);
        const generation = keepLast.generation;
        return result.finally(() => {
            // Supersession and key reuse can both precede this settlement.
            if (
                this._byKey.get(key) === keepLast &&
                keepLast.generation === generation
            ) {
                this._byKey.delete(key);
            }
        });
    }
    /** @param {string} [key] */
    cancel(key) {
        if (key === undefined) {
            const pending = [...this._byKey.values()];
            this._byKey.clear();
            for (const keepLast of pending) {
                keepLast.cancel();
            }
            return;
        }
        const keepLast = this._byKey.get(key);
        this._byKey.delete(key);
        keepLast?.cancel();
    }
    /** @param {string} key */
    forget(key) {
        this.cancel(key);
    }
}

/** @template T */
export class Race {
    constructor() {
        /** @type {Promise<T> | null} */
        this.currentProm = null;
        /** @type {((value: T) => void) | null} */
        this.currentPromResolver = null;
        /** @type {((error: any) => void) | null} */
        this.currentPromRejecter = null;
        /** @type {number} */
        this._generation = 0;
    }
    /**
     * @param {Promise<T>} promise
     * @returns {Promise<T>}
     */
    add(promise) {
        if (!this.currentProm) {
            this._generation++;
            const gen = this._generation;
            const { promise: raceProm, resolve, reject } = Promise.withResolvers();
            this.currentProm = raceProm;
            this.currentPromResolver = (value) => {
                if (this._generation !== gen) {
                    return;
                }
                this.currentProm = null;
                this.currentPromResolver = null;
                this.currentPromRejecter = null;
                resolve(value);
            };
            this.currentPromRejecter = (error) => {
                if (this._generation !== gen) {
                    return;
                }
                this.currentProm = null;
                this.currentPromResolver = null;
                this.currentPromRejecter = null;
                reject(error);
            };
        }
        promise.then(this.currentPromResolver, this.currentPromRejecter);
        return this.currentProm;
    }
    /** @returns {Promise<T>|null} */
    getCurrentProm() {
        return this.currentProm;
    }
}

export class InFlight {
    constructor() {
        this._count = 0;
        /** @type {Promise<void> & { resolve: () => void } | null} */
        this._idle = null;
    }
    /** @returns {boolean} */
    get isBusy() {
        return this._count > 0;
    }
    /**
     * Returns the original promise, including any caller-provided methods.
     * @template {Promise<unknown>} P
     * @param {P} promise
     * @returns {P}
     */
    track(promise) {
        this._count++;
        this._idle ||= /** @type {any} */ (new Deferred());
        const settled = () => {
            if (--this._count === 0) {
                const idle = /** @type {any} */ (this._idle);
                this._idle = null;
                idle.resolve();
            }
        };
        promise.then(settled, settled);
        return promise;
    }
    /** @returns {Promise<void>} */
    whenIdle() {
        return this._idle || Promise.resolve();
    }
}

/**
 * The constructor returns a native promise with resolve/reject methods.
 * Its instance contract is augmented in @types/concurrency.d.ts.
 * @template [T=unknown]
 */
export class Deferred {
    constructor() {
        const { promise, resolve, reject } = Promise.withResolvers();
        return Object.assign(promise, { resolve, reject });
    }
}
