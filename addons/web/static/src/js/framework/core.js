odoo.define('web.core', function (require) {
"use strict";

var Class = require('web.Class');
var mixins = require('web.mixins');
var Registry = require('web.Registry');
var translation = require('web.translation');

var qweb = require('qweb');
var _ = require('_');
var $ = require('$');

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

var main_bus = new Bus ();

_.each('click,dblclick,keydown,keypress,keyup'.split(','), function(evtype) {
    $('html').on(evtype, function(ev) {
        main_bus.trigger(evtype, ev);
    });
});
_.each('resize,scroll'.split(','), function(evtype) {
    $(window).on(evtype, function(ev) {
        main_bus.trigger(evtype, ev);
    });
});


// Underscore customization
//-------------------------------------------------------------------------
_.str.toBoolElse = function (str, elseValues, trueValues, falseValues) {
    var ret = _.str.toBool(str, trueValues, falseValues);
    if (_.isUndefined(ret)) {
        return elseValues;
    }
    return ret;
};

// IE patch
//-------------------------------------------------------------------------
if (typeof(console) === "undefined") {
    // Even IE9 only exposes console object if debug window opened
    window.console = {};
    ('log error debug info warn assert clear dir dirxml trace group'
        + ' groupCollapsed groupEnd time timeEnd profile profileEnd count'
        + ' exception').split(/\s+/).forEach(function(property) {
            console[property] = _.identity;
    });
}

/**
    Some hack to make placeholders work in ie9.
*/
if (!('placeholder' in document.createElement('input'))) {    
    document.addEventListener("DOMNodeInserted",function(event){
        var nodename =  event.target.nodeName.toLowerCase();
        if ( nodename === "input" || nodename == "textarea" ) {
            $(event.target).placeholder();
        }
    });
}



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
qweb.debug = debug;
_.extend(qweb.default_dict, {
    '__debug__': debug,
    'moment': function(date) { return new moment(date); },
});

qweb.preprocess_node = function() {
    // Note that 'this' is the Qweb Node
    switch (this.node.nodeType) {
        case Node.TEXT_NODE:
        case Node.CDATA_SECTION_NODE:
            // Text and CDATAs
            var translation = this.node.parentNode.attributes['t-translation'];
            if (translation && translation.value === 'off') {
                return;
            }
            var match = /^(\s*)([\s\S]+?)(\s*)$/.exec(this.node.data);
            if (match) {
                this.node.data = match[1] + _t(match[2]) + match[3];
            }
            break;
        case Node.ELEMENT_NODE:
            // Element
            var attr, attrs = ['label', 'title', 'alt', 'placeholder'];
            while ((attr = attrs.pop())) {
                if (this.attributes[attr]) {
                    this.attributes[attr] = _t(this.attributes[attr]);
                }
            }
    }
};

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

$.async_when = function() {
    var async = false;
    var def = $.Deferred();
    $.when.apply($, arguments).done(function() {
        var args = arguments;
        var action = function() {
            def.resolve.apply(def, args);
        };
        if (async)
            action();
        else
            setTimeout(action, 0);
    }).fail(function() {
        var args = arguments;
        var action = function() {
            def.reject.apply(def, args);
        };
        if (async)
            action();
        else
            setTimeout(action, 0);
    });
    async = true;
    return def;
};

return {
    debug: debug,
    qweb: qweb,

    // core classes and functions
    Class: Class,
    Bus: Bus,
    mixins: mixins,
    bus: main_bus,
    _t: _t,
    _lt: _lt,

    // registries
    view_registry: new Registry(),
    crash_registry: new Registry(),
    action_registry : new Registry(),
    form_widget_registry: new Registry(),
    form_tag_registry: new Registry(),
    form_custom_registry: new Registry(),
    list_widget_registry: new Registry(),
    search_widgets_registry: new Registry(),
    search_filters_registry: new Registry(),

    // necessary to make the kanban view compatible between 
    // community and enterprise edition
    one2many_view_registry: new Registry(),

};


});
