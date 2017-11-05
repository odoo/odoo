odoo.define('web.nvd3.extensions', function () {
'use strict';

/**
 * The nvd3 library extensions and fixes should be done here to avoid patching
 * in place.
 */

nv.dev = false;  // sets nvd3 library in production mode

// monkey patch nvd3 to allow removing eventhandler on windowresize events
// see https://github.com/novus/nvd3/pull/396 for more details

// Adds a resize listener to the window.
nv.utils.onWindowResize = function (fun) {
    if (fun === null) return;
    window.addEventListener('resize', fun);
};

// Backwards compatibility with current API.
nv.utils.windowResize = nv.utils.onWindowResize;

// Removes a resize listener from the window.
nv.utils.offWindowResize = function (fun) {
    if (fun === null) return;
    window.removeEventListener('resize', fun);
};

// monkey patch nvd3 to prevent crashes when user changes view and nvd3
// tries to remove tooltips after 500 ms...  seriously nvd3, what were you
// thinking?
nv.tooltip.cleanup = function () {
    $('.nvtooltip').remove();
};

// monkey patch nvd3 to prevent it to display a tooltip (position: absolute)
// with a negative `top`; with this patch the highest tooltip's position is
// still in the graph
var originalCalcTooltipPosition = nv.tooltip.calcTooltipPosition;
nv.tooltip.calcTooltipPosition = function () {
    var container = originalCalcTooltipPosition.apply(this, arguments);
    container.style.top = container.style.top.split('px')[0] < 0 ? 0 + 'px' : container.style.top;
    return container;
};
});
