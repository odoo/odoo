import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { Tooltip } from "./tooltip";
import { hasTouch } from "@web/core/browser/feature_detection";

import { whenReady } from "@odoo/owl";

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

export const tooltipService = {
    dependencies: ["popover"],
    start(env, { popover }) {
        let openTooltipTimeout;
        let closeTooltip;
        let showTimer;
        let target = null;

        /**
         * Detect if the current node is the `sup` tooltip node
         * @param {HTMLElement} el
         * @return {boolean}
         */
        function isHelpNode(el) {
            return (
                el.textContent === "?" &&
                (el.hasAttribute("data-tooltip") || el.hasAttribute("data-tooltip-template"))
            );
        }

        /**
         * Closes the currently opened tooltip if any, or prevent it from opening.
         */
        function cleanup() {
            target = null;
            browser.clearTimeout(openTooltipTimeout);
            openTooltipTimeout = null;
            if (closeTooltip) {
                closeTooltip();
                closeTooltip = null;
            }
        }

        /**
         * Checks that the target is in the DOM and we're hovering the target.
         * @returns {boolean}
         */
        function shouldCleanup() {
            if (!target) {
                return false;
            }
            if (!document.body.contains(target)) {
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
         */
        function openTooltip(el, { tooltip = "", template, info, position, delay = OPEN_DELAY }) {
            cleanup();
            if (!tooltip && !template) {
                return;
            }

            target = el;
            // Prevent title from showing on a parent at the same time (break the title scope heritage)
            if (!target.title) {
                target.title = "";
            }
            const timeoutDelay = isHelpNode(el) ? 0 : delay;
            openTooltipTimeout = browser.setTimeout(() => {
                // verify that the element is still in the DOM
                if (target.isConnected) {
                    closeTooltip = popover.add(
                        target,
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
         */
        function openElementsTooltip(el, titleTooltip) {
            // Fix weird behavior in Firefox where MouseEvent can be dispatched
            // from TEXT_NODE, even if they shouldn't...
            if (el.nodeType === Node.TEXT_NODE) {
                return;
            }
            const selector = titleTooltip ? TOOLTIP_SELECTOR_WITH_TITLE : TOOLTIP_SELECTOR;
            const element = el.closest(selector);
            if (element && element === target) {
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
                openTooltip(element, params);
            }
        }

        /**
         * Checks whether there is a tooltip registered on the event target, and
         * if there is, creates a timeout to open the corresponding tooltip
         * after a delay.
         *
         * @param {MouseEvent} ev a "mouseenter" event
         */
        function onMouseenter(ev) {
            const target = ev.target?.closest(TOOLTIP_SELECTOR_WITH_TITLE);
            if (!target) {
                return;
            }
            if (target.title?.length) {
                // If we have a title attribute on a node, we should close the currently displayed tooltip
                // to avoid showing the tooltip and the title at the same time.
                if (openTooltipTimeout) {
                    cleanup();
                }
                // If the title and tooltip are shown at the same time, remove the title and open the tooltip.
                if (target.dataset.tooltipTemplate || target.dataset.tooltip) {
                    target.title = "";
                    openElementsTooltip(target);
                }
            } else {
                openElementsTooltip(target);
            }
        }

        /**
         * Check whether there is a tooltip registered on the event target, and if there is,
         * cleanup it.
         * @param {MouseEvent} ev a "click" event
         */
        function onClick(ev) {
            if (isHelpNode(ev.target)) {
                ev.preventDefault();
            }
            cleanupTooltip(ev);
        }

        function cleanupTooltip(ev) {
            if (target == ev.target) {
                cleanup();
            }
        }
        /**
         * Checks whether there is a tooltip registered on the event target, and
         * if there is, creates a timeout to open the corresponding tooltip
         * after a delay.
         *
         * @param {TouchEvent} ev a "touchstart" event
         */
        function onTouchStart(ev) {
            cleanup();
            const timeoutDelay = isHelpNode(ev.target) ? 0 : SHOW_AFTER_DELAY;
            showTimer = browser.setTimeout(() => {
                openElementsTooltip(ev.target, true);
            }, timeoutDelay);
        }

        function onTouchCancelEnd(ev) {
            if (isHelpNode(ev.target)) {
                ev.preventDefault();
                return;
            }
            if (ev.target.closest(TOOLTIP_SELECTOR_WITH_TITLE)) {
                if (!ev.target.dataset.tooltipTouchTapToShow) {
                    browser.clearTimeout(showTimer);
                    showTimer = null;
                    browser.clearTimeout(openTooltipTimeout);
                    openTooltipTimeout = null;
                }
            }
        }

        whenReady(() => {
            // Regularly check that the target is still in the DOM and if not, close the tooltip
            browser.setInterval(() => {
                if (shouldCleanup()) {
                    cleanup();
                }
            }, CLOSE_DELAY);

            if (hasTouch()) {
                document.body.addEventListener("touchstart", onTouchStart);
                document.body.addEventListener("touchend", onTouchCancelEnd);
                document.body.addEventListener("touchcancel", onTouchCancelEnd);
            }

            // Listen (using event delegation) to "mouseenter" events to open the tooltip if any
            document.body.addEventListener("mouseenter", onMouseenter, { capture: true });
            // Listen (using event delegation) to "mouseleave" events to close the tooltip if any
            document.body.addEventListener("mouseleave", cleanupTooltip, { capture: true });
            document.body.addEventListener("click", onClick, { capture: true });
        });
    },
};

registry.category("services").add("tooltip", tooltipService);
