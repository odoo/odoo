/** @odoo-module **/

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
let bsSanitizeAllowList = Tooltip.Default.allowList;

bsSanitizeAllowList['*'].push('title', 'style', /^data-[\w-]+/);

bsSanitizeAllowList.header = [];
bsSanitizeAllowList.main = [];
bsSanitizeAllowList.footer = [];

bsSanitizeAllowList.caption = [];
bsSanitizeAllowList.col = ['span'];
bsSanitizeAllowList.colgroup = ['span'];
bsSanitizeAllowList.table = [];
bsSanitizeAllowList.thead = [];
bsSanitizeAllowList.tbody = [];
bsSanitizeAllowList.tfooter = [];
bsSanitizeAllowList.tr = [];
bsSanitizeAllowList.th = ['colspan', 'rowspan'];
bsSanitizeAllowList.td = ['colspan', 'rowspan'];

bsSanitizeAllowList.address = [];
bsSanitizeAllowList.article = [];
bsSanitizeAllowList.aside = [];
bsSanitizeAllowList.blockquote = [];
bsSanitizeAllowList.section = [];

bsSanitizeAllowList.button = ['type'];
bsSanitizeAllowList.del = [];

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
export function makeExtendedSanitizeWhiteList(extensions) {
    let allowList = Object.assign({}, Tooltip.Default.allowList);
    Object.keys(extensions).forEach(key => {
        allowList[key] = (allowList[key] || []).concat(extensions[key]);
    });
    return allowList;
}

/* Bootstrap tooltip defaults overwrite */
Tooltip.Default.placement = 'auto';
Tooltip.Default.fallbackPlacement = ['bottom', 'right', 'left', 'top'];
Tooltip.Default.html = true;
Tooltip.Default.trigger = 'hover';
Tooltip.Default.container = 'body';
Tooltip.Default.boundary = 'window';
Tooltip.Default.delay = { show: 1000, hide: 0 };

const bootstrapShowFunction = Tooltip.prototype.show;
Tooltip.prototype.show = function () {
    // Overwrite bootstrap tooltip method to prevent showing 2 tooltip at the
    // same time
    $('.tooltip').remove();
    const errorsToIgnore = ["Please use show on visible elements"];
    try {
        return bootstrapShowFunction.call(this);
    } catch (error) {
        if (errorsToIgnore.includes(error.message)) {
            return 0;
        }
        throw error;
    }
};

/**
 * Bootstrap disables dynamic dropdown positioning when it is in a navbar. Here
 * we make this patch to activate this dynamic navbar's dropdown positioning
 * which is useful to avoid that the elements of the website sub-menus overflow
 * the page.
 */
Dropdown.prototype._detectNavbar = function () {
    return false;
};

/* Bootstrap modal scrollbar compensation on non-body */
const bsAdjustDialogFunction = Modal.prototype._adjustDialog;
Modal.prototype._adjustDialog = function () {
    const document = this._element.ownerDocument;
    document.body.classList.remove('modal-open');
    const $scrollable = $().getScrollingElement(document);
    if (document.body.contains($scrollable[0])) {
        $scrollable.compensateScrollbar(true);
    }
    document.body.classList.add('modal-open');
    return bsAdjustDialogFunction.apply(this, arguments);
};

const bsResetAdjustmentsFunction = Modal.prototype._resetAdjustments;
Modal.prototype._resetAdjustments = function () {
    const document = this._element.ownerDocument;
    document.body.classList.remove('modal-open');
    const $scrollable = $().getScrollingElement(document);
    if (document.body.contains($scrollable[0])) {
        $scrollable.compensateScrollbar(false);
    }
    return bsResetAdjustmentsFunction.apply(this, arguments);
};
