import { compensateScrollbar, getScrollingElement } from "@web/core/utils/scrolling";

/**
 * The bootstrap library extensions and fixes should be done here to avoid
 * patching in place.
 */

/**
 * `_queueCallback`/`executeAfterTransition` waits for a CSS transition on an
 * element before running a callback, with a `setTimeout` fallback in case
 * the transition event never fires. That timeout is not cancelled if the
 * element gets removed/replaced in the meantime (e.g. a template re-render
 * discarding it), so the callback can still fire later against an element
 * that is no longer part of the page - and, transitively, against whatever
 * component instance owned it, which may by then be disposed. Skip it in
 * that case: there is nothing left on screen for it to act on.
 */
const bsExecuteAfterTransition = window.Index.executeAfterTransition;
window.Index.executeAfterTransition = function (callback, transitionElement, waitForTransition) {
    return bsExecuteAfterTransition(
        () => {
            if (transitionElement.isConnected) {
                callback();
            }
        },
        transitionElement,
        waitForTransition
    );
};

if (window.Tooltip) {
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
}

if (window.Dropdown) {
    /**
     * Bootstrap disables dynamic dropdown positioning when it is in a navbar. Here
     * we make this patch to activate this dynamic navbar's dropdown positioning
     * which is useful to avoid that the elements of the website sub-menus overflow
     * the page.
     */
    Dropdown.prototype._detectNavbar = function () {
        return false;
    };
}

if (window.Modal) {
    /* Bootstrap modal scrollbar compensation on non-body */
    const bsAdjustDialogFunction = Modal.prototype._adjustDialog;
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
}
