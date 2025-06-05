import * as Numpad from "@point_of_sale/../tests/generic_helpers/numpad_util";

export function enterValue(keys) {
    return Numpad.enterValue(keys).map((step) => ({
        ...step,
        trigger: `.modal ${step.trigger}`,
    }));
}
export function isShown(val = "") {
    return [
        {
            content: `input shown is '${val}'`,
            trigger: `.modal .value:contains("${val}")`,
        },
    ];
}

export function clickType(name) {
    return {
        content: `click numpad button: ${name}`,
        trigger: `.modal .number-popup-types .number-popup-type-${name}`,
        run: "click",
    };
}

export function hasTypeSelected(name) {
    return {
        content: `check if --${name}-- type is selected`,
        trigger: `.modal .number-popup-types .number-popup-type-${name}.btn-primary`,
    };
}
