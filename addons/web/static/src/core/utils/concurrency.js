// @ts-check

/** @module @web/core/utils/concurrency - Async primitives: Mutex, KeepLast, Race, Deferred, and delay */

/**
 * Returns a promise resolved after 'wait' milliseconds
 *
 * @param {number} [wait=0] the delay in ms
 * @returns {Promise<void>}
 */
export function delay(wait) {
    return new Promise(function (resolve) {
        setTimeout(resolve, wait);
    });
}

/**
 * KeepLast is a concurrency primitive that manages a list of tasks, and only
 * keeps the last task active.  When a new task is added, any previously pending
 * task is silently discarded — its wrapper promise never settles.
 *
 * @template T
 */
export class KeepLast {
    constructor() {
        this._id = 0;
    }
    /**
     * Register a new task.  If a task was already pending it is superseded:
     * its wrapper promise will never resolve or reject.
     *
     * @param {Promise<T>} promise
     * @returns {Promise<T>}
     */
    add(promise) {
        this._id++;
        const currentId = this._id;
        return new Promise((resolve, reject) => {
            promise.then(
                (value) => {
                    if (this._id === currentId) {
                        resolve(value);
                    }
                    // Superseded — silently discard.
                },
                (reason) => {
                    if (this._id === currentId) {
                        reject(reason);
                    }
                    // Superseded — silently discard.
                },
            );
        });
    }
}

/**
 * A (Odoo) mutex is a primitive for serializing computations.  This is
 * useful to avoid a situation where two computations modify some shared
 * state and cause some corrupted state.
 *
 * Imagine that we have a function to fetch some data _load(), which returns
 * a promise which resolves to something useful. Now, we have some code
 * looking like this::
 *
 *      return this._load().then(function (result) {
 *          this.state = result;
 *      });
 *
 * If this code is run twice, but the second execution ends before the
 * first, then the final state will be the result of the first call to
 * _load.  However, if we have a mutex::
 *
 *      this.mutex = new Mutex();
 *
 * and if we wrap the calls to _load in a mutex::
 *
 *      return this.mutex.exec(function() {
 *          return this._load().then(function (result) {
 *              this.state = result;
 *          });
 *      });
 *
 * Then, it is guaranteed that the final state will be the result of the
 * second execution.
 *
 * A Mutex has to be a class, and not a function, because we have to keep
 * track of some internal state.
 */
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
    /**
     * Add a computation to the queue, it will be executed as soon as the
     * previous computations are completed.
     *
     * @template T
     * @param {() => (T | Promise<T>)} action a function which may return a Promise
     * @returns {Promise<T>}
     */
    async exec(action) {
        this._queueSize++;
        if (!this._unlockedProm) {
            const { promise, resolve } = Promise.withResolvers();
            this._unlockedProm = promise;
            this._unlock = () => {
                resolve();
                this._unlockedProm = undefined;
            };
        }
        const always = () =>
            Promise.resolve(action()).finally(() => {
                if (--this._queueSize === 0) {
                    this._unlock();
                }
            });
        this._lock = this._lock.then(always, always);
        return this._lock;
    }
    /**
     * @returns {Promise<void>} resolved as soon as the Mutex is unlocked
     *   (directly if it is currently idle)
     */
    getUnlockedDef() {
        return this._unlockedProm || Promise.resolve();
    }
}

/**
 * Race is a class designed to manage concurrency problems inspired by
 * Promise.race(), except that it is dynamic in the sense that promises can be
 * added anytime to a Race instance. When a promise is added, it returns another
 * promise which resolves as soon as a promise, among all added promises, is
 * resolved. The race is thus over. From that point, a new race will begin the
 * next time a promise will be added.
 *
 * @template T
 */
export class Race {
    constructor() {
        /** @type {Promise<T> | null} */
        this.currentProm = null;
        /** @type {((value: T) => void) | null} */
        this.currentPromResolver = null;
        /** @type {((error: any) => void) | null} */
        this.currentPromRejecter = null;
    }
    /**
     * Register a new promise. If there is an ongoing race, the promise is added
     * to that race. Otherwise, it starts a new race. The returned promise
     * resolves as soon as the race is over, with the value of the first resolved
     * promise added to the race.
     *
     * @param {Promise<T>} promise
     * @returns {Promise<T>}
     */
    add(promise) {
        if (!this.currentProm) {
            const { promise, resolve, reject } = Promise.withResolvers();
            this.currentProm = promise;
            this.currentPromResolver = (value) => {
                this.currentProm = null;
                this.currentPromResolver = null;
                this.currentPromRejecter = null;
                resolve(value);
            };
            this.currentPromRejecter = (error) => {
                this.currentProm = null;
                this.currentPromResolver = null;
                this.currentPromRejecter = null;
                reject(error);
            };
        }
        promise.then(this.currentPromResolver).catch(this.currentPromRejecter);
        return this.currentProm;
    }
    /**
     * @returns {Promise<T>|null} promise resolved as soon as the race is over, or
     *   null if there is no race ongoing)
     */
    getCurrentProm() {
        return this.currentProm;
    }
}

/**
 * A native Promise enriched with public `resolve` and `reject` methods.
 * The constructor returns a Promise (not a Deferred instance) due to the
 * constructor return override — prefer `Promise.withResolvers()` in new code.
 *
 * @template [T=unknown]
 * @returns {Promise<T> & { resolve: (value: T | PromiseLike<T>) => void, reject: (reason?: any) => void }}
 */
export class Deferred {
    constructor() {
        const { promise, resolve, reject } = Promise.withResolvers();
        return Object.assign(promise, { resolve, reject });
    }
}
