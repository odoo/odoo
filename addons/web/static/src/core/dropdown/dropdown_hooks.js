import { useEnv, useState } from "@odoo/owl";
import { DROPDOWN_NESTING } from "@web/core/dropdown/_behaviours/dropdown_nesting";

/**
 * @typedef {Object} DropdownState
 * @property {() => void} open
 * @property {() => void} close
 * @property {boolean} isOpen
 */

/**
 * Hook used to interact with the Dropdown state.
 * In order to use it, pass the returned state to the dropdown component, i.e.:
 *  <Dropdown state="dropdownState" ...>...</Dropdown>
 * @param {Object} callbacks
 * @param {Function} callbacks.onOpen
 * @param {Function} callbacks.onClose
 * @returns {DropdownState}
 */
export function useDropdownState({ onOpen, onClose } = {}) {
    const state = useState({
        isOpen: false,
        open: () => {
            state.isOpen = true;
            onOpen?.();
        },
        close: () => {
            state.isOpen = false;
            onClose?.();
        },
    });
    return state;
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
