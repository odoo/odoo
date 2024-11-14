import * as Numpad from "@point_of_sale/../tests/tours/utils/numpad_util";

export function enterValue(keys) {
    return Numpad.enterValue(keys).map((step) => {
        step.trigger = `.modal ${step.trigger}`;
        return {
            ...step,
        };
    });
}
export function isShown(val = "") {
    return [
        {
            content: `input shown is '${val}'`,
            trigger: `.modal .value:contains("${val}")`,
        },
    ];
}
