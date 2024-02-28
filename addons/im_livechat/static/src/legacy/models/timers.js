/** @odoo-module **/

import Timer from '@im_livechat/legacy/models/timer';

import Class from 'web.Class';

/**
 * This class lists several timers that use a same callback and duration.
 */
const Timers = Class.extend({

    /**
     * Instantiate a new list of timers
     *
     * @param {Object} params
     * @param {integer} params.duration duration of the underlying timers from
     *   start to timeout, in milli-seconds.
     * @param {function} params.onTimeout a function to call back for underlying
     *   timers on timeout.
     */
    init(params) {
        this._duration = params.duration;
        this._timeoutCallback = params.onTimeout;
        this._timers = {};
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Register a timer with ID `timerID` to start.
     *
     * - an already registered timer with this ID is reset.
     * - (optional) can provide a list of arguments that is passed to the
     *   function callback when timer times out.
     *
     * @param {Object} params
     * @param {Array} [params.timeoutCallbackArguments]
     * @param {integer} params.timerID
     */
     registerTimer(params) {
        const timerID = params.timerID;
        if (this._timers[timerID]) {
            this._timers[timerID].clear();
        }
        const timerParams = {
            duration: this._duration,
            onTimeout: this._timeoutCallback,
        };
        if ('timeoutCallbackArguments' in params) {
            timerParams.onTimeout = this._timeoutCallback.bind.apply(
                this._timeoutCallback,
                [null, ...params.timeoutCallbackArguments]
            );
        } else {
            timerParams.onTimeout = this._timeoutCallback;
        }
        this._timers[timerID] = new Timer(timerParams);
        this._timers[timerID].start();
    },
    /**
     * Unregister a timer with ID `timerID`. The unregistered timer is aborted
     * and will not time out.
     *
     * @param {Object} params
     * @param {integer} params.timerID
     */
     unregisterTimer(params) {
        const timerID = params.timerID;
        if (this._timers[timerID]) {
            this._timers[timerID].clear();
            delete this._timers[timerID];
        }
    },

});

export default Timers;
