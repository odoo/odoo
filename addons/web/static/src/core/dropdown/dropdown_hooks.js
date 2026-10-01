import { proxy } from "@odoo/owl";
import { useEnv } from "@web/owl2/utils";
import { DROPDOWN_NESTING } from "@web/core/dropdown/_behaviours/dropdown_nesting";

/**
 * Represents the state of a dropdown.
 * In order to use it, pass the state instance to the dropdown component, i.e.:
 *  <Dropdown state="dropdownState" ...>...</Dropdown>
 * @param {Object} callbacks
 * @param {Function} callbacks.onOpen
 * @param {Function} callbacks.onClose
 */
export class DropdownState {
    isOpen = false;
    constructor({ onOpen, onClose } = {}) {
        this._onOpen = onOpen;
        this._onClose = onClose;
        return proxy(this);
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
    return proxy(new DropdownState({ onOpen, onClose }));
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
