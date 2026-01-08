/** @odoo-module */

import { simulateBarCode } from "@barcodes/../tests/helpers"

export function inLeftSide(steps) {
    return [
        {
            content: "click review button",
            trigger: ".btn-switchpane.review-button",
            mobile: true,
        },
        ...[steps].flat(),
        {
            content: "go back to the products",
            trigger: ".pos-rightheader .floor-button",
            mobile: true,
        },
    ];
}

export function negate(selector) {
    return `body:not(:has(${selector}))`;
}

export function negateStep(step) {
    return {
        ...step,
        trigger: negate(step.trigger),
    };
}

export function selectButton(name) {
    return {
        content: `Select button ${name}`,
        trigger: `button:contains("${name}")`,
    };
}

export function scan_barcode(barcode) {
    return [
        {
            content: `PoS model scan barcode '${barcode}'`,
            trigger: "body", // The element here does not really matter as long as it is present
            run: () => {
                simulateBarCode([...barcode, "Enter"])
            },
        },
    ];
}
