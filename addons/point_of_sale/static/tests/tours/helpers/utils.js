/** @odoo-module */

import { simulateBarCode } from "@barcodes/../tests/helpers";

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

export function negate(selector, parent = "body") {
    return `${parent}:not(:has(${selector}))`;
}
export function negateStep(step) {
    return {
        ...step,
        trigger: negate(step.trigger),
    };
}

<<<<<<< saas-17.2
export function refresh() {
    return {
        content: `refresh page`,
        trigger: "body",
        run: () => {
            window.location.reload();
        },
    };
}

export function elementDoesNotExist(selector) {
    return {
        content: `Check that element "${selector}" don't exist.`,
        trigger: negate(selector),
        isCheck: true,
    };
}

export function selectButton(name) {
    return {
        content: `Select button ${name}`,
        trigger: `button:contains("${name}")`,
    };
}
||||||| 6d0baa2194720188fe50e2a4a89ce6018c90c718
=======
export function selectButton(name) {
    return {
        content: `Select button ${name}`,
        trigger: `button:contains("${name}")`,
    };
}

>>>>>>> 92b18a1a5fcdf0214938683abf8566883af5e156
export function scan_barcode(barcode) {
    return [
        {
            content: `PoS model scan barcode '${barcode}'`,
            trigger: "body", // The element here does not really matter as long as it is present
            run: () => simulateBarCode([...barcode, "Enter"]),
        },
    ];
}
