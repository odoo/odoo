/** @odoo-module **/

import { useEffect } from "./effect_hook";

const { useComponent } = owl.hooks;

// -----------------------------------------------------------------------------
// Hook functions
// -----------------------------------------------------------------------------

/**
 * Focus a given selector as soon as it appears in the DOM and if it was not
 * displayed before. If the selected target is an input|textarea, set the selection
 * at the end.
 *
 * @param {Object} [params]
 * @param {string} [params.selector='autofocus'] default: select the first element
 *                 with an `autofocus` attribute.
 * @returns {Function} function that forces the focus on the next update if visible.
 */
export function useAutofocus(params = {}) {
    const comp = useComponent();
    // Prevent autofocus in mobile
    if (comp.env.isSmall) {
        return () => {};
    }
    const selector = params.selector || "[autofocus]";
    let forceFocusCount = 0;
    useEffect(function autofocus(target) {
        if (target) {
            target.focus();
            if (["INPUT", "TEXTAREA"].includes(target.tagName)) {
                const inputEl = target;
                inputEl.selectionStart = inputEl.selectionEnd = inputEl.value.length;
            }
        }
    }, () => [comp.el.querySelector(selector), forceFocusCount]);

    return function focusOnUpdate() {
        forceFocusCount++; // force the effect to rerun on next patch
    };
}
