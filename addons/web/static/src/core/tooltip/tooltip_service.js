/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { Tooltip } from "./tooltip";
import { hasTouch } from "@web/core/browser/feature_detection";

const { whenReady } = owl;

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

const OPEN_DELAY = 400;
const CLOSE_DELAY = 200;

export const tooltipService = {
    dependencies: ["popover"],
    start(env, { popover }) {
        let openTooltipTimeout;
        let closeTooltip;
        let target = null;
        let positionX;
        let positionY;
        let touchPressed;
        const elementsWithTooltips = new Map();

        /**
         * Closes the currently opened tooltip if any, or prevent it from opening.
         */
        function cleanup() {
            browser.clearTimeout(openTooltipTimeout);
            if (closeTooltip) {
                closeTooltip();
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
            if (hasTouch()) {
                return !touchPressed;
            }
            const targetRect = target.getBoundingClientRect();
            if (
                positionX < targetRect.left ||
                positionX > targetRect.right ||
                positionY < targetRect.top ||
                positionY > targetRect.bottom
            ) {
                return true; // mouse is no longer hovering the target
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
            target = el;
            cleanup();
            if (!tooltip && !template) {
                return;
            }

            openTooltipTimeout = browser.setTimeout(() => {
                if (shouldCleanup()) {
                    cleanup();
                } else {
                    closeTooltip = popover.add(
                        target,
                        Tooltip,
                        { tooltip, template, info },
                        { position }
                    );
                    // Prevent title from showing on a parent at the same time
                    target.title = "";
                }
            }, delay);
        }

        /**
         * Checks whether there is a tooltip registered on the element, and
         * if there is, creates a timeout to open the corresponding tooltip
         * after a delay.
         *
         * @param {HTMLElement} el
         */
        function openElementsTooltip(el) {
            if (elementsWithTooltips.has(el)) {
                openTooltip(el, elementsWithTooltips.get(el));
            } else if (el.matches("[data-tooltip], [data-tooltip-template]")) {
                const {
                    tooltip,
                    tooltipInfo,
                    tooltipDelay,
                    tooltipTemplate: template,
                    tooltipPosition: position,
                } = el.dataset;
                const delay = parseInt(tooltipDelay);
                const info = tooltipInfo ? JSON.parse(tooltipInfo) : null;
                openTooltip(el, { tooltip, template, delay, info, position });
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
            // set mouse position in case the target contains disabled elements which won't trigger mousemove
            positionX = ev.x;
            positionY = ev.y;
            openElementsTooltip(ev.target);
        }

        /**
         * Checks whether there is a tooltip registered on the event target, and
         * if there is, creates a timeout to open the corresponding tooltip
         * after a delay.
         *
         * @param {TouchEvent} ev a "touchstart" event
         */
        function onTouchStart(ev) {
            touchPressed = true;
            openElementsTooltip(ev.target);
        }

        whenReady(() => {
            // Regularly check that the target is still in the DOM and we're still
            // hovering it, because if not, we have to close the tooltipd
            browser.setInterval(() => {
                if (shouldCleanup()) {
                    cleanup();
                }
            }, CLOSE_DELAY);

            if (hasTouch()) {
                document.body.addEventListener("touchstart", onTouchStart);

                document.body.addEventListener("touchend", (ev) => {
                    if (ev.target.matches("[data-tooltip], [data-tooltip-template]")) {
                        if (!ev.target.dataset.tooltipTouchTapToShow) {
                            touchPressed = false;
                        }
                    }
                });

                document.body.addEventListener("touchcancel", (ev) => {
                    if (ev.target.matches("[data-tooltip], [data-tooltip-template]")) {
                        if (!ev.target.dataset.tooltipTouchTapToShow) {
                            touchPressed = false;
                        }
                    }
                });

                return;
            }

            // Track mouse position to be able to detect that we are no longer hovering
            // the target, thus that we should close the tooltip
            document.body.addEventListener("mousemove", (ev) => {
                positionX = ev.x;
                positionY = ev.y;
            });

            // Listen (using event delegation) to "mouseenter" events on all nodes with
            // the "data-tooltip" or "data-tooltip-template" attribute, to open the tooltip.
            document.body.addEventListener("mouseenter", onMouseenter, { capture: true });
        });

        return {
            add(el, params) {
                elementsWithTooltips.set(el, params);
                return () => {
                    elementsWithTooltips.delete(el);
                    if (target === el) {
                        cleanup();
                    }
                };
            },
        };
    },
};

registry.category("services").add("tooltip", tooltipService);
