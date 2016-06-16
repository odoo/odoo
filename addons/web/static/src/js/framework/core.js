odoo.define('web.core', function (require) {
"use strict";

var Class = require('web.Class');
var mixins = require('web.mixins');
var Registry = require('web.Registry');
var translation = require('web.translation');

var QWeb = require('web.QWeb');

var debug = $.deparam($.param.querystring()).debug !== undefined;

var _t = translation._t;
var _lt = translation._lt;

/**
 * Event Bus used to bind events scoped in the current instance
 */
var Bus = Class.extend(mixins.EventDispatcherMixin, {
    init: function() {
        mixins.EventDispatcherMixin.init.call(this, parent);
    },
});

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


/**
 * Lazy translation function, only performs the translation when actually
 * printed (e.g. inserted into a template)
 *
 * Useful when defining translatable strings in code evaluated before the
 * translation database is loaded, as class attributes or at the top-level of
 * an OpenERP Web module
 *
 * @param {String} s string to translate
 * @returns {Object} lazy translation object
 */
var qweb = new QWeb(debug);



/** Setup jQuery timeago */
/*
 * Strings in timeago are "composed" with prefixes, words and suffixes. This
 * makes their detection by our translating system impossible. Use all literal
 * strings we're using with a translation mark here so the extractor can do its
 * job.
 */
{
    _t('less than a minute ago');
    _t('about a minute ago');
    _t('%d minutes ago');
    _t('about an hour ago');
    _t('%d hours ago');
    _t('a day ago');
    _t('%d days ago');
    _t('about a month ago');
    _t('%d months ago');
    _t('about a year ago');
    _t('%d years ago');
}

return {
    debug: debug,
    qweb: qweb,

    // core classes and functions
    Class: Class,
    Bus: Bus,
    mixins: mixins,
    bus: bus,
    main_bus: new Bus(),
    _t: _t,
    _lt: _lt,

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
    view_registry: new Registry(),

    csrf_token: odoo.csrf_token,
};

});
