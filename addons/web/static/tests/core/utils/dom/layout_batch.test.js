// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { microTick } from "@odoo/hoot-mock";
import { flushLayoutBatch, measure, mutate } from "@web/core/utils/dom/layout_batch";

describe.current.tags("headless");

test("reads run before writes, in a microtask, in queue order", async () => {
    const steps = [];
    mutate(() => steps.push("write 1"));
    measure(() => steps.push("read 1"));
    mutate(() => steps.push("write 2"));
    measure(() => steps.push("read 2"));
    expect(steps).toEqual([]);
    await microTick();
    expect(steps).toEqual(["read 1", "read 2", "write 1", "write 2"]);
});

test("a read that queues a write runs it in the same flush; a write that queues a read starts a second round", async () => {
    const steps = [];
    measure(() => {
        steps.push("read");
        mutate(() => {
            steps.push("write");
            measure(() => steps.push("read again"));
        });
    });
    await microTick();
    expect(steps).toEqual(["read", "write", "read again"]);
});

test("flushLayoutBatch drains both queues synchronously", () => {
    const steps = [];
    measure(() => steps.push("read"));
    mutate(() => steps.push("write"));
    flushLayoutBatch();
    expect(steps).toEqual(["read", "write"]);
});

test("one callback's error does not stop the others, and is rethrown after the flush", () => {
    const steps = [];
    measure(() => {
        throw new Error("boom");
    });
    measure(() => steps.push("read"));
    mutate(() => steps.push("write"));
    expect(() => flushLayoutBatch()).toThrow("boom");
    expect(steps).toEqual(["read", "write"]);
});
