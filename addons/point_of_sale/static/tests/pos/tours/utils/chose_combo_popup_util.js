export function isShown() {
    return [
        {
            content: "Chose combo popup is shown",
            trigger: ".chose-combo-popup",
        },
    ];
}

export function apply(option) {
    return [
        {
            content: `Apply combo option ${option}`,
            trigger: `.chose-combo-popup .combo-list .combo-item:contains("${option}") .apply-combo-btn`,
            run: "click",
        },
    ];
}

export function isOptionShown(option) {
    return [
        {
            content: `option ${option} is shown`,
            trigger: `.chose-combo-popup .combo-list .combo-item:contains("${option}")`,
        },
    ];
}
