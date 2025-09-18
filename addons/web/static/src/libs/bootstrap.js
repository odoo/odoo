// @ts-check

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

import {
    compensateScrollbar,
    getScrollingElement,
} from "@web/core/utils/dom/scrolling";
const bsSanitizeAllowList = Tooltip.Default.allowList;

bsSanitizeAllowList["*"].push("title", "style", /^data-[\w-]+/);

bsSanitizeAllowList.header = [];
bsSanitizeAllowList.main = [];
bsSanitizeAllowList.footer = [];

bsSanitizeAllowList.caption = [];
bsSanitizeAllowList.col = ["span"];
bsSanitizeAllowList.colgroup = ["span"];
bsSanitizeAllowList.table = [];
bsSanitizeAllowList.thead = [];
bsSanitizeAllowList.tbody = [];
bsSanitizeAllowList.tfooter = [];
bsSanitizeAllowList.tr = [];
bsSanitizeAllowList.th = ["colspan", "rowspan"];
bsSanitizeAllowList.td = ["colspan", "rowspan"];

bsSanitizeAllowList.address = [];
bsSanitizeAllowList.article = [];
bsSanitizeAllowList.aside = [];
bsSanitizeAllowList.blockquote = [];
bsSanitizeAllowList.section = [];

bsSanitizeAllowList.button = ["type"];
bsSanitizeAllowList.del = [];

/* Bootstrap tooltip defaults overwrite */
Tooltip.Default.placement = "auto";
Tooltip.Default.fallbackPlacement = ["bottom", "right", "left", "top"];
Tooltip.Default.html = true;
Tooltip.Default.trigger = "hover";
Tooltip.Default.container = "body";
Tooltip.Default.boundary = "window";
Tooltip.Default.delay = { show: 1000, hide: 0 };

const bootstrapShowFunction = Tooltip.prototype.show;
/**
 * Patched Tooltip.show: removes any existing tooltips before showing a new one
 * to prevent duplicates. Silently ignores "show on visible elements" errors.
 * @returns {*} The original show() return value, or 0 if suppressed.
 */
Tooltip.prototype.show = function () {
    // Overwrite bootstrap tooltip method to prevent showing 2 tooltip at the
    // same time
    document.querySelectorAll(".tooltip").forEach((el) => el.remove());
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
 * Patched _detectNavbar: always returns false so Bootstrap enables dynamic
 * dropdown positioning, preventing website sub-menu overflow.
 * @returns {false}
 */
Dropdown.prototype._detectNavbar = function () {
    return false;
};

/* Bootstrap modal scrollbar compensation on non-body */
const bsAdjustDialogFunction = Modal.prototype._adjustDialog;
/**
 * Patched _adjustDialog: compensates scrollbar on the actual scrolling element
 * (not just document.body) before delegating to the original Bootstrap logic.
 * @returns {*} The original _adjustDialog() return value.
 */
Modal.prototype._adjustDialog = function () {
    const document = this._element.ownerDocument;

    this._scrollBar.reset();
    document.body.classList.remove("modal-open");

    const scrollable = getScrollingElement(document);
    if (document.body.contains(scrollable)) {
        compensateScrollbar(scrollable, true);
    }

    this._scrollBar.hide();
    document.body.classList.add("modal-open");

    return bsAdjustDialogFunction.apply(this, arguments);
};

const bsResetAdjustmentsFunction = Modal.prototype._resetAdjustments;
/**
 * Patched _resetAdjustments: removes scrollbar compensation from the actual
 * scrolling element before delegating to the original Bootstrap logic.
 * @returns {*} The original _resetAdjustments() return value.
 */
Modal.prototype._resetAdjustments = function () {
    const document = this._element.ownerDocument;

    this._scrollBar.reset();
    document.body.classList.remove("modal-open");

    const scrollable = getScrollingElement(document);
    if (document.body.contains(scrollable)) {
        compensateScrollbar(scrollable, false);
    }
    return bsResetAdjustmentsFunction.apply(this, arguments);
};
