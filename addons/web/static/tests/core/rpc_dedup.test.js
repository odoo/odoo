// @ts-check

/**
 * Pure unit tests for rpc_dedup.js.
 *
 * Tests deduplication of concurrent RPC calls without OWL or DOM.
 */

import { describe, expect, test } from "@odoo/hoot";
import { buildKey, deduplicateRpc } from "@web/core/network/rpc_dedup";

// ---------------------------------------------------------------------------
// buildKey
// ---------------------------------------------------------------------------

describe("buildKey", () => {
    test("produces identical keys for identical inputs", () => {
        const k1 = buildKey("/web/dataset/call_kw", { model: "res.partner" });
        const k2 = buildKey("/web/dataset/call_kw", { model: "res.partner" });
        expect(k1).toBe(k2);
    });

    test("produces different keys for different URLs", () => {
        const k1 = buildKey("/web/dataset/call_kw", { model: "res.partner" });
        const k2 = buildKey("/web/dataset/search_read", { model: "res.partner" });
        expect(k1).not.toBe(k2);
    });

    test("produces different keys for different params", () => {
        const k1 = buildKey("/rpc", { ids: [1] });
        const k2 = buildKey("/rpc", { ids: [2] });
        expect(k1).not.toBe(k2);
    });

    test("handles null params", () => {
        const k1 = buildKey("/rpc", null);
        const k2 = buildKey("/rpc", null);
        expect(k1).toBe(k2);
    });
});

// ---------------------------------------------------------------------------
// deduplicateRpc
// ---------------------------------------------------------------------------

describe("deduplicateRpc", () => {
    test("deduplicates identical concurrent requests", async () => {
        let callCount = 0;
        const rpc = deduplicateRpc(async (url, params) => {
            callCount++;
            return { data: params.id };
        });

        const p1 = rpc("/read", { id: 1 });
        const p2 = rpc("/read", { id: 1 });
        const p3 = rpc("/read", { id: 1 });

        const [r1, r2, r3] = await Promise.all([p1, p2, p3]);

        expect(callCount).toBe(1);
        expect(r1).toEqual({ data: 1 });
        expect(r2).toEqual({ data: 1 });
        expect(r3).toEqual({ data: 1 });
    });

    test("does not deduplicate different requests", async () => {
        let callCount = 0;
        const rpc = deduplicateRpc(async (url, params) => {
            callCount++;
            return { data: params.id };
        });

        const p1 = rpc("/read", { id: 1 });
        const p2 = rpc("/read", { id: 2 });

        await Promise.all([p1, p2]);

        expect(callCount).toBe(2);
    });

    test("allows new request after previous one settles", async () => {
        let callCount = 0;
        const rpc = deduplicateRpc(async (url, params) => {
            callCount++;
            return { data: params.id };
        });

        // First request
        await rpc("/read", { id: 1 });
        expect(callCount).toBe(1);

        // Second request with same params — should fire a new RPC
        await rpc("/read", { id: 1 });
        expect(callCount).toBe(2);
    });

    test("cleans up after rejection", async () => {
        let callCount = 0;
        const rpc = deduplicateRpc(async () => {
            callCount++;
            throw new Error("RPC failed");
        });

        // First call — fails
        try {
            await rpc("/fail", {});
        } catch {
            // expected
        }
        expect(callCount).toBe(1);

        // Second call — should fire a new RPC (not return cached rejection)
        try {
            await rpc("/fail", {});
        } catch {
            // expected
        }
        expect(callCount).toBe(2);
    });

    test("concurrent calls share rejection", async () => {
        let callCount = 0;
        const rpc = deduplicateRpc(async () => {
            callCount++;
            throw new Error("RPC failed");
        });

        const p1 = rpc("/fail", {});
        const p2 = rpc("/fail", {});

        let errors = 0;
        try {
            await p1;
        } catch {
            errors++;
        }
        try {
            await p2;
        } catch {
            errors++;
        }

        expect(callCount).toBe(1);
        expect(errors).toBe(2);
    });

    test("returns the same promise object for deduped calls", async () => {
        const rpc = deduplicateRpc(async () => "result");

        const p1 = rpc("/same", { x: 1 });
        const p2 = rpc("/same", { x: 1 });

        // Same promise reference
        expect(p1).toBe(p2);

        await Promise.all([p1, p2]);
    });
});
