/** @odoo-module */

import { describe, expect, test } from "@odoo/hoot";
import { parseUrl } from "../local_helpers";

import { Runner } from "../../core/runner";
import { Suite } from "../../core/suite";

describe(parseUrl(import.meta.url), () => {
    test("can register suites", () => {
        const runner = new Runner();
        runner.describe("a suite", () => {});
        runner.describe("another suite", () => {});

        expect(runner.suites).toHaveLength(2);
        expect(runner.tests).toHaveLength(0);
        for (const suite of runner.suites.values()) {
            expect(suite).toMatch(Suite);
        }
    });

    test("can register nested suites", () => {
        const runner = new Runner();
        runner.describe(["a", "b", "c"], () => {});

        expect([...runner.suites.values()].map((s) => s.name)).toEqual(["a", "b", "c"]);
    });

    test("can register tests", () => {
        const runner = new Runner();
        runner.describe("suite 1", () => {
            runner.test("test 1", () => {});
        });
        runner.describe("suite 2", () => {
            runner.test("test 2", () => {});
            runner.test("test 3", () => {});
        });

        expect(runner.suites).toHaveLength(2);
        expect(runner.tests).toHaveLength(3);
    });

    test("should not have duplicate suites", () => {
        const runner = new Runner();
        runner.describe(["parent", "child a"], () => {});
        runner.describe(["parent", "child b"], () => {});

        expect([...runner.suites.values()].map((suite) => suite.name)).toEqual([
            "parent",
            "child a",
            "child b",
        ]);
    });

    test("can refuse standalone tests", async () => {
        const runner = new Runner();
        expect(() =>
            runner.test([], "standalone test", () => {
                expect(true).toBe(false);
            })
        ).toThrow();
    });

    test("can register test tags", async () => {
        const runner = new Runner();
        runner.describe("suite", () => {
            let testFn = runner.test;
            for (let i = 1; i <= 10; i++) {
                // 10
                testFn = testFn.tags`Tag-${i}`;
            }

            testFn("tagged test", () => {});
        });

        expect(runner.tags).toHaveLength(10);
        expect(runner.tests.values().next().value.tags).toHaveLength(10);
    });
});
