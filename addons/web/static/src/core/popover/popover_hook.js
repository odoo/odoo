/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";

import { onWillUnmount, status, useComponent, useEnv } from "@odoo/owl";
import { POPOVER_SYMBOL } from "./popover_controller";

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

export function makePopover(popoverService, component, options) {
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
            removeFn = popoverService.add(target, component, props, newOptions);
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
 * @param {import("@web/core/popover/popover_service").PopoverServiceAddOptions} [options]
 * @returns {PopoverHookReturnType}
 */
export function usePopover(component, options = {}) {
    const env = useEnv();
    const popoverService = useService("popover");
    const owner = useComponent();
    const newOptions = Object.create(options);
    newOptions[POPOVER_SYMBOL] = env[POPOVER_SYMBOL];
    newOptions.onClose = () => {
        if (status(owner) !== "destroyed") {
            options.onClose?.();
        }
    };
    const popover = makePopover(popoverService, component, newOptions);
    onWillUnmount(popover.close);
    return popover;
}
