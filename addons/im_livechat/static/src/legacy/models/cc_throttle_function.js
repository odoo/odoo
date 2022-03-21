odoo.define('im_livechat.legacy.mail.model.CCThrottleFunction', function (require) {
"use strict";

var CCThrottleFunctionObject = require('im_livechat.legacy.mail.model.CCThrottleFunctionObject');

/**
 * A function that creates a cancellable and clearable (CC) throttle version
 * of a provided function.
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
 * This throttle version has the following interesting properties:
 *
 * - cancellable: it allows removing a buffered function call during the
 *     cooldown phase, but it keeps the cooldown phase running.
 * - clearable: it allows to clear the internal clock of the throttled function,
 *     so that any cooldown phase is immediately ending.
 *
 * @param {Object} params
 * @param {integer} params.duration a duration for the throttled behaviour,
 *   in milli-seconds.
 * @param {function} params.func the function to throttle
 * @returns {function} the cancellable and clearable throttle version of the
 *   provided function in argument.
 */
var CCThrottleFunction = function (params) {
    var duration = params.duration;
    var func = params.func;

    var throttleFunctionObject = new CCThrottleFunctionObject({
        duration: duration,
        func: func,
    });

    var callable = function () {
        return throttleFunctionObject.do.apply(throttleFunctionObject, arguments);
    };
    callable.cancel = function () {
        throttleFunctionObject.cancel();
    };
    callable.clear = function () {
        throttleFunctionObject.clear();
    };

    return callable;
};

return CCThrottleFunction;

});
