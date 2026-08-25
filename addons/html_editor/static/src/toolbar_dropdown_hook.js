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
 * @param {() => import("@html_editor/core/history_plugin").PreviewableOperation} params.previewable
 */
export function useToolbarDropdownPreview({ dropdown, previewable }) {
    let previewedItem;

    const resetPreview = () => {
        previewedItem = undefined;
        const { activeElement } = document;
        previewable().revert();
        if (activeElement && document.activeElement !== activeElement) {
            activeElement.focus();
        }
    };

    useEffect(() => {
        if (dropdown.isOpen) {
            return resetPreview;
        }
    });

    return {
        preview(ev, item) {
            if (!dropdown.isOpen || item === previewedItem) {
                return;
            }
            previewedItem = item;
            const { activeElement } = document;
            previewable().preview(item);
            if (activeElement && document.activeElement !== activeElement) {
                activeElement.focus();
            }
        },
        commit(item) {
            previewedItem = undefined;
            previewable().commit(item);
        },
        reset: resetPreview,
    };
}
