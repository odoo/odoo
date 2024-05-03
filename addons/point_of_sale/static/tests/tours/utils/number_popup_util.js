import * as Numpad from "@point_of_sale/../tests/tours/utils/numpad_util";

export function enterValue(keys) {
    return Numpad.enterValue(keys).map((step) => ({
        ...step,
        in_modal: true,
    }));
}
export function isShown(val = "") {
    return [
        {
            content: `input shown is '${val}'`,
            trigger: `.value:contains("${val}")`,
            in_modal: true,
            run: () => {},
        },
    ];
}
