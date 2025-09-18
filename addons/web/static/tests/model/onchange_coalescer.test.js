// @ts-check

/**
 * Pure unit tests for onchange_coalescer.js.
 *
 * Tests the debounce/coalescing logic without OWL, DOM, or mock server.
 */

import { describe, expect, test } from "@odoo/hoot";
import { createOnchangeCoalescer } from "@web/model/relational_model/onchange_coalescer";

describe("createOnchangeCoalescer", () => {
    test("coalesces multiple rapid changes into one call", async () => {
        let callCount = 0;
        let lastChanges = null;
        const coalescer = createOnchangeCoalescer(
            async (changes) => {
                callCount++;
                lastChanges = changes;
                return { result: "ok" };
            },
            { delay: 10 },
        );

        // Queue three rapid changes to the same field
        coalescer.queue("name", "J");
        coalescer.queue("name", "Jo");
        const result = await coalescer.queue("name", "John");

        // Wait for the debounce to fire
        await new Promise((resolve) => setTimeout(resolve, 50));

        expect(callCount).toBe(1);
        expect(lastChanges).toEqual({ name: "John" });
        expect(result).toEqual({ result: "ok" });
    });

    test("coalesces changes to different fields", async () => {
        let lastChanges = null;
        const coalescer = createOnchangeCoalescer(
            async (changes) => {
                lastChanges = changes;
                return changes;
            },
            { delay: 10 },
        );

        coalescer.queue("name", "Alice");
        coalescer.queue("email", "alice@example.com");

        await new Promise((resolve) => setTimeout(resolve, 50));

        expect(lastChanges).toEqual({
            name: "Alice",
            email: "alice@example.com",
        });
    });

    test("later values overwrite earlier ones for the same field", async () => {
        let lastChanges = null;
        const coalescer = createOnchangeCoalescer(
            async (changes) => {
                lastChanges = changes;
                return {};
            },
            { delay: 10 },
        );

        coalescer.queue("amount", 10);
        coalescer.queue("amount", 20);
        coalescer.queue("amount", 30);

        await new Promise((resolve) => setTimeout(resolve, 50));

        expect(lastChanges).toEqual({ amount: 30 });
    });

    test("flush() evaluates immediately without waiting for timer", async () => {
        let callCount = 0;
        const coalescer = createOnchangeCoalescer(
            async (changes) => {
                callCount++;
                return changes;
            },
            { delay: 5000 }, // Very long delay
        );

        coalescer.queue("name", "Bob");
        const result = await coalescer.flush();

        expect(callCount).toBe(1);
        expect(result).toEqual({ name: "Bob" });
    });

    test("flush() returns empty object when nothing is pending", async () => {
        const coalescer = createOnchangeCoalescer(
            async () => ({ should: "not be called" }),
            { delay: 10 },
        );

        const result = await coalescer.flush();
        expect(result).toEqual({});
    });

    test("pending is null when no changes are queued", () => {
        const coalescer = createOnchangeCoalescer(async () => ({}));
        expect(coalescer.pending).toBe(null);
    });

    test("pending reflects queued changes", () => {
        const coalescer = createOnchangeCoalescer(async () => ({}), {
            delay: 5000,
        });

        coalescer.queue("name", "test");
        expect(coalescer.pending).toEqual({ name: "test" });

        coalescer.queue("age", 25);
        expect(coalescer.pending).toEqual({ name: "test", age: 25 });
    });

    test("pending is cleared after flush", async () => {
        const coalescer = createOnchangeCoalescer(async () => ({}), {
            delay: 5000,
        });

        coalescer.queue("name", "test");
        await coalescer.flush();

        expect(coalescer.pending).toBe(null);
    });

    test("all queued promises resolve with the same result", async () => {
        const coalescer = createOnchangeCoalescer(
            async () => ({ server: "response" }),
            { delay: 10 },
        );

        const p1 = coalescer.queue("a", 1);
        const p2 = coalescer.queue("b", 2);
        const p3 = coalescer.queue("c", 3);

        const [r1, r2, r3] = await Promise.all([p1, p2, p3]);

        expect(r1).toEqual({ server: "response" });
        expect(r2).toEqual({ server: "response" });
        expect(r3).toEqual({ server: "response" });
    });

    test("separate batches after flush produce separate calls", async () => {
        let callCount = 0;
        const coalescer = createOnchangeCoalescer(
            async (changes) => {
                callCount++;
                return changes;
            },
            { delay: 10 },
        );

        coalescer.queue("name", "first");
        await coalescer.flush();

        coalescer.queue("name", "second");
        await coalescer.flush();

        expect(callCount).toBe(2);
    });
});
