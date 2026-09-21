/* global posmodel */

/**
 * @param {string[]} chars keys to emit, e.g. [..."0100100", "Enter"]
 */
function simulateBarCode(chars) {
    for (const char of chars) {
        document.body.dispatchEvent(
            new KeyboardEvent("keydown", {
                key: char,
                bubbles: true,
                cancelable: true,
            }),
        );
    }
}

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
            trigger: "body",
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
    return run(
        async () => {
            await new Promise((resolve) => {
                const checkTransaction = () => {
                    const activeTransactions =
                        posmodel.data.indexedDB.activeTransactions;
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
                        Array.from(tx.objectStoreName),
                    );
                    const uniqueStores = [...new Set(storeNames)].join(", ");
                    throw new Error(
                        `Timeout waiting indexedDB for transactions to finish. Stores open: [${uniqueStores}]`,
                    );
                }, 2000);
            });
        },
        "refresh page",
        true,
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
