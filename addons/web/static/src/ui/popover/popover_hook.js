// @ts-check

/** @module @web/ui/popover/popover_hook - usePopover hook for open/close lifecycle management within OWL components */

import { onWillUnmount, status, useComponent } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
/** @import { PopoverServiceAddFunction, PopoverServiceAddOptions } from "@web/ui/popover/popover_service" */

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
            removeFn = addFn(/** @type {any} */ (target), component, props, newOptions);
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
    let service;
    if (/** @type {any} */ (options).useBottomSheet) {
        service = useService("bottom_sheet");
    } else {
        service = useService("popover");
    }
    const owner = useComponent();
    const newOptions = Object.create(options);
    newOptions.onClose = () => {
        if (status(owner) !== "destroyed") {
            options.onClose?.();
        }
    };
    const popover = makePopover(service.add, component, newOptions);
    onWillUnmount(popover.close);
    return popover;
}
