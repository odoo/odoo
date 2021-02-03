odoo.define('web_tour.utils', function(require) {
"use strict";

function get_step_key(name) {
    return 'tour_' + name + '_step';
}

function get_running_key() {
    return 'running_tour';
}

function get_running_delay_key() {
    return get_running_key() + "_delay";
}

function get_first_visible_element($elements) {
    for (var i = 0 ; i < $elements.length ; i++) {
        var $i = $elements.eq(i);
        if ($i.is(':visible:hasVisibility')) {
            return $i;
        }
    }
    return $();
}

function do_before_unload(if_unload_callback, if_not_unload_callback, if_not_unload_timeout) {
    if_unload_callback = if_unload_callback || function () {};
    if_not_unload_callback = if_not_unload_callback || if_unload_callback;

    var old_before = window.onbeforeunload;
    var reload_timeout;
    window.onbeforeunload = function () {
        clearTimeout(reload_timeout);
        window.onbeforeunload = old_before;
        if_unload_callback();
        if (old_before) return old_before.apply(this, arguments);
    };
    reload_timeout = _.delay(function () {
        window.onbeforeunload = old_before;
        if_not_unload_callback();
    }, if_not_unload_timeout || 1);
}

function get_jquery_element_from_selector(selector) {
    if (_.isString(selector) && selector.indexOf('iframe') !== -1) {
        var $iframe = $(selector.split('iframe')[0] + ' iframe');
        var $el = $iframe.contents()
            .find(selector.split('iframe')[1]);
        $el.iframeContainer = $iframe[0];
        return $el;
    } else {
        return $(selector);
    }
}


return {

    'get_step_key': get_step_key,
    'get_running_key': get_running_key,
    'get_running_delay_key': get_running_delay_key,
    'get_first_visible_element': get_first_visible_element,
    'do_before_unload': do_before_unload,
    'get_jquery_element_from_selector' : get_jquery_element_from_selector,
};

});

