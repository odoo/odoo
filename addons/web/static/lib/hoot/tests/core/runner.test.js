/** @odoo-module */

import { after, describe, expect, test } from "@odoo/hoot";
import { TestRunner } from "../../core/runner";
import { Suite } from "../../core/suite";
import { parseUrl } from "../local_helpers";

describe(parseUrl(import.meta.url), () => {
    test("can register suites", () => {
        const runner = new TestRunner();
        runner.describe("a suite", () => {});
        runner.describe("another suite", () => {});

        expect(runner.suites.size).toBe(2);
        expect(runner.tests.size).toBe(0);
        for (const suite of runner.suites.values()) {
            expect(suite).toMatch(Suite);
        }
    });

    test("can register nested suites", () => {
        const runner = new TestRunner();
        runner.describe(["a", "b", "c"], () => {});

        expect([...runner.suites.values()].map((s) => s.name)).toEqual(["a", "b", "c"]);
    });

    test("can register tests", () => {
        const runner = new TestRunner();
        runner.describe("suite 1", () => {
            runner.test("test 1", () => {});
        });
        runner.describe("suite 2", () => {
            runner.test("test 2", () => {});
            runner.test("test 3", () => {});
        });

        expect(runner.suites.size).toBe(2);
        expect(runner.tests.size).toBe(3);
    });

    test("should not have duplicate suites", () => {
        const runner = new TestRunner();
        runner.describe(["parent", "child a"], () => {});
        runner.describe(["parent", "child b"], () => {});

        expect([...runner.suites.values()].map((suite) => suite.name)).toEqual([
            "parent",
            "child a",
            "child b",
        ]);
    });

    test("can refuse standalone tests", async () => {
        const runner = new TestRunner();
        expect(() =>
            runner.test([], "standalone test", () => {
                expect(true).toBe(false);
            })
        ).toThrow();
    });

    test("can register test tags", async () => {
        const warn = console.warn;
        console.warn = (message) => expect.step(message);
        after(() => (console.warn = warn));

        const runner = new TestRunner();
        runner.describe("suite", () => {
            let testFn = runner.test.debug.only.skip; // 3
            for (let i = 1; i <= 10; i++) {
                // 10
                testFn = testFn.tags`Tag-${i}`;
            }

            testFn("tagged test", () => {});
        });

        expect(runner.tags.size).toBe(13);
        expect(runner.tests.values().next().value.tags.length).toBe(13);
        expect([
            `%c[HOOT]%c test "suite/tagged test" is explicitly included but marked as skipped: "skip" modifier has been ignored`,
        ]).toVerifySteps();
    });
});
