import { Deferred, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { makeActionAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";

test("canceling an action resolves without a saved record", async () => {
    let options;
    const action = {
        doAction: async (request, args) => {
            options = args;
        },
    };
    const result = makeActionAwaitable(action, "edit");
    await options.onClose();
    expect(await result).toBe(undefined);
});

test("saving keeps the record when the close callback runs synchronously", async () => {
    let options;
    const record = { resId: 4 };
    const action = {
        async doAction(request, args) {
            if (request === "edit") {
                options = args;
            } else {
                await options.onClose?.();
            }
        },
    };
    const result = makeActionAwaitable(action, "edit");
    await options.props.onSave(record);
    expect(await result).toBe(record);
});

for (const phase of ["open", "close"]) {
    test(`an asynchronous ${phase} failure rejects the waiting caller`, async () => {
        let options;
        const error = new Error(`${phase} failed`);
        const action = {
            async doAction(request, args) {
                if (request === "edit" && phase === "close") {
                    options = args;
                    return;
                }
                throw error;
            },
        };
        const result = makeActionAwaitable(action, "edit").catch((reason) => reason);
        if (phase === "close") {
            await options.props.onSave({ resId: 4 });
        }
        expect(await result).toBe(error);
    });
}

test("closing preserves the supplied cleanup callback", async () => {
    let options;
    const action = {
        doAction: async (request, args) => {
            options = args;
        },
    };
    const result = makeActionAwaitable(action, "edit", {
        onClose: () => expect.step("cleanup"),
    });
    await options.onClose();
    expect(await result).toBe(undefined);
    expect.verifySteps(["cleanup"]);
});

test("save remains pending until close finishes, even after its onClose callback", async () => {
    const closeFinished = new Deferred();
    let options;
    const action = {
        async doAction(request, args) {
            if (request === "edit") {
                options = args;
            } else {
                await options.onClose();
                await closeFinished;
            }
        },
    };
    let settled = false;
    const record = { resId: 4 };
    const result = makeActionAwaitable(action, "edit").then((value) => {
        settled = true;
        return value;
    });
    const save = options.props.onSave(record);
    await animationFrame();
    expect(settled).toBe(false);
    closeFinished.resolve();
    await save;
    expect(await result).toBe(record);
});

test("a close failure after onClose still rejects the saved action", async () => {
    let options;
    const error = new Error("dialog removal failed");
    const action = {
        async doAction(request, args) {
            if (request === "edit") {
                options = args;
            } else {
                await options.onClose();
                throw error;
            }
        },
    };
    const result = makeActionAwaitable(action, "edit").catch((reason) => reason);
    await options.props.onSave({ resId: 4 });
    expect(await result).toBe(error);
});

test("a synchronous opening failure rejects the waiting caller", async () => {
    const error = new Error("action dispatch failed");
    const result = makeActionAwaitable(
        {
            doAction() {
                throw error;
            },
        },
        "edit",
    ).catch((reason) => reason);
    expect(await result).toBe(error);
});

test("cancel waits for supplied cleanup and propagates its failure", async () => {
    const cleanup = new Deferred();
    const error = new Error("cleanup failed");
    let options;
    const action = {
        doAction: async (request, args) => {
            options = args;
        },
    };
    let settled = false;
    const result = makeActionAwaitable(action, "edit", { onClose: () => cleanup })
        .catch((reason) => reason)
        .then((value) => {
            settled = true;
            return value;
        });
    const closing = options.onClose();
    await animationFrame();
    expect(settled).toBe(false);
    cleanup.reject(error);
    await closing;
    expect(await result).toBe(error);
});
