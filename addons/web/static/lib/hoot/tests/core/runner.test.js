/** @odoo-module */

import { after, defineTags, describe, expect, test } from "@odoo/hoot";
import { parseUrl } from "../local_helpers";

import { Runner } from "../../core/runner";
import { Suite } from "../../core/suite";
import { undefineTags } from "../../core/tag";

const makeTestRunner = () => {
    const runner = new Runner();
    after(() => undefineTags(runner.tags.keys()));
    return runner;
};

describe(parseUrl(import.meta.url), () => {
    test("can register suites", () => {
        const runner = makeTestRunner();
        runner.describe("a suite", () => {});
        runner.describe("another suite", () => {});

        expect(runner.suites).toHaveLength(2);
        expect(runner.tests).toHaveLength(0);
        for (const suite of runner.suites.values()) {
            expect(suite).toMatch(Suite);
        }
    });

    test("can register nested suites", () => {
        const runner = makeTestRunner();
        runner.describe(["a", "b", "c"], () => {});

        expect([...runner.suites.values()].map((s) => s.name)).toEqual(["a", "b", "c"]);
    });

    test("can register tests", () => {
        const runner = makeTestRunner();
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
        const runner = makeTestRunner();
        runner.describe(["parent", "child a"], () => {});
        runner.describe(["parent", "child b"], () => {});

        expect([...runner.suites.values()].map((suite) => suite.name)).toEqual([
            "parent",
            "child a",
            "child b",
        ]);
    });

    test("can refuse standalone tests", async () => {
        const runner = makeTestRunner();
        expect(() =>
            runner.test([], "standalone test", () => {
                expect(true).toBe(false);
            })
        ).toThrow();
    });

    test("can register test tags", async () => {
        const runner = makeTestRunner();
        runner.describe("suite", () => {
            for (let i = 1; i <= 10; i++) {
                // 10
                runner.test.tags(`Tag-${i}`);
            }

            runner.test("tagged test", () => {});
        });

        expect(runner.tags).toHaveLength(10);
        expect(runner.tests.values().next().value.tags).toHaveLength(10);
    });

    test("can define exclusive test tags", async () => {
        expect.assertions(3);

        defineTags(
            {
                name: "a",
                exclude: ["b"],
            },
            {
                name: "b",
                exclude: ["a"],
            }
        );

        const runner = makeTestRunner();
        runner.describe("suite", () => {
            runner.test.tags("a");
            runner.test("first test", () => {});

            runner.test.tags("b");
            runner.test("second test", () => {});

            runner.test.tags("a", "b");
            expect(() => runner.test("third test", () => {})).toThrow(`cannot apply tag "b"`);

            runner.test.tags("a", "c");
            runner.test("fourth test", () => {});
        });

        expect(runner.tests).toHaveLength(3);
        expect(runner.tags).toHaveLength(3);
    });
});
