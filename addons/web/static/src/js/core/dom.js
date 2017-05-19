odoo.define('web.dom', function (require) {
"use strict";

/**
 * DOM Utility helpers
 *
 * We collect in this file some helpers to help integrate various DOM
 * functionalities with the odoo framework.  A common theme in these functions
 * is the use of the main core.bus, which helps the framework react when
 * something happens in the DOM.
 */

var core = require('web.core');

/**
 * Private function to notify that something has been attached in the DOM
 * @param {htmlString or Element or Array or jQuery} [content] the content that
 * has been attached in the DOM
 * @params {Array} [callbacks] array of {widget: w, callback_args: args} such
 * that on_attach_callback() will be called on each w with arguments args
 */
function _notify (content, callbacks) {
    _.each(callbacks, function(c) {
        if (c.widget && c.widget.on_attach_callback) {
            c.widget.on_attach_callback(c.callback_args);
        }
    });
    core.bus.trigger('DOM_updated', content);
}

return {
    /**
     * Appends content in a jQuery object and optionnally triggers an event
     *
     * @param {jQuery} [$target] the node where content will be appended
     * @param {htmlString or Element or Array or jQuery} [content] DOM element,
     *   array of elements, HTML string or jQuery object to append to $target
     * @param {Boolean} [options.in_DOM] true if $target is in the DOM
     * @param {Array} [options.callbacks] array of objects describing the
     *   callbacks to perform (see _notify for a complete description)
     */
    append: function ($target, content, options) {
        $target.append(content);
        if (options && options.in_DOM) {
            _notify(content, options.callbacks);
        }
    },
    /**
     * Autoresize a $textarea node, by recomputing its height when necessary
     * @param {number} [options.min_height] by default, 50.
     * @param {Widget} [options.parent] if set, autoresize will listen to some
     *   extra events to decide when to resize itself.  This is useful for
     *   widgets that are not in the dom when the autoresize is declared.
     */
    autoresize: function ($textarea, options) {
        if ($textarea.data("auto_resize")) {
            return;
        }

        var $fixedTextarea;
        var minHeight;

        function resize() {
            $fixedTextarea.insertAfter($textarea);
            var heightOffset;
            var style = window.getComputedStyle($textarea[0], null);
            if (style.boxSizing === 'content-box') {
                heightOffset = -(parseFloat(style.paddingTop) + parseFloat(style.paddingBottom));
            } else {
                heightOffset = parseFloat(style.borderTopWidth) + parseFloat(style.borderBottomWidth);
            }
            $fixedTextarea.width($textarea.width());
            $fixedTextarea.val($textarea.val());
            var height = $fixedTextarea[0].scrollHeight;
            $textarea.css({height: Math.max(height + heightOffset, minHeight)});
        }

        options = options || {};
        minHeight = (options && options.min_height) || 50;

        $fixedTextarea = $('<textarea disabled>', {
            class: $textarea[0].className,
        }).css({
            position: 'absolute',
            opacity: 0,
            height: 10,
            top: -10000,
            left: -10000,
        });
        $fixedTextarea.data("auto_resize", true);

        var style = window.getComputedStyle($textarea[0], null);
        if (style.resize === 'vertical') {
            $textarea[0].style.resize = 'none';
        } else if (style.resize === 'both') {
            $textarea[0].style.resize = 'horizontal';
        }
        resize();
        $textarea.data("auto_resize", true);

        $textarea.on('input focus', resize);
        if (options.parent) {
            core.bus.on('DOM_updated', options.parent, resize);
            core.bus.on('view_shown', options.parent, resize);
        }
    },
    /**
     * Detaches widgets from the DOM and performs their on_detach_callback()
     *
     * @param {Array} [to_detach] array of {widget: w, callback_args: args} such
     *   that w.$el will be detached and w.on_detach_callback(args) will be
     *   called
     * @param {jQuery} [options.$to_detach] if given, detached instead of
     *   widgets' $el
     * @return {jQuery} the detached elements
     */
    detach: function (to_detach, options) {
        _.each(to_detach, function(d) {
            if (d.widget.on_detach_callback) {
                d.widget.on_detach_callback(d.callback_args);
            }
        });
        var $to_detach = options && options.$to_detach;
        if (!$to_detach) {
            $to_detach = $(_.map(to_detach, function(d) {
                return d.widget.el;
            }));
        }
        return $to_detach.detach();
    },
    /**
     * Returns the distance between a DOM element and the top-left corner of the
     * window
     *
     * @param {element} [e] the DOM element
     * @return {Object} the left and top distances in pixels
     */
    getPosition: function (e) {
        var position = {left: 0, top: 0};
        while (e) {
            position.left += e.offsetLeft;
            position.top += e.offsetTop;
            e = e.offsetParent;
        }
        return position;
    },
    /**
     * Prepends content in a jQuery object and optionnally triggers an event
     *
     * @param {jQuery} [$target] the node where content will be prepended
     * @param {htmlString or Element or Array or jQuery} [content] DOM element,
     *   array of elements, HTML string or jQuery object to prepend to $target
     * @param {Boolean} [options.in_DOM] true if $target is in the DOM
     * @param {Array} [options.callbacks] array of objects describing the
     *   callbacks to perform (see _notify for a complete description)
     */
    prepend: function ($target, content, options) {
        $target.prepend(content);
        if (options && options.in_DOM) {
            _notify(content, options.callbacks);
        }
    },
};

});
