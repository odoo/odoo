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
                const onKeyUp = (ev) => {
                    if (ev.key === "Escape" && !dropdown.isOpen) {
                        buttonRef()?.focus();
                    }
                };

                document.addEventListener("keyup", onKeyUp, {
                    capture: true,
                    once: true,
                });
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
 * @param {() => any[]} params.getItems
 * @param {() => import("@html_editor/core/history_plugin").PreviewableOperation} [params.previewable]
 */
export function useToolbarDropdownPreview({ dropdown, getItems, previewable }) {
    /** @type {import("@web/core/navigation/navigation").Navigator} */
    let navigator;
    let activeEl;

    const resetPreview = () => {
        navigator?.clearActive();
        activeEl = undefined;
        previewable().revert();
    };

    useEffect(() => {
        if (dropdown.isOpen) {
            return resetPreview;
        }
    });

    return {
        commit(item) {
            activeEl = undefined;
            previewable().commit(item);
        },
        reset: resetPreview,
        navigationOptions: {
            onUpdated: (nav) => {
                navigator = nav;
            },
            onItemActivated: (el) => {
                if (el === activeEl) {
                    return;
                }
                activeEl = el;
                const item = getItems()[Number(el.dataset.previewIndex)];
                if (item) {
                    previewable().preview(item);
                    el.focus();
                }
            },
        },
    };
}
