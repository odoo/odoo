/** @odoo-module */

import { describe, expect, makeExpect, mountOnFixture, test } from "@odoo/hoot";
import { check, tick } from "@odoo/hoot-dom";
import { Component, xml } from "@odoo/owl";
import { parseUrl } from "../local_helpers";

import { Test } from "../../core/test";

describe(parseUrl(import.meta.url), () => {
    test("makeExpect passing, without a test", () => {
        const [customExpect, hooks] = makeExpect({ headless: true });

        expect(() => customExpect(true).toBe(true)).toThrow(
            "cannot call `expect()` outside of a test"
        );

        hooks.before();

        customExpect({ key: true }).toEqual({ key: true });
        customExpect("oui").toBe("oui");

        const results = hooks.after();

        expect(results.pass).toBe(true);
        expect(results.assertions).toHaveLength(2);
    });

    test("makeExpect failing, without a test", () => {
        const [customExpect, hooks] = makeExpect({ headless: true });

        hooks.before();

        customExpect({ key: true }).toEqual({ key: true });
        customExpect("oui").toBe("non");

        const results = hooks.after();

        expect(results.pass).toBe(false);
        expect(results.assertions).toHaveLength(2);
    });

    test("makeExpect with a test", async () => {
        const [customExpect, hooks] = makeExpect({ headless: true });
        const customTest = new Test(null, "test", {}, () => {
            customExpect({ key: true }).toEqual({ key: true });
            customExpect("oui").toBe("non");
        });

        hooks.before(customTest);

        await customTest.run();

        const results = hooks.after();

        expect(customTest.lastResults).toBe(results);
        // Result is expected to have the same shape, no need for other assertions
    });

    test("makeExpect with a test flagged with TODO", async () => {
        const [customExpect, hooks] = makeExpect({ headless: true });
        const customTest = new Test(null, "test", { todo: true }, () => {
            customExpect(1).toBe(1);
        });

        hooks.before(customTest);

        await customTest.run();

        const results = hooks.after();

        expect(results.pass).toBe(false);
        expect(results.assertions[0].pass).toBe(true);
    });

    test("makeExpect with no assertions", () => {
        const [customExpect, hooks] = makeExpect({ headless: true });

        hooks.before();

        expect(() => customExpect.assertions(0)).toThrow(
            "expected assertions count should be more than 1"
        );

        const results = hooks.after();

        expect(results.pass).toBe(false);
        expect(results.assertions).toHaveLength(1);
        expect(results.assertions[0].message).toBe(
            "expected at least one assertion, but none were run"
        );
    });

    test("makeExpect with unconsumed matchers", () => {
        const [customExpect, hooks] = makeExpect({ headless: true });

        hooks.before();

        expect(() => customExpect(true, true)).toThrow("`expect()` only accepts a single argument");
        customExpect(true);

        const results = hooks.after();

        expect(results.pass).toBe(false);
        expect(results.assertions).toHaveLength(1);
        expect(results.assertions[0].message).toBe("called once without calling any matchers");
    });

    test("makeExpect with unverified steps", () => {
        const [customExpect, hooks] = makeExpect({ headless: true });

        hooks.before();

        customExpect.step("oui");
        customExpect.verifySteps(["oui"]);
        customExpect.step("non");

        const results = hooks.after();

        expect(results.pass).toBe(false);
        expect(results.assertions).toHaveLength(2);
        expect(results.assertions[1].message).toBe("unverified steps");
    });

    test("makeExpect retains current values", () => {
        const [customExpect, hooks] = makeExpect({ headless: true });

        hooks.before();

        const object = { a: 1 };
        customExpect(object).toEqual({ b: 2 });
        object.b = 2;

        const testResult = hooks.after();

        const [assertion] = testResult.assertions;
        expect(assertion.pass).toBe(false);
        expect(assertion.failedDetails[1][1]).toEqual({ a: 1 });
        expect(object).toEqual({ a: 1, b: 2 });
    });

    test("'expect' results contain the correct informations", async () => {
        await mountOnFixture(/* xml */ `
            <label style="color: #f00">
                Checkbox
                <input class="cb" type="checkbox" />
            </label>
            <input type="text" value="abc" />
        `);

        await check("input[type=checkbox]");

        const [customExpect, hooks] = makeExpect({ headless: true });

        hooks.before();

        const matchers = [
            // Standard
            ["toBe", 1, 1],
            ["toBeCloseTo", 1, 1],
            ["toBeEmpty", []],
            ["toBeGreaterThan", 1, 0],
            ["toBeInstanceOf", {}, Object],
            ["toBeLessThan", 0, 1],
            ["toBeOfType", 1, "integer"],
            ["toBeWithin", 1, 0, 2],
            ["toEqual", [], []],
            ["toHaveLength", [], 0],
            ["toInclude", [1], 1],
            ["toMatch", "a", "a"],
            [
                "toThrow",
                () => {
                    throw new Error("");
                },
            ],
            // DOM
            ["toBeChecked", ".cb"],
            ["toBeDisplayed", ".cb"],
            ["toBeEnabled", ".cb"],
            ["toBeFocused", ".cb"],
            ["toBeVisible", ".cb"],
            ["toHaveAttribute", ".cb", "type", "checkbox"],
            ["toHaveClass", ".cb", "cb"],
            ["toHaveCount", ".cb", 1],
            ["toHaveInnerHTML", ".cb", ""],
            ["toHaveOuterHTML", ".cb", `<input class="cb" type="checkbox" />`],
            ["toHaveProperty", ".cb", "checked", true],
            ["toHaveRect", "label", { x: 0 }],
            ["toHaveStyle", "label", { color: "rgb(255, 0, 0)" }],
            ["toHaveText", "label", "Checkbox"],
            ["toHaveValue", "input[type=text]", "abc"],
        ];

        for (const [name, ...args] of matchers) {
            customExpect(args.shift())[name](...args);
        }

        const testResult = hooks.after();

        expect(testResult.pass).toBe(true);
        expect(testResult.assertions).toHaveLength(matchers.length);
        expect(testResult.assertions.map(({ label }) => label)).toEqual(
            matchers.map(([name]) => name)
        );
    });

    describe("standard matchers", () => {
        test("toBe", () => {
            // Boolean
            expect(true).toBe(true);
            expect(true).not.toBe(false);

            // Floats
            expect(1.1).toBe(1.1);
            expect(0.1 + 0.2).not.toBe(0.3); // floating point errors

            // Integers
            expect(+0).toBe(-0);
            expect(1 + 2).toBe(3);
            expect(1).not.toBe(-1);
            expect(NaN).toBe(NaN);

            // Strings
            expect("abc").toBe("abc");
            expect(new String("abc")).not.toBe(new String("abc"));

            // Other primitives
            expect(undefined).toBe(undefined);
            expect(undefined).not.toBe(null);

            // Symbols
            const symbol = Symbol("symbol");
            expect(symbol).toBe(symbol);
            expect(symbol).not.toBe(Symbol("symbol"));
            expect(Symbol.for("symbol")).toBe(Symbol.for("symbol"));

            // Objects
            const object = { x: 1 };
            expect(object).toBe(object);
            expect([]).not.toBe([]);
            expect(object).not.toBe({ x: 1 });

            // Dates
            const date = new Date(0);
            expect(date).toBe(date);
            expect(new Date(0)).not.toBe(new Date(0));

            // Nodes
            expect(new Image()).not.toBe(new Image());
            expect(document.createElement("div")).not.toBe(document.createElement("div"));
        });

        test("toBeCloseTo", () => {
            expect(0.2 + 0.1).toBeCloseTo(0.3);
            expect(0.2 + 0.1).toBeCloseTo(0.3, { digits: 2 });
            expect(0.2 + 0.1).toBeCloseTo(0.3, { digits: 16 });
            expect(0.2 + 0.1).not.toBeCloseTo(0.3, { digits: 17 });

            expect(3.51).toBeCloseTo(3.5, { digits: 1 });
            expect(3.51).not.toBeCloseTo(3.5);
            expect(3.51).not.toBeCloseTo(3.5, { digits: 2 });
            expect(3.51).not.toBeCloseTo(3.5, { digits: 17 });
        });

        test("toEqual", () => {
            // Boolean
            expect(true).toEqual(true);
            expect(true).not.toEqual(false);

            // Floats
            expect(1.1).toEqual(1.1);
            expect(0.1 + 0.2).not.toEqual(0.3); // floating point errors

            // Integers
            expect(+0).toEqual(-0);
            expect(1 + 2).toEqual(3);
            expect(1).not.toEqual(-1);
            expect(NaN).toEqual(NaN);

            // Strings
            expect("abc").toEqual("abc");
            expect(new String("abc")).toEqual(new String("abc"));

            // Other primitives
            expect(undefined).toEqual(undefined);
            expect(undefined).not.toEqual(null);

            // Symbols
            const symbol = Symbol("symbol");
            expect(symbol).toEqual(symbol);
            expect(symbol).not.toEqual(Symbol("symbol"));
            expect(Symbol.for("symbol")).toEqual(Symbol.for("symbol"));

            // Objects
            const object = { x: 1 };
            expect(object).toEqual(object);
            expect([]).toEqual([]);
            expect(object).toEqual({ x: 1 });

            // Iterables
            expect(new Set([1, 4, 6])).toEqual(new Set([1, 4, 6]));
            expect(new Set([1, 4, 6])).not.toEqual([1, 4, 6]);
            expect(new Map([[{}, "abc"]])).toEqual(new Map([[{}, "abc"]]));

            // Dates
            const date = new Date(0);
            expect(date).toEqual(date);
            expect(new Date(0)).toEqual(new Date(0));

            // Nodes
            expect(new Image()).toEqual(new Image());
            expect(document.createElement("div")).toEqual(document.createElement("div"));
            expect(document.createElement("div")).not.toEqual(document.createElement("span"));
        });

        test("toMatch", () => {
            class Exception extends Error {}

            expect("aaaa").toMatch(/^a{4}$/);
            expect("aaaa").toMatch("aa");
            expect("aaaa").not.toMatch("aaaaa");

            // Matcher from a class
            expect(new Exception("oui")).toMatch(Error);
            expect(new Exception("oui")).toMatch(Exception);
            expect(new Exception("oui")).toMatch(new Error("oui"));
        });

        test("toThrow", async () => {
            const asyncBoom = async () => {
                throw new Error("rejection");
            };

            const boom = () => {
                throw new Error("error");
            };

            expect(boom).toThrow();
            expect(boom).toThrow("error");
            expect(boom).toThrow(new Error("error"));

            await expect(asyncBoom()).rejects.toThrow();
            await expect(asyncBoom()).rejects.toThrow("rejection");
            await expect(asyncBoom()).rejects.toThrow(new Error("rejection"));
        });

        test("verifyErrors", async () => {
            expect.assertions(1);
            expect.errors(2);

            const asyncBoom = async () => {
                throw new Error("rejection");
            };

            const boom = () => {
                throw new Error("error");
            };

            asyncBoom();
            setTimeout(boom);
            await tick();
            await tick();

            expect.verifyErrors(["error", "rejection"]);
        });

        test("verifySteps", () => {
            expect.assertions(4);

            expect.verifySteps([]);

            expect.step("abc");
            expect.step("def");
            expect.verifySteps(["abc", "def"]);

            expect.step({ property: "foo" });
            expect.step("ghi");

            expect.verifySteps([{ property: "foo" }, "ghi"]);
            expect.verifySteps([]);
        });
    });

    describe("DOM matchers", () => {
        test("toHaveAttribute", async () => {
            await mountOnFixture(/* xml */ `
                <input type="number" disabled="" />
            `);

            expect("input").toHaveAttribute("disabled");
            expect("input").not.toHaveAttribute("readonly");
            expect("input").toHaveAttribute("type", "number");
        });

        test("toHaveCount", async () => {
            await mountOnFixture(/* xml */ `
                <ul>
                    <li>milk</li>
                    <li>eggs</li>
                    <li>milk</li>
                </ul>
            `);

            expect("iframe").toHaveCount(0);
            expect("iframe").not.toHaveCount();
            expect("ul").toHaveCount(1);
            expect("ul").toHaveCount();
            expect("li").toHaveCount(3);
            expect("li").toHaveCount();
            expect("li:contains(milk)").toHaveCount(2);
        });

        test("toHaveText", async () => {
            class TextComponent extends Component {
                static props = {};
                static template = xml`
                    <div class="with">With<t t-esc="nbsp" />nbsp</div>
                    <div class="without">Without nbsp</div>
                `;

                nbsp = "\u00a0";
            }

            await mountOnFixture(TextComponent);

            expect(".with").toHaveText("With nbsp");
            expect(".with").toHaveText("With\u00a0nbsp", { raw: true });
            expect(".with").not.toHaveText("With\u00a0nbsp");

            expect(".without").toHaveText("Without nbsp");
            expect(".without").not.toHaveText("Without\u00a0nbsp");
            expect(".without").not.toHaveText("Without\u00a0nbsp", { raw: true });
        });
    });
});
