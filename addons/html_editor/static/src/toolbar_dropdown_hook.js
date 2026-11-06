import { proxy, untrack, useEffect, useListener } from "@odoo/owl";
import { usePopover } from "@web/core/popover/popover_hook";
import { Tooltip } from "@web/core/tooltip/tooltip";

export function useDropdownAutoVisibility(overlayState, popoverRef) {
    if (!overlayState) {
        return;
    }
    const state = proxy(overlayState);
    const getEl = () => untrack(popoverRef);
    useEffect(() => {
        const isOverlayVisible = state.isOverlayVisible;
        const el = getEl();
        if (el) {
            if (!isOverlayVisible) {
                el.style.visibility = "hidden";
            } else {
                el.style.visibility = "visible";
            }
        }
    });
}

export function useToolbarDropdownFocus(dropdown, buttonRef) {
    useListener(
        document,
        "keydown",
        (ev) => {
            if (ev.key === "Escape" && dropdown.isOpen) {
                buttonRef()?.focus();
            }
        },
        { capture: true }
    );
}

/**
 * The `title` of an element is only displayed by the browser on hover: this
 * hook displays it as a tooltip when an element inside the given container
 * gets the focus from the keyboard as well. It is not displayed when the
 * focus comes from a pointer, as the native tooltip is then displayed on
 * hover.
 *
 * @param {() => HTMLElement | null} containerRef
 */
export function useFocusTooltip(containerRef) {
    const tooltip = usePopover(Tooltip, { setActiveElement: false });
    let isPointerFocus = false;
    useListener(containerRef, "pointerdown", () => {
        isPointerFocus = true;
    });
    useListener(containerRef, "pointerup", () => {
        isPointerFocus = false;
    });
    useListener(containerRef, "focusin", (ev) => {
        tooltip.close();
        const el = ev.target.closest("[title]");
        if (isPointerFocus || !el?.title || !ev.currentTarget.contains(el)) {
            return;
        }
        tooltip.open(el, { tooltip: el.title });
    });
    useListener(containerRef, "focusout", () => tooltip.close());
}
