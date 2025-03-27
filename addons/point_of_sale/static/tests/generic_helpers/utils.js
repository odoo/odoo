/* global posmodel */

import { simulateBarCode } from "@barcodes/../tests/legacy/helpers";

export function negate(selector, parent = "body") {
    return `${parent}:not(:has(${selector}))`;
}
export function run(run, content = "run function") {
    return { content, trigger: "body", run };
}
export function scan_barcode(barcode) {
    return [
        {
            content: `PoS model scan barcode '${barcode}'`,
            trigger: "body", // The element here does not really matter as long as it is present
            run: () => {
                simulateBarCode([...barcode, "Enter"]);
            },
        },
    ];
}
export function negateStep(step) {
    return {
        ...step,
        content: `Check that: ---${step.content}--- is not true`,
        trigger: negate(step.trigger),
    };
}
export function refresh() {
    return run(async () => {
        await new Promise((resolve) => {
            const checkTransaction = () => {
                const activeTransactions = posmodel.data.indexedDB.activeTransactions;
                if (activeTransactions <= 0) {
                    window.location.reload();
                    resolve();
                } else {
                    setTimeout(checkTransaction, 100);
                }
            };

            checkTransaction();
        });
    }, "refresh page");
}
export function elementDoesNotExist(selector) {
    return {
        content: `Check that element "${selector}" don't exist.`,
        trigger: negate(selector),
    };
}
