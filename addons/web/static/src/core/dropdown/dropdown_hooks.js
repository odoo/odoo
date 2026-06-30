import { useEnv, useState } from "@odoo/owl";
import { DROPDOWN_NESTING } from "@web/core/dropdown/_behaviours/dropdown_nesting";
import { Reactive } from "@web/core/utils/reactive";

/**
 * Represents the state of a dropdown.
 * In order to use it, pass the state instance to the dropdown component, i.e.:
 *  <Dropdown state="dropdownState" ...>...</Dropdown>
 * @param {Object} callbacks
 * @param {Function} callbacks.onOpen
 * @param {Function} callbacks.onClose
 */
export class DropdownState extends Reactive {
    isOpen = false;
    constructor({ onOpen, onClose } = {}) {
        super();
        this._onOpen = onOpen;
        this._onClose = onClose;
    }
    open() {
        this.isOpen = true;
        this._onOpen?.();
    }
    close() {
        this.isOpen = false;
        this._onClose?.();
    }
}

/**
 * Hook used to interact with the Dropdown state and to subscribe to changes.
 * @param {Object} callbacks
 * @param {Function} callbacks.onOpen
 * @param {Function} callbacks.onClose
 * @returns {DropdownState}
 */
export function useDropdownState({ onOpen, onClose } = {}) {
    return useState(new DropdownState({ onOpen, onClose }));
}

/**
 * Can be used by components to have some control
 * how and when a wrapping dropdown should close.
 */
export function useDropdownCloser() {
    const env = useEnv();
    const dropdown = env[DROPDOWN_NESTING];
    return {
        close: () => dropdown?.close(),
        closeChildren: () => dropdown?.closeChildren(),
        closeAll: () => dropdown?.closeAllParents(),
    };
}
