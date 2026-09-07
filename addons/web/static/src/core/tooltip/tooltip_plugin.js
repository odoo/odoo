import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { services } from "@web/core/services";
import { Tooltip } from "./tooltip";
import { hasTouch } from "@web/core/browser/feature_detection";
import { PopoverPlugin } from "@web/core/popover/popover_plugin";

import { onWillDestroy, Plugin, usePlugin, whenReady } from "@odoo/owl";

/**
 * The tooltip service allows to display custom tooltips on every elements with
 * a "data-tooltip" attribute. This attribute can be set on elements for which
 * we prefer a custom tooltip instead of the native one displaying the value of
 * the "title" attribute.
 *
 * Usage:
 *   <button data-tooltip="This is a tooltip">Do something</button>
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
    /** @private @type {[EventTarget, string, Function, object][]} */
    listeners = [];

    setup() {
        whenReady(() => {
            this.interval = browser.setInterval(() => {
                if (this.shouldCleanup()) {
                    this.cleanup();
                }
            }, CLOSE_DELAY);

            if (hasTouch()) {
                const onTouchCancelEnd = this.onTouchCancelEnd.bind(this);
                this.addListener(document.body, "touchstart", this.onTouchStart.bind(this));
                this.addListener(document.body, "touchend", onTouchCancelEnd);
                this.addListener(document.body, "touchcancel", onTouchCancelEnd);
            }

            // Listen (using event delegation) to "mouseenter" events to open the tooltip if any
            this.addListener(document.body, "mouseenter", this.onMouseenter.bind(this), {
                capture: true,
            });
            // Listen (using event delegation) to "mouseleave" events to close the tooltip if any
            this.addListener(document.body, "mouseleave", this.cleanupTooltip.bind(this), {
                capture: true,
            });
            this.addListener(document.body, "click", this.onClick.bind(this), { capture: true });
        });

        onWillDestroy(() => {
            browser.clearInterval(this.interval);
            this.removeListeners();
        });
    }

    /** @private */
    addListener(target, type, listener, options) {
        target.addEventListener(type, listener, options);
        this.listeners.push([target, type, listener, options]);
    }

    /** @private */
    removeListeners() {
        for (const [target, type, listener, options] of this.listeners) {
            target.removeEventListener(type, listener, options);
        }
        this.listeners = [];
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
     * Closes the currently opened tooltip if any, or prevent it from opening.
     * @private
     */
    cleanup() {
        this.target = null;
        browser.clearTimeout(this.openTooltipTimeout);
        this.openTooltipTimeout = null;
        if (this.closeTooltip) {
            this.closeTooltip();
            this.closeTooltip = null;
        }
    }

    /**
     * Checks that the target is in the DOM and we're hovering the target.
     * @returns {boolean}
     * @private
     */
    shouldCleanup() {
        if (!this.target) {
            return false;
        }
        if (!document.body.contains(this.target)) {
            return true; // target is no longer in the DOM
        }
        return false;
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
        const timeoutDelay = this.isHelpNode(el) ? 0 : delay;
        this.openTooltipTimeout = browser.setTimeout(() => {
            // verify that the element is still in the DOM
            if (this.target.isConnected) {
                this.closeTooltip = this.popover.add(
                    this.target,
                    Tooltip,
                    { tooltip, template, info },
                    { position }
                );
            }
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
     * @param {MouseEvent} ev a "mouseenter" event
     * @private
     */
    onMouseenter(ev) {
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
        this.showTimer = browser.setTimeout(() => {
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
                browser.clearTimeout(this.showTimer);
                this.showTimer = null;
                browser.clearTimeout(this.openTooltipTimeout);
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
