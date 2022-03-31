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
    let ref = useRef("numpadDecimal");
    useEffect(
        (el) => {
            const handler = (ev, input) => {
                if (
                    !([".", ","].includes(ev.key) && ev.code === "NumpadDecimal") ||
                    ev.key === decimalPoint
                ) {
                    return;
                }
                ev.preventDefault();
                input.value += decimalPoint;
            };
            if (el) {
                const inputs = el.nodeName === "INPUT" ? [el] : el.querySelectorAll("input");
                inputs.forEach((input) => {
                    input.addEventListener("keydown", (e) => handler(e, input));
                    return () => input.removeEventListener("keydown", (e) => handler(e, input));
                });
            }
        },
        () => [ref.el]
    );
}
