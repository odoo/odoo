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

/**
 * Will hide accesskey overlays from all elements.
 */
function hide_accesskey_overlay () {
    var accesskeyElements = $(document).find('[accesskey]').filter(':visible');
    var overlays = accesskeyElements.find('.accesskey_overlay');
    if (overlays.length) {
        return overlays.remove();
    }
};

/**
 * will show overlay for accesskey
 * wherever we have accesskey on any tag, pressing ALT+? will show that accesskey as overlay on that element.
 */
$(document).on('keyup', function (e) {
    if (e.which == 191 && e.altKey) {
        var accesskeyElements = $(document).find('[accesskey]').filter(':visible');
        var overlays = accesskeyElements.find('.accesskey_overlay');
        if (overlays.length) {
            return overlays.remove();
        }
        _.each(accesskeyElements, function (elem) {
            $(_.str.sprintf("<div class='accesskey_overlay'>%s</div>", $(elem).attr('accesskey').toUpperCase())).css({
                position: 'absolute',
                width: '100%',
                height: '100%',
                left: 0,
                top: 0,
                zIndex: 1000000,  // to be on the safe side
                'background-color': 'rgba(0,0,0,.7)',
                'color': '#FFFFFF',
                'justify-content': 'center',
                'display': 'flex',
                'align-items': 'center',
            }).appendTo($(elem).css('position', 'relative'));
        });
    } else if (e.which != 18) {
        hide_accesskey_overlay();
    }
});
$(document).on('click', function () {
    hide_accesskey_overlay();
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
