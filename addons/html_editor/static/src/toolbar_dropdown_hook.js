import { proxy, untrack, useEffect, useListener } from "@odoo/owl";

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
