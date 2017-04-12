odoo.define('web.core', function (require) {
"use strict";

var Bus = require('web.Bus');
var Class = require('web.Class');
var QWeb = require('web.QWeb');
var Registry = require('web.Registry');
var translation = require('web.translation');

var debug = $.deparam($.param.querystring()).debug !== undefined;

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
    debug: debug,
    qweb: new QWeb(debug),

    // core classes and functions
    Class: Class,
    bus: bus,
    main_bus: new Bus(),
    _t: translation._t,
    _lt: translation._lt,

    // registries
    action_registry : new Registry(),
    crash_registry: new Registry(),
    form_custom_registry: new Registry(),
    form_tag_registry: new Registry(),
    form_widget_registry: new Registry(),
    list_widget_registry: new Registry(),
    one2many_view_registry: new Registry(),
    search_filters_registry: new Registry(),
    search_widgets_registry: new Registry(),

    csrf_token: odoo.csrf_token,
};

});
