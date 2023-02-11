/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { useEffect, useListener } from "@web/core/utils/hooks";
import { usePopover } from "@web/core/popover/popover_hook";
import { Tooltip } from "./tooltip";

/**
 * The useTooltip hook allows to display custom tooltips on every elements with
 * a "data-tooltip" attribute inside the Component using the hook. This attribute
 * can be set on elements for which we prefer a custom tooltip instead of the
 * native one displaying the value of the "title" attribute.
 *
 * Usage (with a parent somewhere using the useTooltip hook):
 *   <button data-tooltip="This is a tooltip">Do something</button>
 *
 * The ideal position of the tooltip can be specified thanks to the attribute
 * "data-tooltip-position":
 *   <button data-tooltip="This is a tooltip" data-tooltip-position="left">Do something</button>
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
export function useTooltip() {
    const popover = usePopover();
    let openTooltipTimeout;
    let closeTooltip;
    let target = null;

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
     * Opens the tooltip after a delay, if the event's target has a data-tooltip
     * attribute.
     *
     * @param {MouseEvent} ev a "mouseenter" event
     */
    function onMouseEnter(ev) {
        const dataset = ev.target.dataset;
        const tooltip = dataset.tooltip;
        let template, info;
        if ("tooltipTemplate" in dataset) {
            template = dataset.tooltipTemplate;
            info = dataset.tooltipInfo ? JSON.parse(dataset.tooltipInfo) : null;
        }
        if (tooltip || template) {
            cleanup();
            target = ev.target;
            openTooltipTimeout = browser.setTimeout(() => {
                const position = dataset.tooltipPosition;
                closeTooltip = popover.add(
                    target,
                    Tooltip,
                    { tooltip, template, info },
                    { position }
                );
            }, OPEN_DELAY);
        }
    }

    // Track mouse position to be able to detect that we are no longer hovering
    // the target, thus that we should close the tooltip
    let positionX;
    let positionY;
    useListener("mousemove", (ev) => {
        positionX = ev.x;
        positionY = ev.y;
    });

    // Regularly check that the target is still in the DOM and we're still
    // hovering it, because if not, we have to close the tooltip
    useEffect(
        () => {
            const interval = browser.setInterval(() => {
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
                    return cleanup(); // mouse is no longer hovering the target
                }
            }, CLOSE_DELAY);
            return () => browser.clearInterval(interval);
        },
        () => []
    );

    // Listen (using event delegation) to "mouseenter" events on all nodes with
    // the "data-tooltip" or "data-tooltip-template" attribute, to open the tooltip.
    const selector = "[data-tooltip], [data-tooltip-template]";
    useListener("mouseenter", selector, onMouseEnter, { capture: true });
}
