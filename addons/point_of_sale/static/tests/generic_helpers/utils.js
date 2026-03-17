/* global posmodel */

import { patch } from "@web/core/utils/patch";
import { TourHelpers } from "@web_tour/js/tour_automatic/tour_helpers";

patch(TourHelpers.prototype, {
    async scan(barcode) {
        odoo.__WOWL_DEBUG__.root.env.services.barcode.bus.trigger("barcode_scanned", { barcode });
        await new Promise((resolve) => requestAnimationFrame(resolve));
    },
});

export function negate(selector, parent = "body") {
    return `${parent}:not(:has(${selector}))`;
}
export function run(run, content = "run function", expectUnloadPage = false) {
    return { content, trigger: "body", run, expectUnloadPage };
}
export function scan_barcode(barcode) {
    return [
        {
            content: `PoS model scan barcode '${barcode}'`,
            trigger: "body", // The element here does not really matter as long as it is present
            run: ({ scan }) => scan(barcode),
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
    return run(
        async () => {
            await new Promise((resolve) => {
                const checkTransaction = () => {
                    const activeTransactions = posmodel.data.indexedDB.activeTransactions;
                    if (activeTransactions.size === 0) {
                        window.location.reload();
                        resolve();
                    } else {
                        setTimeout(checkTransaction, 100);
                    }
                };

                setTimeout(() => {
                    checkTransaction();
                }, 305);
                setTimeout(() => {
                    const activeTx = posmodel.data.indexedDB.activeTransactions;
                    const storeNames = Array.from(activeTx).flatMap((tx) =>
                        Array.from(tx.objectStoreName)
                    );
                    const uniqueStores = [...new Set(storeNames)].join(", ");
                    throw new Error(
                        `Timeout waiting indexedDB for transactions to finish. Stores open: [${uniqueStores}]`
                    );
                }, 2000);
            });
        },
        "refresh page",
        true
    );
}
export function elementDoesNotExist(selector) {
    return {
        content: `Check that element "${selector}" don't exist.`,
        trigger: negate(selector),
    };
}

export function assertCurrentOrderDirty(dirty = true) {
    return {
        trigger: "body",
        run() {
            if (posmodel.getOrder().isDirty() !== dirty) {
                throw new Error("Order should be " + (dirty ? "dirty" : "not dirty"));
            }
        },
    };
}
