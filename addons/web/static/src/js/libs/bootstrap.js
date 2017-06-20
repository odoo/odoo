odoo.define('web.bootstrap.extensions', function () {
'use strict';

/**
 * The bootstrap library extensions and fixes should be done here to avoid
 * patching in place.
 */

/* Bootstrap defaults overwrite */
$.fn.tooltip.Constructor.DEFAULTS.placement = 'auto top';
$.fn.tooltip.Constructor.DEFAULTS.html = true;
$.fn.tooltip.Constructor.DEFAULTS.trigger = 'hover focus click';
$.fn.tooltip.Constructor.DEFAULTS.container = 'body';
$.fn.tooltip.Constructor.DEFAULTS.delay = { show: 1000, hide: 0 };
//overwrite bootstrap tooltip method to prevent showing 2 tooltip at the same time
var bootstrap_show_function = $.fn.tooltip.Constructor.prototype.show;
$.fn.modal.Constructor.prototype.enforceFocus = function () { };
$.fn.tooltip.Constructor.prototype.show = function () {
    $('.tooltip').remove();
    //the following fix the bug when using placement
    //auto and the parent element does not exist anymore resulting in
    //an error. This should be remove once we updade bootstrap to a version that fix the bug
    //edit: bug has been fixed here : https://github.com/twbs/bootstrap/pull/13752
    var e = $.Event('show.bs.' + this.type);
    var inDom = $.contains(document.documentElement, this.$element[0]);
    if (e.isDefaultPrevented() || !inDom) return;
    return bootstrap_show_function.call(this);
};
});
