/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { useListener } from "@web/core/utils/hooks";
import { usePopover } from "@web/core/popover/popover_hook";
import { Tooltip } from "./tooltip";
import { registry } from "@web/core/registry";

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

        let Component, props;
        if ("tooltipComponent" in dataset) {
            ({ Component, props } = JSON.parse(dataset["tooltipComponent"]));
            Component = registry.category("tooltips").get(Component, null);
        }
        if (tooltip || Component) {
            cleanup();
            target = ev.target;
            openTooltipTimeout = browser.setTimeout(() => {
                const position = dataset.tooltipPosition;
                closeTooltip = popover.add(
                    target,
                    Tooltip,
                    { tooltip, Component, props },
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
    browser.setInterval(() => {
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

    // Listen (using event delegation) to "mouseenter" events on all nodes with
    // the "data-tooltip" attribute, to open the tooltip.
    useListener("mouseenter", "[data-tooltip]", onMouseEnter, { capture: true });
}
