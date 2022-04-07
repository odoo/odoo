/** @odoo-module **/

import { localization } from "@web/core/l10n/localization";
const { useRef, useEffect } = owl;

/**
 * This hook replaces the decimal separator of the numpad decimal key
 * by the decimal separator from the user's language setting when user
 * edits an input. The input is found using a t-ref="numpadDecimal"
 * reference in the current component. It can be placed directly on an
 * input or an element containing multiple inputs that require the
 * behavior
 */
export function useNumpadDecimal() {
    const decimalPoint = localization.decimalPoint;
    const listeners = [];
    let ref = useRef("numpadDecimal");
    const handler = (ev) => {
        if (
            !([".", ","].includes(ev.key) && ev.code === "NumpadDecimal") ||
            ev.key === decimalPoint
        ) {
            return;
        }
        ev.preventDefault();
        ev.target.value += decimalPoint;
    };
    useEffect(
        (el) => {
            if (el) {
                const inputs = el.nodeName === "INPUT" ? [el] : el.querySelectorAll("input");
                inputs.forEach((input) => {
                    listeners.push(input);
                    input.addEventListener("keydown", handler);
                });
            }
            return () => {
                listeners.forEach((input) => input.removeEventListener("keydown", handler));
            };
        },
        () => [ref.el]
    );
}
