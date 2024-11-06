import { describe, expect, test } from "@odoo/hoot";

import { PairSet } from "@website/core/utils";

describe.current.tags("headless");

test("basic use", () => {
    const pairSet = new PairSet();

    const a = {};
    const b = {};
    expect(pairSet.has(a,b)).not.toBe(true);
    pairSet.add(a,b);
    expect(pairSet.has(a,b)).toBe(true);
    pairSet.delete(a,b);
    expect(pairSet.has(a,b)).not.toBe(true);
});

test("it works with multiple pairs with same first value", () => {
    const pairSet = new PairSet();

    const a = {};
    const b = {};
    const c = {};
    expect(pairSet.has(a,b)).not.toBe(true);
    expect(pairSet.has(a,c)).not.toBe(true);
    pairSet.add(a,b);
    expect(pairSet.has(a,b)).toBe(true);
    expect(pairSet.has(a,c)).not.toBe(true);
    pairSet.add(a,c);
    expect(pairSet.has(a,b)).toBe(true);
    expect(pairSet.has(a,c)).toBe(true);
    pairSet.delete(a,b);
    expect(pairSet.has(a,b)).not.toBe(true);
    expect(pairSet.has(a,c)).toBe(true);
});
