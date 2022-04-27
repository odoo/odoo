/** @odoo-module **/

import Class from 'web.Class';

/**
 * This object models the behaviour of the clearable and cancellable (CC)
 * throttle version of a provided function.
 */
const CCThrottleFunctionObject = Class.extend({

    /**
     * @param {Object} params
     * @param {integer} params.duration duration of the 'cooldown' phase, i.e.
     *   the minimum duration between the most recent function call that has
     *   been made and the following function call.
     * @param {function} params.func provided function for making the CC
     *   throttled version.
     */
    init(params) {
        this._arguments = undefined;
        this._cooldownTimeout = undefined;
        this._duration = params.duration;
        this._func = params.func;
        this._shouldCallFunctionAfterCD = false;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Cancel any buffered function call, but keep the cooldown phase running.
     */
    cancel() {
        this._arguments = undefined;
        this._shouldCallFunctionAfterCD = false;
    },
    /**
     * Clear the internal throttle timer, so that the following function call
     * is immediate. For instance, if there is a cooldown stage, it is aborted.
     */
    clear() {
        if (this._cooldownTimeout) {
            clearTimeout(this._cooldownTimeout);
            this._onCooldownTimeout();
        }
    },
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
     */
    do() {
        this._arguments = Array.prototype.slice.call(arguments);
        if (this._cooldownTimeout === undefined) {
            this._callFunction();
        } else {
            this._shouldCallFunctionAfterCD = true;
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Immediately calls the function with arguments of last buffered function
     * call. It initiates the cooldown stage after this function call.
     *
     * @private
     */
    _callFunction() {
        this._func.apply(null, this._arguments);
        this._cooldown();
    },
    /**
     * Called when the function has been successfully called. The following
     * calls to the function with this object should suffer a "cooldown stage",
     * which prevents the function from being called until this stage has ended.
     *
     * @private
     */
    _cooldown() {
        this.cancel();
        this._cooldownTimeout = setTimeout(
            this._onCooldownTimeout.bind(this),
            this._duration
        );
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the cooldown stage ended from timeout. Calls the function if
     * a function call was buffered.
     *
     * @private
     */
    _onCooldownTimeout() {
        if (this._shouldCallFunctionAfterCD) {
            this._callFunction();
        } else {
            this._cooldownTimeout = undefined;
        }
    },
});

export default CCThrottleFunctionObject;
