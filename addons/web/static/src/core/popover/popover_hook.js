/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";

import { onWillUnmount, status, useComponent } from "@odoo/owl";

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
 * Manages a component to be used as a popover.
 *
 * @param {typeof import("@odoo/owl").Component} component
 * @param {import("@web/core/popover/popover_service").PopoverServiceAddOptions} [options]
 * @returns {PopoverHookReturnType}
 */
export function usePopover(component, options = {}) {
    let removeFn = null;
    const popover = useService("popover");
    const owner = useComponent();
    function close() {
        removeFn?.();
    }
    onWillUnmount(close);
    return {
        open(target, props) {
            close();
            const newOptions = Object.create(options);
            newOptions.onClose = function () {
                removeFn = null;
                if (status(owner) !== "destroyed") {
                    options.onClose?.();
                }
            };
            removeFn = popover.add(target, component, props, newOptions);
        },
        close,
        get isOpen() {
            return Boolean(removeFn);
        },
    };
}
