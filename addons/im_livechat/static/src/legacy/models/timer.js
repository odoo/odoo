/** @odoo-module **/

import Class from 'web.Class';

/**
 * This class creates a timer which, when times out, calls a function.
 */
const Timer = Class.extend({

    /**
     * Instantiate a new timer. Note that the timer is not started on
     * initialization (@see start method).
     *
     * @param {Object} params
     * @param {number} params.duration duration of timer before timeout in
     *   milli-seconds.
     * @param {function} params.onTimeout function that is called when the
     *   timer times out.
     */
    init(params) {
        this._duration = params.duration;
        this._timeout = undefined;
        this._timeoutCallback = params.onTimeout;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Clears the countdown of the timer.
     */
    clear() {
        clearTimeout(this._timeout);
    },
    /**
     * Resets the timer, i.e. resets its duration.
     */
    reset() {
        this.clear();
        this.start();
    },
    /**
     * Starts the timer, i.e. after a certain duration, it times out and calls
     * a function back.
     */
    start() {
        this._timeout = setTimeout(this._onTimeout.bind(this), this._duration);
    },

    //--------------------------------------------------------------------------
    // Handler
    //--------------------------------------------------------------------------

    /**
     * Called when the timer times out, calls back a function on timeout.
     *
     * @private
     */
    _onTimeout() {
        this._timeoutCallback();
    },

});

export default Timer;
