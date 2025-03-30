import { onWillUnmount, status, useComponent } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * @typedef {import("@web/core/popover/popover_service").PopoverServiceAddFunction} PopoverServiceAddFunction
 * @typedef {import("@web/core/popover/popover_service").PopoverServiceAddOptions} PopoverServiceAddOptions
 * @property {boolean} [useBottomSheet] Whether to use bottom sheet on mobile (default: true)
 * @property {string} [title] Title to display in the popover or bottom sheet header
 * @property {string} [popoverClass] CSS classes to apply to the popover
 * Specific to bottom sheet:
 * @property {string} [sheetClasses] CSS classes to apply specifically to the bottom sheet
 * @property {boolean} [initialHeightPercent] Initial height of bottom sheet as percentage
 * @property {boolean} [maxHeightPercent] Maximum height of bottom sheet as percentage
 */

/**
 * @typedef PopoverHookReturnType
 * @property {(target: string | HTMLElement, props: object) => void} open
 *  - Signals the manager to open the configured popover
 *    component on the target, with the given props.
 * @property {() => void} close
 *  - Signals the manager to remove the popover.
 * @property {boolean} isOpen
 *  - Whether the popover is currently open.
 */

/**
 * @param {PopoverServiceAddFunction} addFn
 * @param {typeof import("@odoo/owl").Component} component
 * @param {PopoverServiceAddOptions} options
 * @returns {PopoverHookReturnType}
 */
export function makePopover(addFn, component, options) {
    let removeFn = null;
    function close() {
        removeFn?.();
    }
    return {
        open(target, props) {
            close();
            const newOptions = Object.create(options);
            newOptions.onClose = () => {
                removeFn = null;
                options.onClose?.();
            };
            removeFn = addFn(target, component, props, newOptions);
        },
        close,
        get isOpen() {
            return Boolean(removeFn);
        },
    };
}

/**
 * Manages a component to be used as a popover.
 *
 * @param {typeof import("@odoo/owl").Component} component
 * @param {PopoverServiceAddOptions} [options]
 * @returns {PopoverHookReturnType}
 */
export function usePopover(component, options = {}) {
    const popoverService = useService("popover");
    const owner = useComponent();
    const newOptions = Object.create(options);
    newOptions.onClose = () => {
        if (status(owner) !== "destroyed") {
            options.onClose?.();
        }
    };
    const popover = makePopover(popoverService.add, component, newOptions);
    onWillUnmount(popover.close);
    return popover;
}
