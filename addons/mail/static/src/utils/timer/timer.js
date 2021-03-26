/** @odoo-module **/

import { makeDeferred } from '@mail/utils/deferred/deferred';

//------------------------------------------------------------------------------
// Errors
//------------------------------------------------------------------------------

/**
 * List of Timer errors.
 */

 /**
  * Error when timer has been cleared with `.clear()` or `.reset()`. Used to
  * let know caller of timer that the countdown has been aborted, which
  * means the inner function will not be called. Usually caller should just
  * accept it and kindly treated this error as a polite warning.
  */
 class TimerClearedError extends Error {
    /**
     * @override
     */
    constructor(timerId, ...args) {
        super(...args);
        this.name = 'TimerClearedError';
        this.timerId = timerId;
    }
}

//------------------------------------------------------------------------------
// Private
//------------------------------------------------------------------------------

/**
 * This class creates a timer which, when times out, calls a function.
 * Note that the timer is not started on initialization (@see start method).
 */
class Timer {

    /**
     * @param {Object} env the OWL env
     * @param {function} onTimeout
     * @param {integer} duration
     * @param {Object} [param3={}]
     * @param {boolean} [param3.silentCancelationErrors=true] if unset, caller
     *   of timer will observe some errors that come from current timer calls
     *   that has been cleared with `.clear()` or `.reset()`.
     *   @see TimerClearedError for when timer has been aborted from `.clear()`
     *     or `.reset()`.
     */
    constructor(env, onTimeout, duration, { silentCancelationErrors = true } = {}) {
        this.env = env;
        /**
         * Determine whether the timer has a pending timeout.
         */
        this.isRunning = false;
        /**
         * Duration, in milliseconds, until timer times out and calls the
         * timeout function.
         */
        this._duration = duration;
        /**
         * Determine whether the caller of timer `.start()` and `.reset()`
         * should observe cancelation errors from `.clear()` or `.reset()`.
         */
        this._hasSilentCancelationErrors = silentCancelationErrors;
        /**
         * The function that is called when the timer times out.
         */
        this._onTimeout = onTimeout;
        /**
         * Deferred of a currently pending invocation to inner function on
         * timeout.
         */
        this._timeoutDeferred = undefined;
        /**
         * Internal reference of `setTimeout()` that is used to invoke function
         * when timer times out. Useful to clear it when timer is cleared/reset.
         */
        this._timeoutId = undefined;
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Clear the timer, which basically sets the state of timer as if it was
     * just instantiated, without being started. This function makes sense only
     * when this timer is running.
     */
    clear() {
        this.env.browser.clearTimeout(this._timeoutId);
        this.isRunning = false;
        if (!this._timeoutDeferred) {
            return;
        }
        this._timeoutDeferred.reject(new TimerClearedError(this.id));
    }

    /**
     * Reset the timer, i.e. the pending timeout is refreshed with initial
     * duration. This function makes sense only when this timer is running.
     */
    async reset() {
        this.clear();
        await this.start();
    }

    /**
     * Starts the timer, i.e. after a certain duration, it times out and calls
     * a function back. This function makes sense only when this timer is not
     * yet running.
     *
     * @throws {Error} in case the timer is already running.
     */
    async start() {
        if (this.isRunning) {
            throw new Error("Cannot start a timer that is currently running.");
        }
        this.isRunning = true;
        const timeoutDeferred = makeDeferred();
        this._timeoutDeferred = timeoutDeferred;
        const timeoutId = this.env.browser.setTimeout(
            () => {
                this.isRunning = false;
                timeoutDeferred.resolve(this._onTimeout());
            },
            this._duration
        );
        this._timeoutId = timeoutId;
        let result;
        try {
            result = await timeoutDeferred;
        } catch (error) {
            if (
                !this._hasSilentCancelationErrors ||
                !(error instanceof TimerClearedError) ||
                error.timerId !== this.id
            ) {
                // This branching should never happens.
                // Still defined in case of programming error.
                throw error;
            }
        } finally {
            this.env.browser.clearTimeout(timeoutId);
            this._timeoutDeferred = undefined;
            this.isRunning = false;
        }
        return result;
    }

}

/**
 * Make external timer errors accessible from timer class.
 */
Object.assign(Timer, {
    TimerClearedError,
});

export default Timer;
