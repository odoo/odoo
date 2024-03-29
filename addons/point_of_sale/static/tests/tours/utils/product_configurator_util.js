/** @odoo-module */

export function pickRadio(name) {
    return [
        {
            content: `picking radio attribute with name ${name}`,
            trigger: `.attribute-name-cell:contains('${name}') input`,
            in_modal: true,
        },
    ];
}
export function pickSelect(name) {
    return [
        {
            content: `picking select attribute with name ${name}`,
            trigger: `.configurator_select:has(option:contains('${name}'))`,
            run: `select ${name}`,
            in_modal: true,
        },
    ];
}
export function pickColor(name) {
    return [
        {
            content: `picking color attribute with name ${name}`,
            trigger: `.configurator_color[data-color='${name}']`,
            in_modal: true,
        },
    ];
}
export function fillCustomAttribute(value) {
    return [
        {
            content: `filling custom attribute with value ${value}`,
            trigger: `.custom_value`,
            run: `edit ${value}`,
            in_modal: true,
        },
    ];
}

export function isOptionShown(option) {
    return [
        {
            content: `option ${option} is shown`,
            trigger: `.form-check-label:contains('${option}')`,
            run: () => {},
        },
    ];
}
