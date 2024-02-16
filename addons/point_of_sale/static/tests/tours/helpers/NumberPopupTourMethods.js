import * as Numpad from "@point_of_sale/../tests/tours/helpers/NumpadTourMethods";

/**
 * Note: Maximum of 2 characters because NumberBuffer only allows 2 consecutive
 * fast inputs. Fast inputs is the case in tours.
 *
 * @param {String} keys space-separated input keys
 */
export function pressNumpad(keys) {
    return keys.split(" ").map((key) => Numpad.click(key, { mobile: false }));
}
export function enterValue(keys) {
    const numpadKeys = keys.split("").join(" ");
    return [...pressNumpad(numpadKeys), ...fillPopupValue(keys)];
}
export function fillPopupValue(keys) {
    return [
        {
            content: `'${keys}' inputed in the number popup`,
            trigger: ".value",
            in_modal: true,
            run: `text ${keys}`,
            mobile: true,
        },
    ];
}
export function isShown(val = "") {
    return [
        {
            content: `input shown is '${val}'`,
            trigger: `.value:contains("${val}")`,
            in_modal: true,
            run: () => {},
            mobile: false,
        },
    ];
}
