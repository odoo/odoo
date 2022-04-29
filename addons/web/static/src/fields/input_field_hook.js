/** @odoo-module **/

const { useEffect, useRef } = owl;

/**
 * This hook is meant to be used by field components that use an input or
 * textarea to edit their value. Its purpose is to prevent that value from being
 * erased by an update of the model (typically coming from an onchange) when the
 * user is currently editing it.
 *
 * @param {() => string} getValue a function that returns the value to write in
 *   the input, if the user isn't currently editing it
 * @param {string} [refName="input"] the ref of the input/textarea
 */
export function useInputField(getValue, refName = "input") {
    const inputRef = useRef(refName);
    let isDirty = false;
    let lastSetValue = null;
    function onInput(ev) {
        isDirty = ev.target.value !== lastSetValue;
    }
    function onChange(ev) {
        lastSetValue = ev.target.value;
        isDirty = false;
    }
    useEffect(
        (inputEl) => {
            if (inputEl) {
                inputEl.addEventListener("input", onInput);
                inputEl.addEventListener("change", onChange);
                return () => {
                    inputEl.removeEventListener("input", onInput);
                    inputEl.removeEventListener("change", onChange);
                };
            }
        },
        () => [inputRef.el]
    );
    useEffect(() => {
        if (inputRef.el && !isDirty) {
            inputRef.el.value = getValue();
            lastSetValue = inputRef.el.value;
        }
    });
}
