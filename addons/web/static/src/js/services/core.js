odoo.define('web.core', function (require) {
"use strict";

var Bus = require('web.Bus');
var Class = require('web.Class');
var config = require('web.config');
var QWeb = require('web.QWeb');
var Registry = require('web.Registry');
var translation = require('web.translation');

/**
 * Whether the client is currently in "debug" mode
 *
 * @type Boolean
 */
var bus = new Bus ();

_.each('click,dblclick,keydown,keypress,keyup'.split(','), function(evtype) {
    $('html').on(evtype, function(ev) {
        bus.trigger(evtype, ev);
    });
});
_.each('resize,scroll'.split(','), function(evtype) {
    $(window).on(evtype, function(ev) {
        bus.trigger(evtype, ev);
    });
});

return {
    qweb: new QWeb(config.debug),

    // core classes and functions
    Class: Class,
    bus: bus,
    main_bus: new Bus(),
    _t: translation._t,
    _lt: translation._lt,

    // registries
    action_registry : new Registry(),
    crash_registry: new Registry(),
    search_filters_registry: new Registry(),
    search_widgets_registry: new Registry(),
    /**
     * @type {String}
     */
    csrf_token: odoo.csrf_token,
};

});
