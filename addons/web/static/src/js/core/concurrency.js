odoo.define('web.concurrency', function (require) {
"use strict";

/**
 * Concurrency Utils
 *
 * This file contains a short collection of useful helpers designed to help with
 * everything concurrency related in Odoo.
 *
 * The basic concurrency primitives in Odoo JS are the callback, and the
 * promises.  Promises (deferred) are more composable, so we usually use them
 * whenever possible.  We use the jQuery implementation.
 *
 * Those functions are really nothing special, but are simply the result of how
 * we solved some concurrency issues, when we noticed that a pattern emerged.
 */

var Class = require('web.Class');

return {
    /**
     * The jquery implementation for $.when has a (most of the time) useful
     * property: it is synchronous, if the deferred is resolved immediately.
     *
     * This means that when we execute $.when(def), then all registered
     * callbacks will be executed before the next line is executed.  This is
     * useful quite often, but in some rare cases, we might want to force an
     * async behavior. This is the purpose of this function, which simply adds a
     * setTimeout before resolving the deferred.
     *
     * @returns {Deferred}
     */
    asyncWhen: function () {
        var async = false;
        var def = $.Deferred();
        $.when.apply($, arguments).done(function() {
            var args = arguments;
            var action = function() {
                def.resolve.apply(def, args);
            };
            if (async) {
                action();
            } else {
                setTimeout(action, 0);
            }
        }).fail(function() {
            var args = arguments;
            var action = function() {
                def.reject.apply(def, args);
            };
            if (async) {
                action();
            } else {
                setTimeout(action, 0);
            }
        });
        async = true;
        return def;
    },
    /**
     * Returns a deferred resolved after 'wait' milliseconds
     *
     * @param {int} [wait=0] the delay in ms
     * @return {Deferred}
     */
    delay: function (wait) {
        var def = $.Deferred();
        setTimeout(def.resolve, wait);
        return def;
    },
    /**
     * The DropMisordered abstraction is useful for situations where you have
     * a sequence of operations that you want to do, but if one of them
     * completes after a subsequent operation, then its result is obsolete and
     * should be ignored.
     *
     * Note that is is kind of similar to the DropPrevious abstraction, but
     * subtly different.  The DropMisordered operations will all resolves if
     * they complete in the correct order.
     */
    DropMisordered: Class.extend({
        /**
         * @constructor
         *
         * @param {boolean} [failMisordered=false] whether mis-ordered responses
         *   should be failed or just ignored
         */
        init: function (failMisordered) {
            // local sequence number, for requests sent
            this.lsn = 0;
            // remote sequence number, seqnum of last received request
            this.rsn = -1;
            this.failMisordered = failMisordered || false;
        },
        /**
         * Adds a deferred (usually an async request) to the sequencer
         *
         * @param {Deferred} deferred to ensure add
         * @returns {Deferred}
         */
        add: function (deferred) {
            var res = $.Deferred();

            var self = this, seq = this.lsn++;
            deferred.done(function () {
                if (seq > self.rsn) {
                    self.rsn = seq;
                    res.resolve.apply(res, arguments);
                } else if (self.failMisordered) {
                    res.reject();
                }
            }).fail(function () {
                res.reject.apply(res, arguments);
            });

            return res.promise();
        },
    }),
    /**
     * The DropPrevious abstraction is useful when you have a sequence of
     * operations that you want to execute, but you only care of the result of
     * the last operation.
     *
     * For example, let us say that we have a _fetch method on a widget which
     * fetches data.  We want to rerender the widget after.  We could do this::
     *
     *      this._fetch().then(function (result) {
     *          self.state = result;
     *          self.render();
     *      });
     *
     * Now, we have at least two problems:
     *
     * - if this code is called twice and the second _fetch completes before the
     *   first, the end state will be the result of the first _fetch, which is
     *   not what we expect
     * - in any cases, the user interface will rerender twice, which is bad.
     *
     * Now, if we have a DropPrevious::
     *
     *      this.dropPrevious = new DropPrevious();
     *
     * Then we can wrap the _fetch in a DropPrevious and have the expected
     * result::
     *
     *      this.dropPrevious
     *          .add(this._fetch())
     *          .then(function (result) {
     *              self.state = result;
     *              self.render();
     *          });
     */
    DropPrevious: Class.extend({
        /**
         * Registers a new deferred and rejects the previous one
         *
         * @param {Deferred} deferred the new deferred
         * @returns {Promise}
         */
        add: function (deferred) {
            if (this.current_def) { this.current_def.reject(); }
            var res = $.Deferred();
            deferred.then(res.resolve, res.reject);
            this.current_def = res;
            return res.promise();
        }
    }),
    /**
     * A (Odoo) mutex is a primitive for serializing computations.  This is
     * useful to avoid a situation where two computations modify some shared
     * state and cause some corrupted state.
     *
     * Imagine that we have a function to fetch some data _load(), which returns
     * a deferred which resolves to something useful. Now, we have some code
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
    Mutex: Class.extend({
        init: function () {
            this.def = $.Deferred().resolve();
        },
        /**
         * Add a computation to the queue, it will be executed as soon as the
         * previous computations are completed.
         *
         * @param {function} action a function which may return a deferred
         * @returns {Deferred}
         */
        exec: function (action) {
            var current = this.def;
            var next = this.def = $.Deferred();
            return current.then(function() {
                return $.when(action()).always(function() {
                    next.resolve();
                });
            });
        }
    }),
    /**
     * Rejects a deferred as soon as a reference deferred is either resolved or
     * rejected
     *
     * @param {Deferred} [target_def] the deferred to potentially reject
     * @param {Deferred} [reference_def] the reference target
     * @returns {Deferred}
     */
    rejectAfter: function (target_def, reference_def) {
        var res = $.Deferred();
        target_def.then(res.resolve, res.reject);
        reference_def.always(res.reject);
        return res.promise();
    }
};

});
