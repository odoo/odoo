/** @odoo-module */

import { describe, expect, test } from "@odoo/hoot";
import { tick } from "@odoo/hoot-mock";
import { parseUrl } from "../local_helpers";

describe(parseUrl(import.meta.url), () => {
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
