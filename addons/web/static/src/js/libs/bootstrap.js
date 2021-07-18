odoo.define('web.bootstrap.extensions', function () {
'use strict';

/**
 * The bootstrap library extensions and fixes should be done here to avoid
 * patching in place.
 */

/**
 * Review Bootstrap Sanitization: leave it enabled by default but extend it to
 * accept more common tag names like tables and buttons, and common attributes
 * such as style or data-. If a specific tooltip or popover must accept custom
 * tags or attributes, they must be supplied through the whitelist BS
 * parameter explicitely.
 *
 * We cannot disable sanitization because bootstrap uses tooltip/popover
 * DOM attributes in an "unsafe" way.
 */
var bsSanitizeWhiteList = $.fn.tooltip.Constructor.Default.whiteList;

bsSanitizeWhiteList['*'].push('title', 'style', /^data-[\w-]+/);

bsSanitizeWhiteList.header = [];
bsSanitizeWhiteList.main = [];
bsSanitizeWhiteList.footer = [];

bsSanitizeWhiteList.caption = [];
bsSanitizeWhiteList.col = ['span'];
bsSanitizeWhiteList.colgroup = ['span'];
bsSanitizeWhiteList.table = [];
bsSanitizeWhiteList.thead = [];
bsSanitizeWhiteList.tbody = [];
bsSanitizeWhiteList.tfooter = [];
bsSanitizeWhiteList.tr = [];
bsSanitizeWhiteList.th = ['colspan', 'rowspan'];
bsSanitizeWhiteList.td = ['colspan', 'rowspan'];

bsSanitizeWhiteList.address = [];
bsSanitizeWhiteList.article = [];
bsSanitizeWhiteList.aside = [];
bsSanitizeWhiteList.blockquote = [];
bsSanitizeWhiteList.section = [];

bsSanitizeWhiteList.button = ['type'];
bsSanitizeWhiteList.del = [];

/**
 * Returns an extended version of bootstrap default whitelist for sanitization,
 * i.e. a version where, for each key, the original value is concatened with the
 * received version's value and where the received version's extra key/values
 * are added.
 *
 * Note: the returned version
 *
 * @param {Object} extensions
 * @returns {Object} /!\ the returned whitelist is made from a *shallow* copy of
 *      the default whitelist, extended with given whitelist.
 */
function makeExtendedSanitizeWhiteList(extensions) {
    var whiteList = _.clone($.fn.tooltip.Constructor.Default.whiteList);
    Object.keys(extensions).forEach(key => {
        whiteList[key] = (whiteList[key] || []).concat(extensions[key]);
    });
    return whiteList;
}

/* Bootstrap tooltip defaults overwrite */
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

/* Bootstrap scrollspy fix for non-body to spy */

const bootstrapSpyRefreshFunction = $.fn.scrollspy.Constructor.prototype.refresh;
$.fn.scrollspy.Constructor.prototype.refresh = function () {
    bootstrapSpyRefreshFunction.apply(this, arguments);
    if (this._scrollElement === window || this._config.method !== 'offset') {
        return;
    }
    const baseScrollTop = this._getScrollTop();
    for (let i = 0; i < this._offsets.length; i++) {
        this._offsets[i] += baseScrollTop;
    }
};

/**
 * In some cases, we need to keep the first element of navbars selected.
 */
const bootstrapSpyProcessFunction = $.fn.scrollspy.Constructor.prototype._process;
$.fn.scrollspy.Constructor.prototype._process = function () {
    bootstrapSpyProcessFunction.apply(this, arguments);
    if (this._activeTarget === null && this._config.alwaysKeepFirstActive) {
        this._activate(this._targets[0]);
    }
};

/* Bootstrap modal scrollbar compensation on non-body */
const bsSetScrollbarFunction = $.fn.modal.Constructor.prototype._setScrollbar;
$.fn.modal.Constructor.prototype._setScrollbar = function () {
    const $scrollable = $().getScrollingElement();
    if (document.body.contains($scrollable[0])) {
        $scrollable.compensateScrollbar(true);
    }
    return bsSetScrollbarFunction.apply(this, arguments);
};
const bsResetScrollbarFunction = $.fn.modal.Constructor.prototype._resetScrollbar;
$.fn.modal.Constructor.prototype._resetScrollbar = function () {
    const $scrollable = $().getScrollingElement();
    if (document.body.contains($scrollable[0])) {
        $scrollable.compensateScrollbar(false);
    }
    return bsResetScrollbarFunction.apply(this, arguments);
};

return {
    makeExtendedSanitizeWhiteList: makeExtendedSanitizeWhiteList,
};
});
