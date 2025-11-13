import { onWillUnmount, reactive, status, useComponent, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * @typedef {import("@web/core/popover/popover_service").PopoverServiceAddFunction} PopoverServiceAddFunction
 * @typedef {import("@web/core/popover/popover_service").PopoverServiceAddOptions} PopoverServiceAddOptions
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
    return reactive({
        _removeFn: null,
        open(target, props) {
            this.close();
            const newOptions = Object.create(options);
            newOptions.onClose = () => {
                this._removeFn = null;
                options.onClose?.();
            };
            this._removeFn = addFn(target, component, props, newOptions);
        },
        close() {
            this._removeFn?.();
        },
        get isOpen() {
            return Boolean(this._removeFn);
        },
    });
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
    if (options.useBottomSheet) {
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
    const popover = useState(makePopover(service.add, component, newOptions));
    onWillUnmount(() => popover.close());
    return popover;
}
