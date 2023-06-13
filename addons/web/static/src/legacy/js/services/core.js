/** @odoo-module alias=web.core **/

import Bus from "web.Bus";
import config from "web.config";
import Class from "web.Class";
import QWeb from "web.QWeb";
import Registry from "web.Registry";

/**
 * Whether the client is currently in "debug" mode
 *
 * @type Boolean
 */
var bus = new Bus();

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

export default {
    qweb: new QWeb(config.isDebug()),

    // core classes and functions
    Class: Class,
    bus: bus,
    main_bus: new Bus(),

    // registries
    action_registry: new Registry(),
    crash_registry: new Registry(),
    serviceRegistry: new Registry(),
    /**
     * @type {String}
     */
    csrf_token: odoo.csrf_token,
};
