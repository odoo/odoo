odoo.define('web.bootstrap.extensions', function () {
'use strict';

/**
 * The bootstrap library extensions and fixes should be done here to avoid
 * patching in place.
 */

/* Bootstrap defaults overwrite */
$.fn.tooltip.Constructor.Default.placement = 'auto';
$.fn.tooltip.Constructor.Default.fallbackPlacement = ['bottom', 'right', 'left', 'top'];
$.fn.tooltip.Constructor.Default.html = true;
$.fn.tooltip.Constructor.Default.trigger = 'hover';
$.fn.tooltip.Constructor.Default.container = 'body';
$.fn.tooltip.Constructor.Default.boundary = 'window';
$.fn.tooltip.Constructor.Default.delay = { show: 1000, hide: 0 };

var bootstrapShowFunction = $.fn.tooltip.Constructor.prototype.show;
$.fn.tooltip.Constructor.prototype.show = function () {
    // Overwrite bootstrap tooltip method to prevent showing 2 tooltip at the
    // same time
    $('.tooltip').remove();

    return bootstrapShowFunction.call(this);
};
});
