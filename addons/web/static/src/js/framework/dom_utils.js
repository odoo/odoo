odoo.define('web.dom_utils', function (require) {
"use strict";

var core = require('web.core');

/**
 * Autoresize a $textarea node, by recomputing its height when necessary
 * @param {number} [options.min_height] by default, 50.
 * @param {Widget} [options.parent] if set, autoresize will listen to some extra
 * events to decide when to resize itself.  This is useful for widgets that are
 * not in the dom when the autoresize is declared.
 */
function autoresize ($textarea, options) {
    if ($textarea.data("auto_resize")) {
        return;
    }
    options = options || {};

    var $fixed_text_area;
    var min_height = (options && options.min_height) || 50;
    if (!$fixed_text_area) {
        $fixed_text_area = $('<textarea disabled>').css({
            position: 'absolute',
            opacity: 0,
            height: 10,
            top: -10000,
            left: -10000,
        });
        $fixed_text_area.addClass($textarea[0].className);
        $fixed_text_area.insertAfter($textarea);
        $fixed_text_area.data("auto_resize", true);
    }

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

    function resize () {
        var heightOffset;
        var style = window.getComputedStyle($textarea[0], null);
        if (style.boxSizing === 'content-box') {
            heightOffset = -(parseFloat(style.paddingTop) + parseFloat(style.paddingBottom));
        } else {
            heightOffset = parseFloat(style.borderTopWidth) + parseFloat(style.borderBottomWidth);
        }
        $fixed_text_area.width($textarea.width());
        $fixed_text_area.val($textarea.val());
        var height = $fixed_text_area[0].scrollHeight;
        $textarea.css({height: Math.max(height + heightOffset, min_height)});
    }
}

return {
    autoresize: autoresize,
};

});
