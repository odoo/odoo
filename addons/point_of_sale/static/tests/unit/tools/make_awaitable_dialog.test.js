import { after, Deferred, expect, test } from "@odoo/hoot";
import { ask, makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { isolateLogging } from "@web/../tests/core/debug/logging_helpers";
import { enableLogging, getStats } from "@web/core/debug/debug_logger";

class Probe {}
for (const kind of ["payload", "confirmation"]) {
    function open(options) {
        const captured = {};
        const dialog = {
            add: (comp, props, opts) =>
                Object.assign(captured, { props, options: opts }),
        };
        captured.result =
            kind === "payload"
                ? makeAwaitable(dialog, Probe, {}, options)
                : ask(dialog, {}, options, Probe);
        return captured;
    }
    test(`${kind}: cancellation awaits caller cleanup and forwards arguments`, async () => {
        const cleanup = new Deferred();
        const args = [];
        const dialog = open({
            onClose: (value) => {
                args.push(value);
                return cleanup;
            },
        });
        let settled = false;
        dialog.result.then(() => {
            settled = true;
        });
        const closing = dialog.options.onClose("reason");
        await Promise.resolve();
        expect(args).toEqual(["reason"]);
        expect(settled).toBe(false);
        cleanup.resolve();
        await closing;
        expect(await dialog.result).toBe(kind === "payload" ? undefined : false);
    });
    test(`${kind}: cleanup failure reaches both close and pending caller`, async () => {
        const error = new Error("cleanup failed");
        const dialog = open({
            onClose: () => {
                throw error;
            },
        });
        const result = dialog.result.catch((reason) => reason);
        expect(
            await Promise.resolve()
                .then(() => dialog.options.onClose())
                .catch((reason) => reason),
        ).toBe(error);
        expect(await result).toBe(error);
    });
    test(`${kind}: cleanup failure after answering remains visible to the closer`, async () => {
        const error = new Error("late cleanup failed");
        const dialog = open({
            onClose: async () => {
                throw error;
            },
        });
        if (kind === "payload") {
            dialog.props.getPayload(0);
        } else {
            dialog.props.confirm();
        }
        expect(await dialog.result).toBe(kind === "payload" ? 0 : true);
        expect(
            await Promise.resolve()
                .then(() => dialog.options.onClose())
                .catch((reason) => reason),
        ).toBe(error);
        expect(await dialog.result).toBe(kind === "payload" ? 0 : true);
    });
    test(`${kind}: answering preserves its value and still runs close cleanup`, async () => {
        let cleaned = 0;
        const dialog = open({ onClose: () => cleaned++ });
        if (kind === "payload") {
            dialog.props.getPayload(0);
        } else {
            dialog.props.confirm();
        }
        expect(await dialog.result).toBe(kind === "payload" ? 0 : true);
        await dialog.options.onClose();
        expect(cleaned).toBe(1);
    });
}

test("payload then close records one completed performance span", async () => {
    after(isolateLogging());
    enableLogging("pos.dialog", { persist: false });
    let payload;
    let close;
    const result = makeAwaitable(
        {
            add(comp, props, options) {
                payload = props.getPayload;
                close = options.onClose;
            },
        },
        Probe,
    );
    payload(false);
    expect(await result).toBe(false);
    await close();
    expect(
        getStats().find(
            (row) => row.ns === "pos.dialog" && row.label === "makeAwaitable Probe",
        ).count,
    ).toBe(1);
});
