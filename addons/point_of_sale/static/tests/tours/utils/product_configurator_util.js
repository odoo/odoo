export function pickRadio(name) {
    return [
        {
            content: `picking radio attribute with name ${name}`,
            trigger: `.modal .attribute-name-cell:contains('${name}') input`,
            run: "click",
        },
    ];
}
export function pickSelect(name) {
    return [
        {
            content: `picking select attribute with name ${name}`,
            trigger: `.modal .configurator_select:has(option:contains('${name}'))`,
            run: `select ${name}`,
        },
    ];
}
export function pickColor(name) {
    return [
        {
            content: `picking color attribute with name ${name}`,
            trigger: `.modal .configurator_color[data-color='${name}']`,
            run: "click",
        },
    ];
}
export function fillCustomAttribute(value) {
    return [
        {
            content: `filling custom attribute with value ${value}`,
            trigger: `.modal .custom_value`,
            run: `edit ${value}`,
        },
    ];
}

export function numberRadioOptions(number) {
    return [
        {
            trigger: `.attribute-name-cell`,
            run: () => {
                const radio_options = document.querySelectorAll(".attribute-name-cell").length;
                if (radio_options !== number) {
                    throw new Error(`Expected ${number} radio options, got ${radio_options}`);
                }
            },
        },
    ];
}

export function isOptionShown(option) {
    return [
        {
            content: `option ${option} is shown`,
            trigger: `.form-check-label:contains('${option}')`,
        },
    ];
}
