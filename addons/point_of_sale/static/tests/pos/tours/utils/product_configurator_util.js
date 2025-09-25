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

export function isUnavailable(option) {
    return [
        {
            content: `option ${option} is unavailable`,
            trigger: `.modal .attribute span.text-muted:contains('${option}')`,
        },
    ];
}

export function isAddDisabled() {
    return [
        {
            content: "Add button is disabled",
            trigger: ".modal .btn-primary.disabled",
        },
    ];
}

export function isAddEnabled() {
    return [
        {
            content: "Add button is enabled",
            trigger: ".modal .btn-primary:not(.disabled)",
        },
    ];
}

export function checkImageVariantVisible() {
    return [
        {
            content: `Check that the image is displayed`,
            trigger: `.configurator_color.rounded-3`,
        },
    ];
}

export function checkImageVariantTextVisible(variantName) {
    return [
        {
            content: `Check that the variant is visible`,
            trigger: `.text-center.mt-2.small span:contains("${variantName}")`,
        },
    ];
}

export function checkImagePriceExtraVisible(price) {
    return [
        {
            content: `Check that the extra price is displayed`,
            trigger: `.price_extra.px-2.py-1.rounded-pill.text-bg-info:contains("${price}")`,
        },
    ];
}
