/** @odoo-module **/

import Bus from "@web/legacy/js/core/bus";
import Class from "@web/legacy/js/core/class";
import translation from "@web/legacy/js/core/translation";

/**
 * Whether the client is currently in "debug" mode
 *
 * @type Boolean
 */
export var bus = new Bus();

["click","dblclick","keydown","keypress","keyup"].forEach((evtype) => {
    $('html').on(evtype, function (ev) {
        bus.trigger(evtype, ev);
    });
});
["resize", "scroll"].forEach((evtype) => {
    $(window).on(evtype, function (ev) {
        bus.trigger(evtype, ev);
    });
});

export const _t = translation._t;
export const _lt = translation._lt;
export const csrf_token = odoo.csrf_token;

export default {
    // core classes and functions
    Class: Class,
    bus: bus,
    _t: _t,
    _lt: _lt,
    /**
     * @type {String}
     */
    csrf_token: csrf_token,
};
