odoo.define('mail/static/src/utils/throttle/throttle.js', function (require) {
'use strict';

const { makeDeferred } = require('mail/static/src/utils/deferred/deferred.js');

/**
 * This module define an utility function that enables throttling calls on a
 * provided function. Such throttled calls can be canceled, flushed and/or
 * cleared:
 *
 * - cancel: Canceling a throttle function call means that if a function call is
 *   pending invocation, cancel removes this pending call invocation. It however
 *   preserves the internal timer of the cooling down phase of this throttle
 *   function, meaning that any following throttle function call will be pending
 *   and has to wait for the remaining time of the cooling down phase before
 *   being invoked.
 *
 * - flush: Flushing a throttle function call means that if a function call is
 *   pending invocation, flush immediately terminates the cooling down phase and
 *   the pending function call is immediately invoked. Flush also works without
 *   any pending function call: it just terminates the cooling down phase, so
 *   that a following function call is guaranteed to be immediately called.
 *
 * - clear: Clearing a throttle function combines canceling and flushing
 *   together.
 */

//------------------------------------------------------------------------------
// Errors
//------------------------------------------------------------------------------

/**
 * List of internal and external Throttle errors.
 * Internal errors are prefixed with `_`.
 */

 /**
  * Error when throttle function has been canceled with `.cancel()`. Used to
  * let the caller know of throttle function that the call has been canceled,
  * which means the inner function will not be called. Usually caller should
  * just accept it and kindly treat this error as a polite warning.
  */
class ThrottleCanceledError extends Error {
    /**
     * @override
     */
    constructor(throttleId, ...args) {
        super(...args);
        this.name = 'ThrottleCanceledError';
        this.throttleId = throttleId;
    }
}
/**
 * Error when throttle function has been reinvoked again. Used to let know
 * caller of throttle function that the call has been canceled and replaced with
 * another one, which means the (potentially) following inner function will be
 * in the context of another call. Same as for `ThrottleCanceledError`, usually
 * caller should just accept it and kindly treat this error as a polite
 * warning.
 */
class ThrottleReinvokedError extends Error {
    /**
     * @override
     */
    constructor(throttleId, ...args) {
        super(...args);
        this.name = 'ThrottleReinvokedError';
        this.throttleId = throttleId;
    }
}
/**
 * Error when throttle function has been flushed with `.flush()`. Used
 * internally to immediately invoke pending inner functions, since a flush means
 * the termination of cooling down phase.
 *
 * @private
 */
class _ThrottleFlushedError extends Error {
    /**
     * @override
     */
    constructor(throttleId, ...args) {
        super(...args);
        this.name = '_ThrottleFlushedError';
        this.throttleId = throttleId;
    }
}

//------------------------------------------------------------------------------
// Private
//------------------------------------------------------------------------------

/**
 * This class models the behaviour of the cancelable, flushable and clearable
 * throttle version of a provided function. See definitions at the top of this
 * file.
 */
class Throttle {

    /**
     * @param {Object} env the OWL env
     * @param {function} func provided function for making throttled version.
     * @param {integer} duration duration of the 'cool down' phase, i.e.
     *   the minimum duration between the most recent function call that has
     *   been made and the following function call (of course, assuming no flush
     *   in-between).
     */
    constructor(env, func, duration) {
        /**
         * Reference to the OWL envirionment. Useful to fine-tune control of
         * time flow in tests.
         * @see mail/static/src/utils/test_utils.js:start.hasTimeControl
         */
        this.env = env;
        /**
         * Unique id of this throttle function. Useful for the ThrottleError
         * management, in order to determine whether these errors come from
         * this throttle or from another one (e.g. inner function makes use of
         * another throttle).
         */
        this.id = _.uniqueId('throttle_');
        /**
         * Deferred of current cooling down phase in progress. Defined only when
         * there is a cooling down phase in progress. Resolved when cooling down
         * phase terminates from timeout, and rejected if flushed.
         *
         * @see _ThrottleFlushedError for rejection of this deferred.
         */
        this._coolingDownDeferred = undefined;
        /**
         * Duration, in milliseconds, of the cool down phase.
         */
        this._duration = duration;
        /**
         * Inner function to be invoked and throttled.
         */
        this._function = func;
        /**
         * Determines whether the throttle function is currently in cool down
         * phase. Cool down phase happens just after inner function has been
         * invoked, and during this time any following function call are pending
         * and will be invoked only after the end of the cool down phase (except
         * if canceled).
         */
        this._isCoolingDown = false;
        /**
         * Deferred of a currently pending invocation to inner function. Defined
         * only during a cooling down phase and just after when throttle
         * function has been called during this cooling down phase. It is kept
         * until cooling down phase ends (either from timeout or flushed
         * throttle) or until throttle is canceled (i.e. removes pending invoke
         * while keeping cooling down phase live on).
         */
        this._pendingInvokeDeferred = undefined;
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Cancel any buffered function call while keeping the cooldown phase
     * running.
     */
    cancel() {
        if (!this._isCoolingDown) {
            return;
        }
        if (!this._pendingInvokeDeferred) {
            return;
        }
        this._pendingInvokeDeferred.reject(new ThrottleCanceledError(this.id));
    }

    /**
     * Clear any buffered function call and immediately terminates any cooling
     * down phase in progress.
     */
    clear() {
        this.cancel();
        this.flush();
    }

    /**
     * Called when there is a call to the function. This function is throttled,
     * so the time it is called depends on whether the "cooldown stage" occurs
     * or not:
     *
     * - no cooldown stage: function is called immediately, and it starts
     *      the cooldown stage when successful.
     * - in cooldown stage: function is called when the cooldown stage has
     *      ended from timeout.
     *
     * Note that after the cooldown stage, only the last attempted function
     * call will be considered.
     *
     * @param {...any} args
     * @throws {ThrottleReinvokedError|ThrottleCanceledError}
     * @returns {any} result of called function, if it's called.
     */
    async do(...args) {
        if (!this._isCoolingDown) {
            return this._invokeFunction(...args);
        }
        if (this._pendingInvokeDeferred) {
            this._pendingInvokeDeferred.reject(new ThrottleReinvokedError(this.id));
        }
        try {
            this._pendingInvokeDeferred = makeDeferred();
            await Promise.race([this._coolingDownDeferred, this._pendingInvokeDeferred]);
        } catch (error) {
            if (
                !(error instanceof _ThrottleFlushedError) ||
                error.throttleId !== this.id
            ) {
                throw error;
            }
        } finally {
            this._pendingInvokeDeferred = undefined;
        }
        return this._invokeFunction(...args);
    }

    /**
     * Flush the internal throttle timer, so that the following function call
     * is immediate. For instance, if there is a cooldown stage, it is aborted.
     */
    flush() {
        if (!this._isCoolingDown) {
            return;
        }
        const coolingDownDeferred = this._coolingDownDeferred;
        this._coolingDownDeferred = undefined;
        this._isCoolingDown = false;
        coolingDownDeferred.reject(new _ThrottleFlushedError(this.id));
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Invoke the inner function of this throttle and starts cooling down phase
     * immediately after.
     *
     * @private
     * @param  {...any} args
     */
    _invokeFunction(...args) {
        const res = this._function(...args);
        this._startCoolingDown();
        return res;
    }

    /**
     * Called just when the inner function is being called. Starts the cooling
     * down phase, which turn any call to this throttle function as pending
     * inner function calls. This will be called after the end of cooling down
     * phase (except if canceled).
     */
    async _startCoolingDown() {
        if (this._coolingDownDeferred) {
            throw new Error("Cannot start cooling down if there's already a cooling down in progress.");
        }
        // Keep local reference of cooling down deferred, because the one stored
        // on `this` could be overwritten by another call to this throttle.
        const coolingDownDeferred = makeDeferred();
        this._coolingDownDeferred = coolingDownDeferred;
        this._isCoolingDown = true;
        const cooldownTimeoutId = this.env.browser.setTimeout(
            () => coolingDownDeferred.resolve(),
            this._duration
        );
        let unexpectedError;
        try {
            await coolingDownDeferred;
        } catch (error) {
            if (
                !(error instanceof _ThrottleFlushedError) ||
                error.throttleId !== this.id
            ) {
                // This branching should never happen.
                // Still defined in case of programming error.
                unexpectedError = error;
            }
        } finally {
            this.env.browser.clearTimeout(cooldownTimeoutId);
            this._coolingDownDeferred = undefined;
            this._isCoolingDown = false;
        }
        if (unexpectedError) {
            throw unexpectedError;
        }
    }

}

//------------------------------------------------------------------------------
// Public
//------------------------------------------------------------------------------

/**
 * A function that creates a cancelable, flushable and clearable throttle
 * version of a provided function. See definitions at the top of this file.
 *
 * This throttle mechanism allows calling a function at most once during a
 * certain period:
 *
 * - When a function call is made, it enters a 'cooldown' phase, in which any
 *     attempt to call the function is buffered until the cooldown phase ends.
 * - At most 1 function call can be buffered during the cooldown phase, and the
 *     latest one in this phase will be considered at its end.
 * - When a cooldown phase ends, any buffered function call will be performed
 *     and another cooldown phase will follow up.
 *
 * @param {Object} env the OWL env
 * @param {function} func the function to throttle.
 * @param {integer} duration duration, in milliseconds, of the cooling down
 *   phase of the throttling.
 * @param {Object} [param2={}]
 * @param {boolean} [param2.silentCancelationErrors=true] if unset, caller
 *   of throttle function will observe some errors that come from current
 *   throttle call that has been canceled, such as when throttle function has
 *   been explicitly canceled with `.cancel()` or when another new throttle call
 *   has been registered.
 *   @see ThrottleCanceledError for when a call has been canceled from explicit
 *     call.
 *   @see ThrottleReinvokedError for when a call has been canceled from another
 *     new throttle call has been registered.
 * @returns {function} the cancelable, flushable and clearable throttle version
 *   of the provided function.
 */
function throttle(
    env,
    func,
    duration,
    { silentCancelationErrors = true } = {}
) {
    const throttleObj = new Throttle(env, func, duration);
    const callable = async (...args) => {
        try {
            // await is important, otherwise errors are not intercepted.
            return await throttleObj.do(...args);
        } catch (error) {
            const isSelfReinvokedError = (
                error instanceof ThrottleReinvokedError &&
                error.throttleId === throttleObj.id
            );
            const isSelfCanceledError = (
                error instanceof ThrottleCanceledError &&
                error.throttleId === throttleObj.id
            );

            if (silentCancelationErrors && (isSelfReinvokedError || isSelfCanceledError)) {
                // Silently ignore cancelation errors.
                // Promise is indefinitely pending for async functions.
                return new Promise(() => {});
            } else {
                throw error;
            }
        }
    };
    Object.assign(callable, {
        cancel: () => throttleObj.cancel(),
        clear: () => throttleObj.clear(),
        flush: () => throttleObj.flush(),
    });
    return callable;
}

/**
 * Make external throttle errors accessible from throttle function.
 */
Object.assign(throttle, {
    ThrottleReinvokedError,
    ThrottleCanceledError,
});


return throttle;

});
