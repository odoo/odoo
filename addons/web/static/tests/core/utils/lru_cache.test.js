// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { LruCache } from "@web/core/utils/lru_cache";

describe.current.tags("headless");

test("capacity must be a nonnegative integer", () => {
    for (const limit of [-1, -Infinity, NaN, Infinity, 1.5]) {
        expect(() => new LruCache(limit)).toThrow(RangeError);
    }
});

test("invalid capacity reassignment preserves the previous capacity and entries", () => {
    const cache = new LruCache(1);
    cache.set("old", 1);
    for (const limit of [-1, -Infinity, NaN, Infinity, 1.5]) {
        expect(() => {
            cache.limit = limit;
        }).toThrow(RangeError);
        expect(cache.limit).toBe(1);
        expect(cache.peek("old")).toBe(1);
    }
    cache.set("new", 2);
    expect(cache.size).toBe(1);
    expect(cache.has("old")).toBe(false);
});

/**
 * @param {number} limit
 * @param {number} n
 * @returns {LruCache}
 */
function filled(limit, n = limit) {
    const cache = new LruCache(limit);
    for (let i = 0; i < n; i++) {
        cache.set(`k${i}`, i);
    }
    return cache;
}

/** @param {LruCache} cache */
const keys = (cache) => [...cache._entries.keys()];

test("insertion order is recency order, coldest first", () => {
    const cache = filled(3);
    expect(keys(cache)).toEqual(["k0", "k1", "k2"]);
    cache.get("k0");
    expect(keys(cache)).toEqual(["k1", "k2", "k0"], {
        message: "a hit moves to the back",
    });
});

test("a miss does not disturb the order and inserts nothing", () => {
    const cache = filled(3);
    expect(cache.get("absent")).toBe(undefined);
    expect(keys(cache)).toEqual(["k0", "k1", "k2"]);
    expect(cache.size).toBe(3);
});

test("touch refreshes without handing the value out", () => {
    const cache = filled(3);
    expect(cache.touch("k0")).toBe(undefined);
    expect(keys(cache)).toEqual(["k1", "k2", "k0"]);
});

test("writing past the limit evicts the coldest, not the oldest hit", () => {
    const cache = filled(3);
    cache.get("k0");
    cache.set("k3", 3);
    expect(keys(cache)).toEqual(["k2", "k0", "k3"], {
        message: "k1 was coldest once k0 had been read",
    });
    expect(cache.size).toBe(3);
});

test("re-setting a key refreshes it instead of growing the cache", () => {
    const cache = filled(3);
    cache.set("k0", 99);
    expect(cache.size).toBe(3);
    expect(keys(cache)).toEqual(["k1", "k2", "k0"]);
    expect(cache.get("k0")).toBe(99);
});

test("delete reports whether it removed anything, and frees the slot", () => {
    const cache = filled(3);
    expect(cache.delete("k1")).toBe(true);
    expect(cache.delete("k1")).toBe(false);
    expect(cache.size).toBe(2);
    cache.set("k3", 3);
    expect(keys(cache)).toEqual(["k0", "k2", "k3"]);
});

test("clear empties it without disturbing the limit", () => {
    const cache = filled(3);
    cache.clear();
    expect(cache.size).toBe(0);
    cache.set("a", 1);
    cache.set("b", 2);
    cache.set("c", 3);
    cache.set("d", 4);
    expect(cache.size).toBe(3);
});

test("lowering the limit on a full cache converges on the next write", () => {
    const cache = filled(10);
    expect(cache.size).toBe(10);

    cache.limit = 3;
    cache.set("new", 1);

    expect(cache.size).toBe(3, { message: "one write is enough to converge" });
    expect(keys(cache)).toEqual(["k8", "k9", "new"], {
        message: "and it drops the coldest entries, not arbitrary ones",
    });
});

test("a limit of zero keeps nothing", () => {
    const cache = new LruCache(0);
    cache.set("a", 1);
    expect(cache.size).toBe(0);
    expect(cache.get("a")).toBe(undefined);
    expect(cache.has("a")).toBe(false);
});

test("a stored undefined is indistinguishable from a miss, by design", () => {
    const cache = new LruCache(3);
    cache.set("a", undefined);
    expect(cache.get("a")).toBe(undefined);
    expect(cache.has("a")).toBe(true);
    expect(cache.size).toBe(1);
});

test("peek reads without refreshing recency", () => {
    const cache = filled(3);
    expect(cache.peek("k0")).toBe(0);
    expect(keys(cache)).toEqual(["k0", "k1", "k2"]);
    expect(cache.peek("absent")).toBe(undefined);
});
