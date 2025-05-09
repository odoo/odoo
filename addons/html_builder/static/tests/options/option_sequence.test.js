import {
    after,
    before,
    BEGIN,
    END,
    SNIPPET_SPECIFIC,
    splitBetween,
} from "@html_builder/utils/option_sequence";
import { expect, test } from "@odoo/hoot";

const ARBITRARY_FAKE_POSITION = 7777777777;

test("before throws if position doesn't exist", async () => {
    expect(() => before(ARBITRARY_FAKE_POSITION)).toThrow();
});

test("before throws if position is BEGIN", async () => {
    expect(() => before(BEGIN)).toThrow();
});

test("before returns a smaller position", async () => {
    expect(before(SNIPPET_SPECIFIC)).toBeLessThan(SNIPPET_SPECIFIC);
    expect(before(END)).toBeLessThan(END);
});

test("after throws if position doesn't exist", async () => {
    expect(() => after(ARBITRARY_FAKE_POSITION)).toThrow();
});

test("after throws if position is END", async () => {
    expect(() => after(END)).toThrow();
});

test("after returns a bigger position", async () => {
    expect(after(SNIPPET_SPECIFIC)).toBeGreaterThan(SNIPPET_SPECIFIC);
    expect(after(BEGIN)).toBeGreaterThan(BEGIN);
});

test("splitBetween correctly splits to the right values", async () => {
    expect(splitBetween(0, 3, 2)).toMatch([1, 2]);
    expect(splitBetween(0, 10, 2)).toMatch([10 / 3, (2 * 10) / 3]);
    expect(splitBetween(0, 8, 7)).toMatch([1, 2, 3, 4, 5, 6, 7]);
    expect(splitBetween(1, 5, 3)).toMatch([2, 3, 4]);
});
