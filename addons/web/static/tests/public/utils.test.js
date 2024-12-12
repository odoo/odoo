import { describe, expect, test } from "@odoo/hoot";

import { PairSet } from "@web/public/utils";

describe.current.tags("headless");

test("[PairSet] can add and delete pairs", () => {
    const pairSet = new PairSet();

    const a = {};
    const b = {};
    expect(pairSet.has(a, b)).toBe(false);
    pairSet.add(a, b);
    expect(pairSet.has(a, b)).toBe(true);
    pairSet.delete(a, b);
    expect(pairSet.has(a, b)).toBe(false);
});

test("[PairSet] can add and delete pairs with the same first element", () => {
    const pairSet = new PairSet();

    const a = {};
    const b = {};
    const c = {};
    expect(pairSet.has(a, b)).toBe(false);
    expect(pairSet.has(a, c)).toBe(false);
    pairSet.add(a, b);
    expect(pairSet.has(a, b)).toBe(true);
    expect(pairSet.has(a, c)).toBe(false);
    pairSet.add(a, c);
    expect(pairSet.has(a, b)).toBe(true);
    expect(pairSet.has(a, c)).toBe(true);
    pairSet.delete(a, c);
    expect(pairSet.has(a, b)).toBe(true);
    expect(pairSet.has(a, c)).toBe(false);
    pairSet.delete(a, b);
    expect(pairSet.has(a, b)).toBe(false);
    expect(pairSet.has(a, c)).toBe(false);
});

test("[PairSet] do not duplicated pairs", () => {
    const pairSet = new PairSet();

    const a = {};
    const b = {};
    expect(pairSet.map.size).toBe(0);
    pairSet.add(a, b);
    expect(pairSet.map.size).toBe(1);
    pairSet.add(a, b);
    expect(pairSet.map.size).toBe(1);
});
