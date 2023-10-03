/** @odoo-module */

import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";

import { useEffect, useRef } from "@odoo/owl";

/**
 * This hook is meant to be used with an input or textarea. Its purpose is to
 * prevent the value from being erased by an update of the props (a change
 * typically coming from the server) when the user is currently editing it.
 *
 * @param {Object} params
 * @param {() => string} params.getValue a function that returns the value to write in
 *   the input, if the user isn't currently editing it
 * @param {(value: string) => void} params.onChange a function to call when the input is changed
 * @param {Object} [params.ref] a ref to the input/textarea
 * @param {string} [params.refName="input"] the name of the ref of the input/textarea
 */
export function useInputHook(params) {
    const inputRef = params.ref || useRef(params.refName || "input");

    let isDirty = false;

    /**
     * When a user types, we need to set the input as dirty.
     */
    function onInput() {
        isDirty = true;
    }

    /**
     * On blur, we consider the input no longer dirty.
     */
    function onChange(ev) {
        isDirty = false;
        params.onChange(ev.target.value);
    }
    function onKeydown(ev) {
        const hotkey = getActiveHotkey(ev);
        if (["enter", "tab", "shift+tab"].includes(hotkey)) {
            params.onChange(ev.target.value);
        }
    }

    useEffect(
        (inputEl) => {
            if (inputEl) {
                inputEl.addEventListener("input", onInput);
                inputEl.addEventListener("change", onChange);
                inputEl.addEventListener("keydown", onKeydown);
                return () => {
                    inputEl.removeEventListener("input", onInput);
                    inputEl.removeEventListener("change", onChange);
                    inputEl.removeEventListener("keydown", onKeydown);
                };
            }
        },
        () => [inputRef.el]
    );

    /**
     * Sometimes, a patch can happen with possible a new value for the input
     * If the user was typing a new value (isDirty) we need to do nothing.
     * If it is not such a case, we update the input with the new value.
     */
    useEffect(() => {
        if (inputRef.el && !isDirty) {
            inputRef.el.value = params.getValue();
        }
    });

    return inputRef;
}
