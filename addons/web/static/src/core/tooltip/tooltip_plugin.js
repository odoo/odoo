import { registry } from "@web/core/registry";
import { services } from "@web/core/services";
import { Tooltip } from "./tooltip";
import { hasTouch } from "@web/core/browser/feature_detection";
import { PopoverPlugin } from "@web/core/popover/popover_plugin";

import { effect, onWillDestroy, Plugin, signal, useListener, usePlugin } from "@odoo/owl";
import { generateHTMLId } from "../utils/strings";

/**
 * The tooltip service allows to display custom tooltips on every elements with
 * a "data-tooltip" attribute. This attribute can be set on elements for which
 * we prefer a custom tooltip instead of the native one displaying the value of
 * the "title" attribute.
 *
 * Usage:
 *   <button data-tooltip="This is a tooltip">Do something</button>
 *
 * The tooltip isn't displayed if it would only repeat what the user can already
 * read, i.e. if its content is exactly the text content of the element, and if
 * that text is entirely displayed (not truncated by an overflow).
 *
 * The ideal position of the tooltip can be specified thanks to the attribute
 * "data-tooltip-position":
 *   <button data-tooltip="This is a tooltip" data-tooltip-position="left">Do something</button>
 *
 * The opening delay can be modified with the "data-tooltip-delay" attribute (default: 400):
 *   <button data-tooltip="This is a tooltip" data-tooltip-delay="0">Do something</button>
 *
 * The default behaviour on touch devices to open the tooltip can be modified from "hold-to-show"
 * to "tap-to-show" "with the data-tooltip-touch-tap-to-show" attribute:
 *  <button data-tooltip="This is a tooltip" data-tooltip-touch-tap-to-show="true">Do something</button>
 *
 * For advanced tooltips containing dynamic and/or html content, the
 * "data-tooltip-template" and "data-tooltip-info" attributes can be used.
 * For example, let's suppose the following qweb template:
 *   <t t-name="some_template">
 *     <ul>
 *       <li>info.x</li>
 *       <li>info.y</li>
 *     </ul>
 *   </t>
 * This template can then be used in a tooltip as follows:
 *   <button data-tooltip-template="some_template" data-tooltip-info="info">Do something</button>
 * with "info" being a stringified object with two keys "x" and "y".
 */

export const OPEN_DELAY = 400;
export const CLOSE_DELAY = 200;
export const SHOW_AFTER_DELAY = 250;
const TOOLTIP_SELECTOR = "[data-tooltip], [data-tooltip-template]";
const TOOLTIP_SELECTOR_WITH_TITLE = TOOLTIP_SELECTOR + ", [title]";

export class TooltipPlugin extends Plugin {
    /** @private */
    popover = usePlugin(PopoverPlugin);
    /** @private */
    openTooltipTimeout = null;
    /** @private */
    closeTooltip = null;
    /** @private */
    showTimer = null;
    /** @private */
    target = null;
    /** @private */
    interval = null;

    setup() {
        this.interval = window.setInterval(() => {
            if (this.shouldCleanup()) {
                this.cleanup();
            }
        }, CLOSE_DELAY);

        if (hasTouch()) {
            const onTouchCancelEnd = this.onTouchCancelEnd.bind(this);
            useListener(document.body, "touchstart", this.onTouchStart.bind(this));
            useListener(document.body, "touchend", onTouchCancelEnd);
            useListener(document.body, "touchcancel", onTouchCancelEnd);
        }

        // Listen (using event delegation) to "mouseenter" events to open the tooltip if any
        useListener(document.body, "mouseenter", this.onMouseenterOrFocusin.bind(this), {
            capture: true,
        });
        // Listen (using event delegation) to "focusin" events to open the tooltip if any
        useListener(document.body, "focusin", this.onMouseenterOrFocusin.bind(this), {
            capture: true,
        });
        // Listen (using event delegation) to "mouseleave" events to close the tooltip if any
        useListener(document.body, "mouseleave", this.cleanupTooltip.bind(this), {
            capture: true,
        });
        // Listen (using event delegation) to "focusout" events to close the tooltip if any
        useListener(document.body, "focusout", this.onFocusout.bind(this), { capture: true });
        useListener(document.body, "click", this.onClick.bind(this), { capture: true });

        onWillDestroy(() => {
            window.clearInterval(this.interval);
        });
    }

    /**
     * Detect if the current node is the `sup` tooltip node
     * @param {HTMLElement} el
     * @return {boolean}
     * @private
     */
    isHelpNode(el) {
        return (
            el.textContent === "?" &&
            (el.hasAttribute("data-tooltip") || el.hasAttribute("data-tooltip-template"))
        );
    }

    /**
     * Detect if the content of the element is truncated by an overflow.
     * Note that elements that can't be measured (e.g. non blockified inline
     * elements, whose clientWidth is 0) can't truncate their own content.
     *
     * @param {HTMLElement} el
     * @return {boolean}
     * @private
     */
    isOverflowing(el) {
        return (
            el.clientWidth > 0 &&
            (el.scrollWidth > el.clientWidth || el.scrollHeight > el.clientHeight)
        );
    }

    /**
     * Detect if the element is (partially) clipped by one of its ancestors.
     * Such an element doesn't overflow itself, but is visually cut anyway
     * (e.g. an inline element inside a ".text-truncate" container, or a
     * "flex-shrink-0" element inside a narrower one).
     *
     * @param {HTMLElement} el
     * @return {boolean}
     * @private
     */
    isClippedByAncestor(el) {
        const { top, right, bottom, left } = el.getBoundingClientRect();
        for (
            let parent = el.parentElement;
            parent && parent !== document.documentElement;
            parent = parent.parentElement
        ) {
            if (!this.isOverflowing(parent)) {
                continue; // nothing sticks out of that ancestor, nor does el
            }
            // that check is only done on the few ancestors having an
            // overflowing content, as "getComputedStyle" isn't free
            const { overflowX, overflowY } = getComputedStyle(parent);
            if (overflowX === "visible" && overflowY === "visible") {
                continue; // that ancestor doesn't clip its content
            }
            const rect = parent.getBoundingClientRect();
            if (
                left < rect.left - 1 ||
                right > rect.right + 1 ||
                top < rect.top - 1 ||
                bottom > rect.bottom + 1
            ) {
                return true;
            }
        }
        return false;
    }

    /**
     * Detect if the text displayed by the element is entirely visible, i.e.
     * if it is neither truncated by an overflow (on the element itself or
     * on one of its descendants, e.g. an inner ".text-truncate"), nor
     * clipped by one of its ancestors.
     *
     * @param {HTMLElement} el
     * @return {boolean}
     * @private
     */
    isTextEntirelyVisible(el) {
        if (this.isOverflowing(el)) {
            return false; // most common case: the element itself is truncated
        }
        for (const descendant of el.querySelectorAll("*")) {
            // "isOverflowing" is a couple of integer reads, while
            // "textContent" walks the subtree of the element, so we only
            // look at the text of the few descendants that overflow: those
            // displaying no text can't hide any part of it anyway (e.g. a
            // button displaying only an icon).
            if (this.isOverflowing(descendant) && descendant.textContent.trim()) {
                return false;
            }
        }
        return !this.isClippedByAncestor(el);
    }

    /**
     * Detect if the tooltip would only repeat what the user can already
     * read, i.e. if it is a plain text tooltip (no template) whose content
     * is the text displayed by the element, that text being entirely
     * visible (i.e. neither truncated by an overflow nor clipped).
     *
     * @param {HTMLElement} el
     * @param {string} tooltip
     * @param {string} [template]
     * @return {boolean}
     * @private
     */
    isTooltipRedundant(el, tooltip, template) {
        if (template) {
            return false; // dynamic content, nothing to compare
        }
        const normalize = (str) => str.replace(/\s+/g, " ").trim();
        // "innerText" is used instead of "textContent" as it only contains
        // the text that is actually rendered, ignoring e.g. a label hidden
        // by a "d-none" on small screens, which the tooltip must display.
        if (normalize(el.innerText) !== normalize(tooltip)) {
            return false;
        }
        return this.isTextEntirelyVisible(el);
    }

    /**
     * Closes the currently opened tooltip if any, or prevent it from opening.
     * @private
     */
    cleanup() {
        this.target?.removeAttribute("aria-describedby");
        this.target?.removeAttribute("aria-details");
        this.target = null;
        window.clearTimeout(this.openTooltipTimeout);
        this.openTooltipTimeout = null;
        if (this.closeTooltip) {
            this.closeTooltip();
            this.closeTooltip = null;
        }
    }

    /**
     * Checks whether the target of the current tooltip has been removed from the DOM.
     * @returns {boolean}
     * @private
     */
    shouldCleanup() {
        return this.target?.isConnected === false;
    }

    /**
     * Checks whether there is a tooltip registered on the event target, and
     * if there is, creates a timeout to open the corresponding tooltip
     * after a delay.
     *
     * @param {HTMLElement} el the element on which to add the tooltip
     * @param {object} param1
     * @param {string} [param1.tooltip] the string to add as a tooltip, if
     *  no tooltip template is specified
     * @param {string} [param1.template] the name of the template to use for
     *  tooltip, if any
     * @param {object} [param1.info] info for the tooltip template
     * @param {'top'|'bottom'|'left'|'right'} param1.position
     * @param {number} [param1.delay] delay after which the popover should
     *  open
     * @private
     */
    openTooltip(el, { tooltip = "", template, info, position, delay = OPEN_DELAY }) {
        this.cleanup();
        if (!tooltip && !template) {
            return;
        }

        this.target = el;
        // Prevent title from showing on a parent at the same time (break the title scope heritage)
        if (!this.target.title) {
            this.target.title = "";
        }
        // Verify that the tooltip is actually useful.
        if (this.isTooltipRedundant(this.target, tooltip, template)) {
            return;
        }

        const tooltipId = generateHTMLId("tooltip_");
        if (tooltip) {
            this.target.setAttribute("aria-describedby", tooltipId);
        } else if (template) {
            this.target.setAttribute("aria-details", tooltipId);
        }
        const timeoutDelay = this.isHelpNode(el) ? 0 : delay;
        const popoverRef = signal.ref();
        this.closeTooltip = this.popover.add(
            this.target,
            Tooltip,
            { tooltip, template, info, tooltipId },
            { position, popoverClass: "visually-hidden", ref: popoverRef }
        );
        this.openTooltipTimeout = window.setTimeout(() => {
            if (!this.target.isConnected) {
                this.cleanup();
                return;
            }
            // The timeout doesn't guarantee that the popover is mounted yet.
            effect(() => {
                popoverRef()?.classList.remove("visually-hidden");
            });
        }, timeoutDelay);
    }

    /**
     * Checks whether there is a tooltip registered on the element, and
     * if there is, creates a timeout to open the corresponding tooltip
     * after a delay.
     *
     * @param {HTMLElement} el
     * @param { boolean | undefined } titleTooltip
     * @private
     */
    openElementsTooltip(el, titleTooltip) {
        // Fix weird behavior in Firefox where MouseEvent can be dispatched
        // from TEXT_NODE, even if they shouldn't...
        if (el.nodeType === Node.TEXT_NODE) {
            return;
        }
        const selector = titleTooltip ? TOOLTIP_SELECTOR_WITH_TITLE : TOOLTIP_SELECTOR;
        const element = el.closest(selector);
        if (element && element === this.target) {
            return;
        }
        if (element) {
            const dataset = element.dataset;
            const params = {
                tooltip: titleTooltip
                    ? element.dataset.tooltip || element.title
                    : element.dataset.tooltip,
                template: dataset.tooltipTemplate,
                position: dataset.tooltipPosition,
            };
            if (dataset.tooltipInfo) {
                params.info = JSON.parse(dataset.tooltipInfo);
            }
            if (dataset.tooltipDelay) {
                params.delay = parseInt(dataset.tooltipDelay, 10);
            }
            this.openTooltip(element, params);
        }
    }

    /**
     * Checks whether there is a tooltip registered on the event target, and
     * if there is, creates a timeout to open the corresponding tooltip
     * after a delay.
     *
     * @param {MouseEvent|FocusEvent} ev a "mouseenter" or "focusin" event
     * @private
     */
    onMouseenterOrFocusin(ev) {
        const target = ev.target?.closest(TOOLTIP_SELECTOR_WITH_TITLE);
        if (!target) {
            return;
        }
        if (target.title?.length) {
            // If we have a title attribute on a node, we should close the currently displayed tooltip
            // to avoid showing the tooltip and the title at the same time.
            if (this.openTooltipTimeout) {
                this.cleanup();
            }
            // If the title and tooltip are shown at the same time, remove the title and open the tooltip.
            if (target.dataset.tooltipTemplate || target.dataset.tooltip) {
                target.title = "";
                this.openElementsTooltip(target);
            }
        } else {
            this.openElementsTooltip(target);
        }
    }

    /**
     * Check whether there is a tooltip registered on the event target, and if there is,
     * cleanup it.
     * @param {MouseEvent} ev a "click" event
     * @private
     */
    onClick(ev) {
        if (this.isHelpNode(ev.target)) {
            ev.preventDefault();
        }
        this.cleanupTooltip(ev);
    }

    /**
     * Checks whether the new target is different from the target that lost
     * focus, and if so, clean it up.
     * @param {FocusEvent} ev
     */
    onFocusout(ev) {
        if (
            (this.target === ev.target || this.target === ev.target.closest(TOOLTIP_SELECTOR)) &&
            this.target !== ev.relatedTarget?.closest(TOOLTIP_SELECTOR)
        ) {
            this.cleanup();
        }
    }

    /** @private */
    cleanupTooltip(ev) {
        if (this.target == ev.target) {
            this.cleanup();
        }
    }

    /**
     * Checks whether there is a tooltip registered on the event target, and
     * if there is, creates a timeout to open the corresponding tooltip
     * after a delay.
     *
     * @param {TouchEvent} ev a "touchstart" event
     * @private
     */
    onTouchStart(ev) {
        this.cleanup();
        const timeoutDelay = this.isHelpNode(ev.target) ? 0 : SHOW_AFTER_DELAY;
        this.showTimer = window.setTimeout(() => {
            this.openElementsTooltip(ev.target, true);
        }, timeoutDelay);
    }

    /** @private */
    onTouchCancelEnd(ev) {
        if (this.isHelpNode(ev.target)) {
            ev.preventDefault();
            return;
        }
        if (ev.target.closest(TOOLTIP_SELECTOR_WITH_TITLE)) {
            if (!ev.target.dataset.tooltipTouchTapToShow) {
                window.clearTimeout(this.showTimer);
                this.showTimer = null;
                window.clearTimeout(this.openTooltipTimeout);
                this.openTooltipTimeout = null;
            }
        }
    }
}

services.add(TooltipPlugin);

/**
 * -----------------------------------------------------------------------------
 * @todo owl3 migration
 * temporary - to remove when all use of the tooltip service are removed
 * -----------------------------------------------------------------------------
 */
export const tooltipService = {
    dependencies: ["popover"],
    start() {
        return usePlugin(TooltipPlugin);
    },
};

registry.category("services").add("tooltip", tooltipService);
