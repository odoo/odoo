/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { Tooltip } from "./tooltip";

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
                return;
            }
            if (!document.body.contains(target)) {
                return cleanup(); // target is no longer in the DOM
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
         * Opens the tooltip after a delay, if the event's target has a data-tooltip
         * attribute.
         *
         * @param {MouseEvent} ev a "mouseenter" event
         */
        function onMouseenter(ev) {
            let el = ev.target;
            if (!el.matches("[data-tooltip], [data-tooltip-template]")) {
                return;
            }
            target = el;
            const dataset = el.dataset;
            const tooltip = dataset.tooltip;
            let template, info;
            if ("tooltipTemplate" in dataset) {
                template = dataset.tooltipTemplate;
                info = dataset.tooltipInfo ? JSON.parse(dataset.tooltipInfo) : null;
            }
            if (tooltip && tooltip === "" && !template) {
                return;
            }
            cleanup();
            openTooltipTimeout = browser.setTimeout(() => {
                if (shouldCleanup()) {
                    cleanup();
                } else {
                    const position = dataset.tooltipPosition;
                    closeTooltip = popover.add(
                        target,
                        Tooltip,
                        { tooltip, template, info },
                        { position }
                    );
                }
            }, dataset.tooltipDelay || OPEN_DELAY);
        }

        whenReady(() => {
            // Regularly check that the target is still in the DOM and we're still
            // hovering it, because if not, we have to close the tooltipd
            browser.setInterval(() => {
                if (shouldCleanup()) {
                    cleanup();
                }
            }, CLOSE_DELAY);

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
    },
};

registry.category("services").add("tooltip", tooltipService);
