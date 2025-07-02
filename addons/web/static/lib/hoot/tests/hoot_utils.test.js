/** @odoo-module */

import { describe, expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { isInstanceOf, isIterable } from "@web/../lib/hoot-dom/hoot_dom_utils";
import {
    deepEqual,
    formatHumanReadable,
    formatTechnical,
    generateHash,
    levenshtein,
    lookup,
    match,
    parseQuery,
    title,
    toExplicitString,
} from "../hoot_utils";
import { mountForTest, parseUrl } from "./local_helpers";

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
                message: [a, `==`, b],
            });
        }
        for (const [a, b] of FALSY_CASES) {
            expect(deepEqual(a, b)).toBe(false, {
                message: [a, `!=`, b],
            });
        }
        for (const [a, b] of TRUTHY_IF_UNORDERED_CASES) {
            expect(deepEqual(a, b)).toBe(false, {
                message: [a, `!=`, b],
            });
            expect(deepEqual(a, b, { ignoreOrder: true })).toBe(true, {
                message: [a, `==`, b, `(unordered))`],
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
                [Symbol("s")]: "value",
                a: true,
            })
        ).toBe(
            `{
  a: true,
  b: 2,
  Symbol(s): "value",
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

    test("isInstanceOf", async () => {
        await mountForTest(/* xml */ `
            <iframe srcdoc="" />
        `);

        expect(() => isInstanceOf()).toThrow(TypeError);
        expect(() => isInstanceOf("a")).toThrow(TypeError);

        expect(isInstanceOf(null, null)).toBe(false);
        expect(isInstanceOf(undefined, undefined)).toBe(false);
        expect(isInstanceOf("", String)).toBe(false);
        expect(isInstanceOf(24, Number)).toBe(false);
        expect(isInstanceOf(true, Boolean)).toBe(false);

        class List extends Array {}

        class A {}
        class B extends A {}

        expect(isInstanceOf([], Array)).toBe(true);
        expect(isInstanceOf(new List(), Array)).toBe(true);
        expect(isInstanceOf(new B(), B)).toBe(true);
        expect(isInstanceOf(new B(), A)).toBe(true);
        expect(isInstanceOf(new Error("error"), Error)).toBe(true);
        expect(isInstanceOf(/a/, RegExp, Date)).toBe(true);
        expect(isInstanceOf(new Date(), RegExp, Date)).toBe(true);

        const { contentDocument, contentWindow } = queryOne("iframe");

        expect(isInstanceOf(queryOne("iframe"), HTMLIFrameElement)).toBe(true);
        expect(contentWindow instanceof Window).toBe(false);
        expect(isInstanceOf(contentWindow, Window)).toBe(true);
        expect(contentDocument.body instanceof HTMLBodyElement).toBe(false);
        expect(isInstanceOf(contentDocument.body, HTMLBodyElement)).toBe(true);
    });

    test("isIterable", () => {
        expect(isIterable([1, 2, 3])).toBe(true);
        expect(isIterable(new Set([1, 2, 3]))).toBe(true);

        expect(isIterable(null)).toBe(false);
        expect(isIterable("abc")).toBe(false);
        expect(isIterable({})).toBe(false);
    });

    test("levenshtein", () => {
        expect(levenshtein("abc", "abc")).toBe(0);
        expect(levenshtein("abc", "àbc ")).toBe(2);
        expect(levenshtein("abc", "def")).toBe(3);
        expect(levenshtein("abc", "adc")).toBe(1);
    });

    test("parseQuery & lookup", () => {
        /**
         * @param {string} query
         * @param {string[]} itemsList
         * @param {string} [property]
         */
        const expectQuery = (query, itemsList, property = "key") => {
            const keyedItems = itemsList.map((item) => ({ [property]: item }));
            const result = lookup(parseQuery(query), keyedItems);
            return {
                /**
                 * @param {string[]} expected
                 */
                toEqual: (expected) =>
                    expect(result).toEqual(
                        expected.map((item) => ({ [property]: item })),
                        { message: `query ${query} should match ${expected}` }
                    ),
            };
        };

        const list = [
            "Frodo",
            "Sam",
            "Merry",
            "Pippin",
            "Frodo Sam",
            "Merry Pippin",
            "Frodo Sam Merry Pippin",
        ];

        // Error handling
        expect(() => parseQuery()).toThrow();
        expect(() => lookup()).toThrow();
        expect(() => lookup("a", [{ key: "a" }])).toThrow();
        expect(() => lookup(parseQuery("a"))).toThrow();

        // Empty query and/or empty lists
        expectQuery("", []).toEqual([]);
        expectQuery("", ["bababa", "baaab", "cccbccb"]).toEqual(["bababa", "baaab", "cccbccb"]);
        expectQuery("aaa", []).toEqual([]);

        // Regex
        expectQuery(`/.b$/`, ["bababa", "baaab", "cccbccB"]).toEqual(["baaab"]);
        expectQuery(`/.b$/i`, ["bababa", "baaab", "cccbccB"]).toEqual(["baaab", "cccbccB"]);

        // Exact match
        expectQuery(`"aaa"`, ["bababa", "baaab", "cccbccb"]).toEqual(["baaab"]);
        expectQuery(`"sam"`, list).toEqual([]);
        expectQuery(`"Sam"`, list).toEqual(["Sam", "Frodo Sam", "Frodo Sam Merry Pippin"]);
        expectQuery(`"Sam" "Frodo"`, list).toEqual(["Frodo Sam", "Frodo Sam Merry Pippin"]);
        expectQuery(`"Frodo Sam"`, list).toEqual(["Frodo Sam", "Frodo Sam Merry Pippin"]);
        expectQuery(`"FrodoSam"`, list).toEqual([]);
        expectQuery(`"Frodo  Sam"`, list).toEqual([]);
        expectQuery(`"Sam" -"Frodo"`, list).toEqual(["Sam"]);

        // Partial (fuzzy) match
        expectQuery(`aaa`, ["bababa", "baaab", "cccbccb"]).toEqual(["baaab", "bababa"]);
        expectQuery(`aaa -bbb`, ["bababa", "baaab", "cccbccb"]).toEqual(["baaab"]);
        expectQuery(`-aaa`, ["bababa", "baaab", "cccbccb"]).toEqual(["cccbccb"]);
        expectQuery(`frosapip`, list).toEqual(["Frodo Sam Merry Pippin"]);
        expectQuery(`-s fro`, list).toEqual(["Frodo"]);
        expectQuery(` FR  SAPI `, list).toEqual(["Frodo Sam Merry Pippin"]);

        // Mixed queries
        expectQuery(`"Sam" fro pip`, list).toEqual(["Frodo Sam Merry Pippin"]);
        expectQuery(`fro"Sam"pip`, list).toEqual(["Frodo Sam Merry Pippin"]);
        expectQuery(`-"Frodo" s`, list).toEqual(["Sam"]);
        expectQuery(`"Merry" -p`, list).toEqual(["Merry"]);
        expectQuery(`"rry" -s`, list).toEqual(["Merry", "Merry Pippin"]);
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
