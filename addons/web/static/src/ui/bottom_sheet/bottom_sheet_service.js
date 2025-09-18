// @ts-check

/** @module @web/ui/bottom_sheet/bottom_sheet_service - Service for programmatically showing mobile bottom sheet overlays */

import { markRaw } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { BottomSheet } from "@web/ui/bottom_sheet/bottom_sheet";

/**
 * @typedef {{
 *   env?: object;
 *   onClose?: () => void;
 *   class?: string;
 *   role?: string;
 *   ref?: Function;
 *   useBottomSheet?: Boolean;
 * }} BottomSheetServiceAddOptions
 *
 * @typedef {ReturnType<bottomSheetService["start"]>["add"]} BottomSheetServiceAddFunction
 */

/** Service for showing mobile-friendly bottom sheet overlays (slide-up panels). */
export const bottomSheetService = {
    dependencies: ["overlay"],
    start(_, { overlay }) {
        let bottomSheetCount = 0;
        /**
         * Signals the manager to add a popover.
         *
         * @param {HTMLElement} target
         * @param {typeof import("@odoo/owl").Component} component
         * @param {object} [props]
         * @param {BottomSheetServiceAddOptions} [options]
         * @returns {() => void}
         */
        const add = (target, component, props = {}, options = {}) => {
            function removeAndUpdateCount() {
                _remove();
                bottomSheetCount--;
                if (bottomSheetCount === 0) {
                    document.body.classList.remove("bottom-sheet-open");
                } else if (bottomSheetCount === 1) {
                    document.body.classList.remove("bottom-sheet-open-multiple");
                }
            }
            const _remove = overlay.add(
                BottomSheet,
                {
                    close: removeAndUpdateCount,
                    component,
                    componentProps: markRaw(props),
                    ref: options.ref,
                    class: options.class,
                    role: options.role,
                },
                {
                    env: options.env,
                    onRemove: options.onClose,
                    rootId: /** @type {ShadowRoot} */ (target.getRootNode())?.host?.id,
                },
            );
            bottomSheetCount++;
            if (bottomSheetCount === 1) {
                document.body.classList.add("bottom-sheet-open");
            } else if (bottomSheetCount > 1) {
                document.body.classList.add("bottom-sheet-open-multiple");
            }

            return removeAndUpdateCount;
        };

        return { add };
    },
};

registry.category("services").add("bottom_sheet", bottomSheetService);
