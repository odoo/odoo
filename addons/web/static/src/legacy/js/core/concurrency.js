/** @odoo-module **/

/**
 * Concurrency Utils
 *
 * This file contains a short collection of useful helpers designed to help with
 * everything concurrency related in Odoo.
 *
 * The basic concurrency primitives in Odoo JS are the callback, and the
 * promises.  Promises (promise) are more composable, so we usually use them
 * whenever possible.  We use the jQuery implementation.
 *
 * Those functions are really nothing special, but are simply the result of how
 * we solved some concurrency issues, when we noticed that a pattern emerged.
 */

import Class from "@web/legacy/js/core/class";

const concurrency = {
    /**
     * A MutexedDropPrevious is a primitive for serializing computations while
     * skipping the ones that where executed between a current one and before
     * the execution of a new one. This is useful to avoid useless RPCs.
     *
     * You can read the Mutex description to understand its role ; for the
     * DropPrevious part of this abstraction, imagine the following situation:
     * you have a code that call the server with a fixed argument and a list of
     * operations that only grows after each call and you only care about the
     * RPC result (the server code doesn't do anything). If this code is called
     * three times (A B C) and C is executed before B has started, it's useless
     * to make an extra RPC (B) if you know that it won't have an impact and you
     * won't use its result.
     *
     * Note that the promise returned by the exec call won't be resolved if
     * exec is called before the first exec call resolution ; only the promise
     * returned by the last exec call will be resolved (the other are rejected);
     *
     * A MutexedDropPrevious has to be a class, and not a function, because we
     * have to keep track of some internal state. The exec function takes as
     * argument an action (and not a promise as DropPrevious for example)
     * because it's the MutexedDropPrevious role to trigger the RPC call that
     * returns a promise when it's time.
     */
    MutexedDropPrevious: Class.extend({
        init: function () {
            this.locked = false;
            this.currentProm = null;
            this.pendingAction = null;
            this.pendingProm = null;
        },
        /**
         * @param {function} action a function which may return a promise
         * @returns {Promise}
         */
        exec: function (action) {
            var self = this;
            var resolution;
            var rejection;
            if (this.locked) {
                this.pendingAction = action;
                var oldPendingDef = this.pendingProm;

                this.pendingProm = new Promise(function (resolve, reject) {
                    resolution = resolve;
                    rejection = reject;
                    if (oldPendingDef) {
                        oldPendingDef.reject();
                    }
                    self.currentProm.reject();
                });
                this.pendingProm.resolve = resolution;
                this.pendingProm.reject = rejection;
                return this.pendingProm;
            } else {
                this.locked = true;
                this.currentProm = new Promise(function (resolve, reject) {
                    resolution = resolve;
                    rejection = reject;
                    function unlock() {
                        self.locked = false;
                        if (self.pendingAction) {
                            var action = self.pendingAction;
                            var prom = self.pendingProm;
                            self.pendingAction = null;
                            self.pendingProm = null;
                            self.exec(action)
                                .then(prom.resolve)
                                .guardedCatch(prom.reject);
                        }
                    }
                    Promise.resolve(action())
                        .then(function (result) {
                            resolve(result);
                            unlock();
                        })
                        .guardedCatch(function (reason) {
                            reject(reason);
                            unlock();
                        });
                });
                this.currentProm.resolve = resolution;
                this.currentProm.reject = rejection;
                return this.currentProm;
            }
        }
    }),
};

export default concurrency;
