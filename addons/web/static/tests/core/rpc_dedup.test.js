// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { getKey } from "@web/core/network/rpc_dedup";

describe.current.tags("headless");

describe("getKey", () => {
    test("sparse arrays preserve their wire length and null slots", () => {
        const partial = [1, 2, 3];
        delete partial[1];
        for (const ids of [Array(1), Array(3), partial]) {
            expect(getKey("/rpc", { ids })).toBe(
                getKey("/rpc", { ids: JSON.parse(JSON.stringify(ids)) }),
            );
            expect(getKey("/rpc", { ids })).not.toBe(getKey("/rpc", { ids: [] }));
        }
    });

    test("boxed primitives have the same key as their wire values", () => {
        for (const value of [Object(1), Object(2), Object(false), Object("text")]) {
            expect(getKey("/rpc", { value })).toBe(
                getKey("/rpc", { value: JSON.parse(JSON.stringify(value)) }),
            );
        }
        expect(getKey("/rpc", { value: Object(1) })).not.toBe(
            getKey("/rpc", { value: Object(2) }),
        );
    });

    test("toJSON receives the containing property or array index", () => {
        const value = { toJSON: (key) => key };
        const params = { value, array: [value], nested: { other: value } };
        expect(getKey("/rpc", params)).toBe(
            getKey("/rpc", JSON.parse(JSON.stringify(params))),
        );
    });

    test("shared references serialize but circular references reject", () => {
        const shared = { z: 1, a: 2 };
        expect(getKey("/rpc", [shared, shared])).toBe(
            getKey("/rpc", [
                { a: 2, z: 1 },
                { a: 2, z: 1 },
            ]),
        );
        const circular = {};
        circular.self = circular;
        expect(() => getKey("/rpc", circular)).toThrow(TypeError);
    });

    test("produces identical keys for identical inputs", () => {
        const k1 = getKey("/web/dataset/call_kw", { model: "res.partner" });
        const k2 = getKey("/web/dataset/call_kw", { model: "res.partner" });
        expect(k1).toBe(k2);
    });

    test("produces different keys for different URLs", () => {
        const k1 = getKey("/web/dataset/call_kw", { model: "res.partner" });
        const k2 = getKey("/web/dataset/search_read", { model: "res.partner" });
        expect(k1).not.toBe(k2);
    });

    test("produces different keys for different params", () => {
        const k1 = getKey("/rpc", { ids: [1] });
        const k2 = getKey("/rpc", { ids: [2] });
        expect(k1).not.toBe(k2);
    });

    test("handles null params", () => {
        const k1 = getKey("/rpc", null);
        const k2 = getKey("/rpc", null);
        expect(k1).toBe(k2);
    });

    test("is insensitive to object key insertion order at every depth", () => {
        const k1 = getKey("/rpc", {
            model: "res.partner",
            kwargs: { context: { lang: "en", tz: "utc", uid: 7 } },
        });
        const k2 = getKey("/rpc", {
            kwargs: { context: { uid: 7, tz: "utc", lang: "en" } },
            model: "res.partner",
        });
        expect(k1).toBe(k2);
    });

    test("mirrors JSON.stringify semantics for the payload domain", () => {
        expect(getKey("/rpc", { a: undefined, b: 1 })).toBe(getKey("/rpc", { b: 1 }));
        const withHole = getKey("/rpc", { ids: [1, undefined, 3] });
        expect(withHole).toInclude("[1,null,3]");
        const k = getKey("/rpc", { when: { toJSON: () => "2026-06-09" } });
        expect(k).toInclude('"when":"2026-06-09"');
        expect(getKey("/rpc", { ids: [2, 1] })).not.toBe(
            getKey("/rpc", { ids: [1, 2] }),
        );
        const parsed = JSON.parse(getKey("/web/x", { model: "res.users" }));
        expect(parsed.params.model).toBe("res.users");
        expect(parsed.url).toBe("/web/x");
    });
});
