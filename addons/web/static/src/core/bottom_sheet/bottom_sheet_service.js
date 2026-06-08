import { markRaw } from "@odoo/owl";
import { BottomSheet } from "@web/core/bottom_sheet/bottom_sheet";
import { registry } from "@web/core/registry";

/**
 * @typedef {{
 *   env?: object;
 *   onClose?: () => void;
 *   class?: string;
 *   role?: string;
 *   ref?: Function;
 *   useBottomSheet?: Boolean;
 * }} PopoverServiceAddOptions
 *
 * @typedef {ReturnType<popoverService["start"]>["add"]} PopoverServiceAddFunction
 */

export const popoverService = {
    dependencies: ["overlay"],
    start(_, { overlay }) {
        let bottomSheetCount = 0;
        /**
         * Signals the manager to add a popover.
         *
         * @param {HTMLElement} target
         * @param {typeof import("@odoo/owl").Component} component
         * @param {object} [props]
         * @param {PopoverServiceAddOptions} [options]
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
                    rootId: target.getRootNode()?.host?.id,
                }
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

registry.category("services").add("bottom_sheet", popoverService);
