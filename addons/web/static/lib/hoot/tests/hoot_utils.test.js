/** @odoo-module */

import { describe, expect, test } from "@odoo/hoot";
import { isIterable, isRegExpFilter } from "@web/../lib/hoot-dom/hoot_dom_utils";
import { deepEqual, formatHumanReadable, generateHash, lookup, match, title } from "../hoot_utils";
import { parseUrl } from "./local_helpers";

describe(parseUrl(import.meta.url), () => {
    test("deepEqual", () => {
        expect(deepEqual(true, true)).toBe(true);
        expect(deepEqual(false, false)).toBe(true);
        expect(deepEqual(null, null)).toBe(true);
        expect(deepEqual({ b: 2, a: 1 }, { a: 1, b: 2 })).toBe(true);
        expect(deepEqual({ o: { a: [{ b: 1 }] } }, { o: { a: [{ b: 1 }] } })).toBe(true);
        expect(deepEqual([1, 2, 3], [1, 2, 3])).toBe(true);

        expect(deepEqual(true, false)).toBe(false);
        expect(deepEqual(null, undefined)).toBe(false);
        expect(deepEqual([1, 2, 3], [3, 1, 2])).toBe(false);
    });

    test("formatHumanReadable", () => {
        // Strings
        expect(formatHumanReadable("abc")).toBe(`"abc"`);
        expect(formatHumanReadable("a".repeat(300))).toBe(`"${"a".repeat(255)}..."`);
        // Numbers
        expect(formatHumanReadable(1)).toBe(`1`);
        // Other primitives
        expect(formatHumanReadable(true)).toBe(`true`);
        expect(formatHumanReadable(null)).toBe(`null`);
        // Functions & classes
        expect(formatHumanReadable(function oui() {})).toBe(`Function oui() { ... }`);
        expect(formatHumanReadable(class Oui {})).toBe(`class Oui { ... }`);
        // Iterators
        expect(formatHumanReadable([1, 2, 3])).toBe(`[...]`);
        expect(formatHumanReadable(new Set([1, 2, 3]))).toBe(`Set [...]`);
        expect(
            formatHumanReadable(
                new Map([
                    ["a", 1],
                    ["b", 2],
                ])
            )
        ).toBe(`Map [...]`);
        // Objects
        expect(formatHumanReadable(/ab(c)d/gi)).toBe(`/ab(c)d/gi`);
        expect(formatHumanReadable(new Date("1997-01-09T12:30:00.000Z"))).toBe(
            `1997-01-09T12:30:00.000Z`
        );
        expect(formatHumanReadable({ a: { b: 1 } })).toBe(`{ a: { ... } }`);
        expect(formatHumanReadable(new Proxy({}, {}))).toBe(`{  }`);
        expect(formatHumanReadable(window)).toBe(`Window { ... }`);
        expect(formatHumanReadable(document.createElement("div"))).toBe(`<div>`);
    });

    test("generateHash", () => {
        expect(generateHash("abc").length).toBe(8);
        expect(generateHash("abcdef").length).toBe(8);
        expect(generateHash("abc")).toBe(generateHash("abc"));

        expect(generateHash("abc")).not.toBe(generateHash("def"));
    });

    test("isIterable", () => {
        expect(isIterable([1, 2, 3])).toBe(true);
        expect(isIterable(new Set([1, 2, 3]))).toBe(true);

        expect(isIterable(null)).toBe(false);
        expect(isIterable("abc")).toBe(false);
        expect(isIterable({})).toBe(false);
    });

    test("isRegExpFilter", () => {
        expect(isRegExpFilter("/abc/")).toBe(true);
        expect(isRegExpFilter("/abc/i")).toBe(true);

        expect(isRegExpFilter("/abc")).toBe(false);
        expect(isRegExpFilter("abc/")).toBe(false);
    });

    test("lookup", () => {
        const list = ["babAba", "bAAab", "cccbCCb"];
        expect(lookup("aaa", list)).toEqual(["bAAab", "babAba"]);
        expect(lookup(/.b$/, list)).toEqual(["bAAab", "cccbCCb"]);
    });

    test("match", () => {
        expect(match("abc", /^abcd?/)).toBe(true);
        expect(match(new Error("error message"), "message")).toBe(true);
    });

    test("title", () => {
        expect(title("abcDef")).toBe("AbcDef");
    });
});
