/** @odoo-module **/

/**
 * KeepLast is a concurrency primitive that manages a list of tasks, and only
 * keeps the last task active.
 */
export class KeepLast {
    constructor() {
        this._id = 0;
    }
    /**
     * Register a new task
     *
     * @template T
     * @param {Promise<T>} promise
     * @returns {Promise<T>}
     */
    add(promise) {
        this._id++;
        const currentId = this._id;
        return new Promise((resolve, reject) => {
            promise
                .then((value) => {
                    if (this._id === currentId) {
                        resolve(value);
                    }
                })
                .catch((reason) => {
                    // not sure about this part
                    if (this._id === currentId) {
                        reject(reason);
                    }
                });
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
        this._lock = Promise.resolve();
        this._queueSize = 0;
        this._unlockedProm = undefined;
        this._unlock = undefined;
    }
    /**
     * Add a computation to the queue, it will be executed as soon as the
     * previous computations are completed.
     *
     * @param {function} action a function which may return a Promise
     * @returns {Promise}
     */
    async exec(action) {
        this._queueSize++;
        if (!this._unlockedProm) {
            this._unlockedProm = new Promise((resolve) => {
                this._unlock = () => {
                    resolve();
                    this._unlockedProm = undefined;
                };
            });
        }
        const always = () => {
            return Promise.resolve(action()).finally(() => {
                if (--this._queueSize === 0) {
                    this._unlock();
                }
            });
        };
        this._lock = this._lock.then(always, always);
        return this._lock;
    }
    /**
     * @returns {Promise} resolved as soon as the Mutex is unlocked
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
 */
export class Race {
    constructor() {
        this.currentProm = null;
        this.currentPromResolver = null;
    }
    /**
     * Register a new promise. If there is an ongoing race, the promise is added
     * to that race. Otherwise, it starts a new race. The returned promise
     * resolves as soon as the race is over, with the value of the first resolved
     * promise added to the race.
     *
     * @param {Promise} promise
     * @returns {Promise
     */
    add(promise) {
        if (!this.currentProm) {
            this.currentProm = new Promise((resolve) => {
                this.currentPromResolver = (value) => {
                    this.currentProm = null;
                    this.currentPromResolver = null;
                    resolve(value);
                };
            });
        }
        promise.then(this.currentPromResolver);
        return this.currentProm;
    }
    /**
     * @returns {Promise|null} promise resolved as soon as the race is over, or
     *   null if there is no race ongoing)
     */
    getCurrentProm() {
        return this.currentProm;
    }
}

/**
 * Deferred is basically a resolvable/rejectable extension of Promise.
 */
export class Deferred {
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
