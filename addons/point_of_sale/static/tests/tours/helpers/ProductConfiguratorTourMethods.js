/** @odoo-module */

export function pickRadio(name) {
    return [
        {
            content: `picking radio attribute with name ${name}`,
            trigger: `.product-configurator-popup div.attribute-name-cell:contains('${name}') input`,
        },
    ];
}
export function pickSelect(name) {
    return [
        {
            content: `picking select attribute with name ${name}`,
            trigger: `.product-configurator-popup .configurator_select:has(option:contains('${name}'))`,
            run: `text ${name}`,
        },
    ];
}
export function pickColor(name) {
    return [
        {
            content: `picking color attribute with name ${name}`,
            trigger: `.product-configurator-popup .configurator_color[data-color='${name}']`,
        },
    ];
}
export function fillCustomAttribute(value) {
    return [
        {
            content: `filling custom attribute with value ${value}`,
            trigger: `.product-configurator-popup .custom_value`,
            run: `text ${value}`,
        },
    ];
}
export function confirmAttributes() {
    return [
        {
            content: `confirming product configuration`,
            trigger: `.product-configurator-popup .button.confirm`,
        },
    ];
}
export function cancelAttributes() {
    return [
        {
            content: `canceling product configuration`,
            trigger: `.product-configurator-popup .button.cancel`,
        },
    ];
}

export function isShown() {
    return [
        {
            content: "product configurator is shown",
            trigger: ".product-configurator-popup:not(:has(.d-none))",
            run: () => {},
        },
    ];
}

export function numberRadioOptions(number) {
    return [
        {
            trigger: `.product-configurator-popup .attribute-name-cell`,
            run: () => {
                const radio_options = $('.product-configurator-popup .attribute-name-cell').length;
                if (radio_options !== number) {
                    throw new Error(`Expected ${number} radio options, got ${radio_options}`);
                }
            }
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
