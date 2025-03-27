/** @odoo-module */

import { describe, expect, test } from "@odoo/hoot";
import { isIterable, isRegExpFilter } from "@web/../lib/hoot-dom/hoot_dom_utils";
import {
    deepEqual,
    formatHumanReadable,
    formatTechnical,
    generateHash,
    levenshtein,
    lookup,
    match,
    title,
    toExplicitString,
} from "../hoot_utils";
import { parseUrl } from "./local_helpers";

describe(parseUrl(import.meta.url), () => {
    test("deepEqual", () => {
        const recursive = {};
        recursive.self = recursive;

        const TRUTHY_CASES = [
            [true, true],
            [false, false],
            [null, null],
            [recursive, recursive],
            [new Date(0), new Date(0)],
            [
                { b: 2, a: 1 },
                { a: 1, b: 2 },
            ],
            [{ o: { a: [{ b: 1 }] } }, { o: { a: [{ b: 1 }] } }],
            [Symbol.for("a"), Symbol.for("a")],
            [document.createElement("div"), document.createElement("div")],
            [
                [1, 2, 3],
                [1, 2, 3],
            ],
        ];
        const FALSY_CASES = [
            [true, false],
            [null, undefined],
            [recursive, { ...recursive, a: 1 }],
            [
                [1, 2, 3],
                [3, 1, 2],
            ],
            [new Date(0), new Date(1_000)],
            [{ a: new Date(0) }, { a: 0 }],
            [document.createElement("a"), document.createElement("div")],
            [{ [Symbol("a")]: 1 }, { [Symbol("a")]: 1 }],
        ];
        const TRUTHY_IF_UNORDERED_CASES = [
            [
                [1, "2", 3],
                ["2", 3, 1],
            ],
            [
                [1, { a: [4, 2] }, "3"],
                [{ a: [2, 4] }, "3", 1],
            ],
            [
                new Set([
                    "abc",
                    new Map([
                        ["b", 2],
                        ["a", 1],
                    ]),
                ]),
                new Set([
                    new Map([
                        ["a", 1],
                        ["b", 2],
                    ]),
                    "abc",
                ]),
            ],
        ];

        expect.assertions(
            TRUTHY_CASES.length + FALSY_CASES.length + TRUTHY_IF_UNORDERED_CASES.length * 2
        );

        for (const [a, b] of TRUTHY_CASES) {
            expect(deepEqual(a, b)).toBe(true, {
                message: (_, r) => [a, r`==`, b],
            });
        }
        for (const [a, b] of FALSY_CASES) {
            expect(deepEqual(a, b)).toBe(false, {
                message: (_, r) => [a, r`!=`, b],
            });
        }
        for (const [a, b] of TRUTHY_IF_UNORDERED_CASES) {
            expect(deepEqual(a, b)).toBe(false, {
                message: (_, r) => [a, r`!=`, b],
            });
            expect(deepEqual(a, b, { ignoreOrder: true })).toBe(true, {
                message: (_, r) => [a, r`==`, b, r`(unordered))`],
            });
        }
    });

    test("formatHumanReadable", () => {
        // Strings
        expect(formatHumanReadable("abc")).toBe(`"abc"`);
        expect(formatHumanReadable("a".repeat(300))).toBe(`"${"a".repeat(80)}…"`);
        expect(formatHumanReadable(`with "double quotes"`)).toBe(`'with "double quotes"'`);
        expect(formatHumanReadable(`with "double quotes" and 'single quote'`)).toBe(
            `\`with "double quotes" and 'single quote'\``
        );
        // Numbers
        expect(formatHumanReadable(1)).toBe(`1`);
        // Other primitives
        expect(formatHumanReadable(true)).toBe(`true`);
        expect(formatHumanReadable(null)).toBe(`null`);
        // Functions & classes
        expect(formatHumanReadable(async function oui() {})).toBe(`async function oui() { … }`);
        expect(formatHumanReadable(class Oui {})).toBe(`class Oui { … }`);
        // Iterators
        expect(formatHumanReadable([1, 2, 3])).toBe(`[1, 2, 3]`);
        expect(formatHumanReadable(new Set([1, 2, 3]))).toBe(`Set [1, 2, 3]`);
        expect(
            formatHumanReadable(
                new Map([
                    ["a", 1],
                    ["b", 2],
                ])
            )
        ).toBe(`Map [["a", 1], ["b", 2]]`);
        // Objects
        expect(formatHumanReadable(/ab(c)d/gi)).toBe(`/ab(c)d/gi`);
        expect(formatHumanReadable(new Date("1997-01-09T12:30:00.000Z"))).toBe(
            `1997-01-09T12:30:00.000Z`
        );
        expect(formatHumanReadable({})).toBe(`{  }`);
        expect(formatHumanReadable({ a: { b: 1 } })).toBe(`{ a: { b: 1 } }`);
        expect(
            formatHumanReadable(
                new Proxy(
                    {
                        allowed: true,
                        get forbidden() {
                            throw new Error("Cannot access!");
                        },
                    },
                    {}
                )
            )
        ).toBe(`{ allowed: true }`);
        expect(formatHumanReadable(window)).toBe(`Window {  }`);
        // Nodes
        expect(formatHumanReadable(document.createElement("div"))).toBe("<div>");
        expect(formatHumanReadable(document.createTextNode("some text"))).toBe("#text");
        expect(formatHumanReadable(document)).toBe("#document");
    });

    test("formatTechnical", () => {
        expect(
            formatTechnical({
                b: 2,
                a: true,
            })
        ).toBe(
            `{
  a: true,
  b: 2,
}`.trim()
        );

        expect(formatTechnical(["a", "b"])).toBe(
            `[
  "a",
  "b",
]`.trim()
        );

        class List extends Array {}

        expect(formatTechnical(new List("a", "b"))).toBe(
            `List [
  "a",
  "b",
]`.trim()
        );

        function toArguments() {
            return arguments;
        }

        expect(formatTechnical(toArguments("a", "b"))).toBe(
            `Arguments [
  "a",
  "b",
]`.trim()
        );
    });

    test("generateHash", () => {
        expect(generateHash("abc")).toHaveLength(8);
        expect(generateHash("abcdef")).toHaveLength(8);
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

    test("levenshtein", () => {
        expect(levenshtein("abc", "abc")).toBe(0);
        expect(levenshtein("abc", "àbc ")).toBe(2);
        expect(levenshtein("abc", "def")).toBe(3);
        expect(levenshtein("abc", "adc")).toBe(1);
    });

    test("lookup", () => {
        const list = [{ key: "bababa" }, { key: "baaab" }, { key: "cccbccb" }];
        expect(lookup("aaa", list)).toEqual([{ key: "baaab" }, { key: "bababa" }]);
        expect(lookup(/.b$/, list)).toEqual([{ key: "baaab" }, { key: "cccbccb" }]);
    });

    test("match", () => {
        expect(match("abc", /^abcd?/)).toBe(true);
        expect(match(new Error("error message"), "message")).toBe(true);
    });

    test("title", () => {
        expect(title("abcDef")).toBe("AbcDef");
    });

    test("toExplicitString", () => {
        expect(toExplicitString("\n")).toBe(`\\n`);
        expect(toExplicitString("\t")).toBe(`\\t`);

        expect(toExplicitString(" \n")).toBe(` \n`);
        expect(toExplicitString("\t ")).toBe(`\t `);

        expect(toExplicitString("Abc\u200BDef")).toBe(`Abc\\u200bDef`);
    });
});
