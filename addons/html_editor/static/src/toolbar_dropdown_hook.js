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

/**
 * Manages the focus of a toolbar dropdown:
 * - Escape moves the focus back to the dropdown toggle,
 * - when the dropdown is opened from the keyboard, its active item (i.e. the
 *   current value) gets the focus, so that keyboard and screen reader users
 *   start from it. Without active item, the focus stays on the toggle: focusing
 *   another item would preview it.
 *
 * @param {Object} dropdown state of the dropdown, as returned by `useDropdownState`
 * @param {() => HTMLElement | null} buttonRef dropdown toggle reference
 * @param {() => HTMLElement | null} menuRef dropdown menu reference
 */
export function useToolbarDropdownFocus(dropdown, buttonRef, menuRef) {
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
    // A click triggered by the keyboard (Enter or Space) has no `detail`.
    // Opening the dropdown with the arrows does not trigger a click.
    let isOpenedByPointer = false;
    useListener(buttonRef, "click", (ev) => {
        isOpenedByPointer = ev.detail !== 0;
    });
    useEffect(() => {
        const menuEl = menuRef();
        if (!dropdown.isOpen) {
            isOpenedByPointer = false;
            return;
        }
        if (!menuEl || isOpenedByPointer || document.activeElement !== untrack(buttonRef)) {
            return;
        }
        menuEl.querySelector(".o-dropdown-item.active")?.focus();
    });
}

/**
 * Previews a toolbar dropdown item while it is hovered or navigated to, and
 * reverts the preview when the pointer leaves the menu or the dropdown closes.
 *
 * @param {Object} params
 * @param {Object} params.dropdown state of the dropdown, as returned by `useDropdownState`
 * @param {() => HTMLElement | null} params.menuRef dropdown menu reference
 * @param {import("@html_editor/core/history_plugin").PreviewableOperation} params.previewableOperation
 */
export function useToolbarDropdownPreview({ dropdown, menuRef, previewableOperation }) {
    let previewedItem;

    const revertPreview = () => {
        previewedItem = undefined;
        const { activeElement } = document;
        previewableOperation.revert();
        if (activeElement && document.activeElement !== activeElement) {
            activeElement.focus();
        }
    };

    useListener(menuRef, "mouseleave", revertPreview);

    useEffect(() => {
        if (dropdown.isOpen) {
            return revertPreview;
        }
    });

    return {
        preview(item) {
            if (!dropdown.isOpen || item === previewedItem) {
                return;
            }
            previewedItem = item;
            const { activeElement } = document;
            previewableOperation.preview(item);
            if (activeElement && document.activeElement !== activeElement) {
                activeElement.focus();
            }
        },
        commit(item) {
            previewedItem = undefined;
            previewableOperation.commit(item);
        },
        revert: revertPreview,
    };
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
    const tooltip = usePopover(Tooltip, { closeOnEscape: false, setActiveElement: false });
    // Whether the next focus comes from a pointer. It is only valid for the
    // focus given by the pointer down: it is reset when the pointer is
    // released anywhere, and once used, as the pointer may be released in
    // another document (e.g. the iframe of the editable).
    let isPointerFocus = false;
    const resetPointerFocus = () => {
        isPointerFocus = false;
    };
    useListener(containerRef, "pointerdown", () => {
        isPointerFocus = true;
    });
    useListener(document, "pointerup", resetPointerFocus, { capture: true });
    useListener(document, "pointercancel", resetPointerFocus, { capture: true });
    useListener(containerRef, "focusin", (ev) => {
        const isFocusedByPointer = isPointerFocus;
        isPointerFocus = false;
        tooltip.close();
        const el = ev.target.closest("[title]");
        if (isFocusedByPointer || !el?.title || !ev.currentTarget.contains(el)) {
            return;
        }
        tooltip.open(el, { tooltip: el.title });
    });
    useListener(containerRef, "focusout", () => tooltip.close());
    // e.g. a dropdown opened from the keyboard while its toggle keeps the
    // focus (capture, as dropdown toggles stop the propagation of clicks)
    useListener(containerRef, "click", () => tooltip.close(), { capture: true });
}
