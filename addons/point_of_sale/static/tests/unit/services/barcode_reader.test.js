import { Deferred, expect, microTick, test } from "@odoo/hoot";
import { BarcodeReader } from "@point_of_sale/app/services/barcode_reader_service";

function makeReader(gs1 = false) {
    return new BarcodeReader(
        {
            parse_barcode: (code) =>
                gs1 ? [{ type: "product", code }] : { type: "product", code },
        },
        { notification: { add: () => expect.step("unknown") } },
    );
}

test("closing the newest exclusive registration restores the preceding one", async () => {
    const reader = makeReader();
    reader.register({ product: () => expect.step("normal") });
    const closeFirst = reader.register({ product: () => expect.step("first") }, true);
    const closeSecond = reader.register({ product: () => expect.step("second") }, true);
    await reader.scan("1");
    closeSecond();
    await reader.scan("2");
    closeFirst();
    await reader.scan("3");
    expect.verifySteps(["second", "first", "normal"]);
});

test("disposing an older exclusive registration leaves the newest active", async () => {
    const reader = makeReader();
    const closeFirst = reader.register({ product: () => expect.step("first") }, true);
    reader.register({ product: () => expect.step("second") }, true);
    closeFirst();
    closeFirst();
    await reader.scan("1");
    expect.verifySteps(["second"]);
});

for (const synchronous of [false, true]) {
    test(`GS1 ${synchronous ? "throw" : "rejection"} waits for every started handler before the next scan`, async () => {
        const reader = makeReader(true);
        const pending = new Deferred();
        const failure = new Error("Handler failed");
        reader.register({
            gs1: ([barcode]) => (barcode.code === "first" ? pending : undefined),
        });
        reader.register({
            gs1: ([barcode]) => {
                if (barcode.code === "first") {
                    if (synchronous) {
                        throw failure;
                    }
                    return Promise.reject(failure);
                }
                expect.step("second scan");
            },
        });
        let settled = false;
        const first = reader.scan("first").catch((error) => {
            expect(error).toBe(failure);
            settled = true;
        });
        const second = reader.scan("second");
        for (let tick = 0; tick < 10; tick++) {
            await microTick();
        }
        expect.verifySteps([]);
        expect(settled).toBe(false);
        pending.resolve();
        await Promise.all([first, second]);
        expect(settled).toBe(true);
        expect.verifySteps(["second scan"]);
    });
}

test("normal barcode callbacks remain sequential", async () => {
    const reader = makeReader();
    const pending = new Deferred();
    reader.register({ product: () => pending });
    reader.register({ product: () => expect.step("second handler") });
    const scan = reader.scan("1");
    await microTick();
    expect.verifySteps([]);
    pending.resolve();
    await scan;
    expect.verifySteps(["second handler"]);
});

test("registering the same exclusive map twice gives independent cleanup handles", async () => {
    const reader = makeReader();
    const callbacks = { product: () => expect.step("exclusive") };
    const first = reader.register(callbacks, true);
    const second = reader.register(callbacks, true);
    first();
    first();
    await reader.scan("1");
    expect.verifySteps(["exclusive"]);
    second();
    expect(reader.exclusiveCbMap).toBe(null);
});

test("successful GS1 handlers still start concurrently", async () => {
    const reader = makeReader(true);
    const pending = new Deferred();
    reader.register({
        gs1: () => {
            expect.step("first handler");
            return pending;
        },
    });
    reader.register({ gs1: () => expect.step("second handler") });
    const scan = reader.scan("1");
    for (let tick = 0; tick < 10; tick++) {
        await microTick();
    }
    expect.verifySteps(["first handler", "second handler"]);
    pending.resolve();
    await scan;
});

test("GS1 dispatch does not defer handlers beyond registration cleanup", async () => {
    const reader = makeReader(true);
    const unregister = reader.register({ gs1: () => expect.step("handler") });
    const scan = reader.scan("1");
    queueMicrotask(() => {
        unregister();
        expect.step("disposed");
    });
    await scan;
    expect.verifySteps(["handler", "disposed"]);
});
