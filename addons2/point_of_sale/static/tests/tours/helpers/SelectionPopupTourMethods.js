/** @odoo-module */

export function clickItem(name) {
    return [
        {
            content: `click selection '${name}'`,
            trigger: `.selection-item:contains("${name}")`,
        },
    ];
}

export function hasSelectionItem(name) {
    return [
        {
            content: `selection popup has '${name}'`,
            trigger: `.selection-item:contains("${name}")`,
            run: () => {},
        },
    ];
}
export function isShown() {
    return [
        {
            content: "selection popup is shown",
            trigger: ".modal-dialog .popup-selection",
            run: () => {},
        },
    ];
}
