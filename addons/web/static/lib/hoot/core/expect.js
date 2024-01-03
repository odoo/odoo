/** @odoo-module */
/* eslint-disable no-restricted-syntax */

import {
    getActiveElement,
    getNodeText,
    getNodeValue,
    getStyle,
    isCheckable,
    isDisplayed,
    isEmpty,
    isVisible,
    queryAll,
} from "@web/../lib/hoot-dom/helpers/dom";
import { isFirefox, isIterable } from "@web/../lib/hoot-dom/hoot_dom_utils";
import {
    HootError,
    Markup,
    deepEqual,
    ensureArguments,
    ensureArray,
    formatHumanReadable,
    hootLog,
    isNil,
    isOfType,
    match,
    strictEqual,
} from "../hoot_utils";
import { Test } from "./test";

/**
 * @typedef {import("../hoot_utils").ArgumentType} ArgumentType
 *
 * @typedef {{
 *  message?: string;
 * }} ExpectOptions
 *
 * @typedef {import("@odoo/hoot-dom").Target} Target
 */

/**
 * @template [R=unknown]
 * @template [A=R]
 * @typedef {{
 *  acceptedType: ArgumentType | ArgumentType[];
 *  details: (actual: A) => any[];
 *  message: (pass: boolean) => string;
 *  name: string;
 *  predicate: (actual: A) => boolean;
 *  transform?: (received: R) => A;
 * }} MatcherSpecifications
 */

/**
 * @template Async
 * @typedef {{
 *  not?: boolean;
 *  rejects?: Async;
 *  resolves?: Async;
 * }} Modifiers
 */

/**
 * @template T
 * @typedef {T | Iterable<T>} MaybeIterable
 */

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const { Boolean, Error, Object, Promise, TypeError, console, performance } = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @param {import("./runner").TestRunner} runner
 * @param {Test} test
 */
const afterTest = (runner, test) => {
    currentResult.duration = performance.now() - currentResult.ts;

    // Steps
    if (currentResult.steps.length) {
        registerAssertion(
            new Assertion({
                label: "step",
                message: `unverified steps`,
                pass: false,
                info: [[Markup.red("Steps:"), Markup.diff([], currentResult.steps)]],
            })
        );
    }

    // Assertions count
    if (!currentResult.assertions.length) {
        registerAssertion(
            new Assertion({
                label: "assertions",
                message: `expected at least one assertion, but none were run`,
                pass: false,
            })
        );
    } else if (
        currentResult.expectedAssertions &&
        currentResult.assertions.length !== currentResult.expectedAssertions
    ) {
        registerAssertion(
            new Assertion({
                label: "assertions",
                message: `expected ${currentResult.expectedAssertions} assertions, but ${currentResult.assertions.length} were run`,
                pass: false,
            })
        );
    }

    // Errors count
    const errorCount = currentResult.errors.length;
    if (currentResult.expectedErrors) {
        if (currentResult.expectedErrors !== errorCount) {
            registerAssertion(
                new Assertion({
                    label: "errors",
                    message: `expected ${currentResult.expectedErrors} errors, but ${errorCount} were thrown`,
                    pass: false,
                })
            );
        }
    } else if (errorCount) {
        registerAssertion(
            new Assertion({
                label: "errors",
                message: `${errorCount} unverified error(s)`,
                pass: false,
            })
        );
    }

    // "Todo" tag
    if (test.config.todo) {
        if (currentResult.pass) {
            registerAssertion(
                new Assertion({
                    label: "TODO",
                    message: `all assertions passed: remove "todo" test modifier`,
                    pass: false,
                })
            );
        } else {
            currentResult.pass = true;
        }
    }

    // Set test status
    if (currentResult.aborted) {
        test.status = Test.ABORTED;
    } else if (currentResult.pass) {
        test.status ||= Test.PASSED;
    } else {
        test.status = Test.FAILED;
    }

    /** @type {import("../hoot_utils").Reporting} */
    const report = {
        assertions: currentResult.assertions.length,
        tests: 1,
    };
    if (!currentResult.pass) {
        report.failed = 1;
    } else if (test.config.todo) {
        report.todo = 1;
    } else {
        report.passed = 1;
    }

    test.parent.reporting.add(report);

    currentResult = null;
};

/**
 * @param  {...string} values
 */
const and = (...values) => {
    const last = values.pop();
    if (values.length) {
        return [values.join(", "), last].join(" and ");
    } else {
        return last;
    }
};

/**
 * @param {number} expected
 */
const assertions = (expected) => {
    if (!currentResult) {
        throw scopeError("expect.assertions");
    }
    ensureArguments([[expected, "integer"]]);

    currentResult.expectedAssertions = expected;
};

/**
 * @param {import("./runner").TestRunner} runner
 * @param {Test} test
 */
const beforeTest = (runner, test) => {
    test.results.push(new TestResult());

    // Must be retrieved from the list to be proxified
    currentResult = test.results.at(-1);
};

/**
 * @param {unknown} value
 */
const canDiff = (value) => value && !["boolean", "number"].includes(typeof value);

/**
 * @template T
 * @param {(item: T) => boolean} predicate
 * @returns {(value: MaybeIterable<T>) => boolean}
 */
const each = (predicate) => (value) => {
    const values = ensureArray(value);
    return values.length && values.every(predicate);
};

/**
 * @param {number} expected
 */
const errors = (expected) => {
    if (!currentResult) {
        throw scopeError("expect.errors");
    }
    ensureArguments([[expected, "integer"]]);

    currentResult.expectedErrors = expected;
};

/** @type {(typeof Matchers)["extend"]} */
const extend = (matcher) => {
    return Matchers.extend(matcher);
};

/**
 * @param {string} message
 * @param {{ received: unknown; actual: unknown; not: boolean }} params
 */
const formatMessage = (message, { received, actual, not }) =>
    message
        .replace(NOT_REGEX, (_, ifTrue, ifFalse) => (not ? ifFalse || "" : ifTrue || ""))
        .replace(RECEIVED_REGEX, formatHumanReadable(received))
        .replace(ACTUAL_REGEX, formatHumanReadable(actual))
        .replace(ELEMENTS_REGEX, (_, elements) =>
            typeof received === "string"
                ? `${elements} matching "${received}"`
                : formatHumanReadable(actual)
        );

/**
 * @param {string} stack
 */
const formatStack = (stack) => {
    let stackLines = String(stack)
        .split(/\n/g)
        .slice(isFirefox() ? 1 : 2); // remove `saveStack` (and ´Error´ in chrome)
    if (stackLines.length > 10) {
        stackLines = [...stackLines.slice(0, 10), `... ${stackLines.length - 10} more`];
    }
    return stackLines.map((v) => Markup.text(v.trim()));
};

/**
 * @param {Node} node
 * @param {string[]} keys
 * @returns {Record<string, string>}
 */
const getStyleValues = (node, keys) => {
    const nodeStyle = getStyle(node);
    if (!nodeStyle) {
        return {};
    }
    return Object.fromEntries(keys.map((key) => [key, nodeStyle[key]]));
};

/**
 *
 * @param {Node} node
 * @param {Record<string, string>} styleDef
 */
const hasStyle = (node, styleDef) => {
    const nodeStyle = getStyle(node);
    if (!nodeStyle) {
        return false;
    }
    for (const [prop, value] of Object.entries(styleDef)) {
        if (nodeStyle[prop] !== value) {
            return false;
        }
    }
    return true;
};

/**
 * @param {string} modifier
 * @param {string} message
 */
const matcherModifierError = (modifier, message) =>
    new HootError(`cannot use modifier "${modifier}": ${message}`);

/**
 * @param {string} styleString
 * @returns {Record<string, string>}
 */
const parseStyle = (styleString) =>
    Object.fromEntries(styleString.split(";").map((prop) => prop.split(":").map((v) => v.trim())));

/**
 * @param {Assertion} assertion
 */
const registerAssertion = (assertion) => {
    currentResult.assertions.push(assertion);
    currentResult.pass &&= assertion.pass;
};

/**
 * @param {string} method
 */
const scopeError = (method) => new HootError(`cannot call \`${method}()\` outside of a test`);

/**
 * @param {string} name
 */
const step = (name) => {
    if (!currentResult) {
        throw scopeError("expect.step");
    }
    ensureArguments([[name, "string"]]);

    currentResult.steps.push(name);
};

const ACTUAL_REGEX = /%(actual)%/i;
const ELEMENTS_REGEX = /%(elements?)%/i;
const NOT_REGEX = /\[([\w\s]*)!([\w\s]*)\]/;
const RECEIVED_REGEX = /%(received)%/i;

/** @type {TestResult | null} */
let currentResult = null;
let currentStack = "";

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * @param {import("./runner").TestRunner} runner
 */
export function makeExpectFunction(runner) {
    /**
     * Main entry point to write assertions in tests.
     *
     * This function takes a value whose expected type depends on the following
     * matcher. See the documentation of each matcher for more information.
     *
     * Note that this function can only be called inside of a test.
     *
     * @template [R=unknown]
     * @param {R} received
     * @example
     *  expect([1, 2, 3]).toEqual(1, 2, 3);
     */
    function expect(received) {
        if (!currentResult) {
            throw scopeError("expect");
        }

        return new Matchers(received, {}, runner.config.headless);
    }

    return Object.assign(expect, {
        assertions,
        errors,
        extend,
        step,
        // Private members
        __after: afterTest,
        __before: beforeTest,
    });
}

export class Assertion {
    static nextId = 1;

    id = Assertion.nextId++;
    /** @type {[any, any][] | null} */
    info = null;
    label = "";
    message = "";
    /** @type {Modifiers<false>} */
    modifiers = { not: false, rejects: false, resolves: false };
    pass = false;
    ts = performance.now();

    /**
     * @param {Partial<Assertion>} values
     */
    constructor(values) {
        Object.assign(this, values);
    }
}

/**
 * @template R
 * @template [A=R]
 * @template [Async=false]
 */
export class Matchers {
    /** @type {Record<string, (...args: any[]) => MatcherSpecifications>} */
    static registry = Object.create(null);

    /** @type {A} */
    #actual = null;
    /** @type {R} */
    #received = null;
    #headless = false;
    /** @type {Modifiers<Async>} */
    #modifiers = {
        not: false,
        rejects: false,
        resolves: false,
    };

    /**
     * @param {R} received
     * @param {Modifiers<Async>} modifiers
     * @param {boolean} headless
     */
    constructor(received, modifiers, headless) {
        this.#received = received;
        this.#headless = headless;
        this.#modifiers = modifiers;

        for (const [fnName, fn] of Object.entries(this.constructor.registry)) {
            const resolve = this.#resolve.bind(this);
            const saveStack = this.#saveStack.bind(this);
            this[fnName] = {
                [fnName](...args) {
                    saveStack();
                    const result = fn(...args);
                    return resolve({ ...result, name: fnName });
                },
            }[fnName];
        }
    }

    //-------------------------------------------------------------------------
    // Modifiers
    //-------------------------------------------------------------------------

    /**
     * Returns a set of matchers expecting a result opposite to what normal matchers
     * would expect.
     *
     * @returns {Omit<Matchers<R, A, Async>, "not">}
     * @example
     *  expect(false).not.toBeTruthy();
     * @example
     *  expect("foo").not.toBe("bar");
     */
    get not() {
        if (this.#modifiers.not) {
            throw matcherModifierError("not", `matcher is already negated`);
        }
        return new Matchers(this.#received, { ...this.#modifiers, not: true }, this.#headless);
    }

    /**
     * Returns a set of matchers which will await the received value as a promise
     * and will be applied to a value rejected by that promise. The matcher will
     * throw an error should the promise resolve instead of being rejected.
     *
     * @returns {Omit<Matchers<R, A, true>, "rejects" | "resolves">}
     * @example
     *  await expect(Promise.reject("foo")).rejects.toBe("foo");
     */
    get rejects() {
        if (this.#modifiers.rejects || this.#modifiers.resolves) {
            throw matcherModifierError(
                "rejects",
                `matcher value has already been wrapped in a promise resolver`
            );
        }
        return new Matchers(this.#received, { ...this.#modifiers, rejects: true }, this.#headless);
    }

    /**
     * Returns a set of matchers which will await the received value as a promise
     * and will be applied to a value resolved by that promise. The matcher will
     * throw an error should the promise reject instead of being resolved.

     * @returns {Omit<Matchers<R, A, true>, "rejects" | "resolves">}
     * @example
     *  await expect(Promise.resolve("foo")).resolves.toBe("foo");
     */
    get resolves() {
        if (this.#modifiers.rejects || this.#modifiers.resolves) {
            throw matcherModifierError(
                "resolves",
                `matcher value has already been wrapped in a promise resolver`
            );
        }
        return new Matchers(this.#received, { ...this.#modifiers, resolves: true }, this.#headless);
    }

    //-------------------------------------------------------------------------
    // Standard matchers
    //-------------------------------------------------------------------------

    /**
     * Expects the received value to be strictly equal to the `expected` value.
     *
     * @param {R} expected
     * @param {ExpectOptions} [options]
     * @example
     *  expect("foo").toBe("foo");
     * @example
     *  expect({ foo: 1 }).not.toBe({ foo: 1 });
     */
    toBe(expected, options) {
        this.#saveStack();

        ensureArguments([
            [expected, "any"],
            [options, ["object", null]],
        ]);

        return this.#resolve({
            name: "toBe",
            acceptedType: "any",
            predicate: (actual) => strictEqual(actual, expected),
            message: (pass) =>
                options?.message ||
                (pass
                    ? `received value is[! not] strictly equal to %actual%`
                    : `expected values to be strictly equal`),
            details: (actual) => {
                const details = [
                    [Markup.green("Expected:"), expected],
                    [Markup.red("Received:"), actual],
                ];
                if (canDiff(actual) && canDiff(expected)) {
                    details.push([Markup.text("Diff:"), Markup.diff(expected, actual)]);
                }
                return details;
            },
        });
    }

    /**
     * Expects the received value to be empty:
     * - `iterable`: no items
     * - `object`: no keys
     * - `node`: no content (i.e. no value or text)
     * - anything else: falsy value (`false`, `0`, `""`, `null`, `undefined`)
     *
     * @param {ExpectOptions} [options]
     * @example
     *  expect({}).toBeEmpty();
     * @example
     *  expect(["a", "b"]).not.toBeEmpty();
     * @example
     *  expect(queryOne("input")).toBeEmpty();
     */
    toBeEmpty(options) {
        this.#saveStack();

        ensureArguments([[options, ["object", null]]]);

        return this.#resolve({
            name: "toBeEmpty",
            acceptedType: ["string", "node", "node[]"],
            predicate: isEmpty,
            message: (pass) =>
                options?.message ||
                (pass ? `%actual% is[! not] empty` : `%actual% should[! not] be empty`),
            details: (actual) => [[Markup.red("Received:"), actual]],
        });
    }

    /**
     * Expects the received value to be strictly greater than `min`.
     *
     * @param {number} min
     * @param {ExpectOptions} [options]
     * @example
     *  expect(5).toBeGreaterThan(-1);
     * @example
     *  expect(4 + 2).toBeGreaterThan(5);
     */
    toBeGreaterThan(min, options) {
        this.#saveStack();

        ensureArguments([
            [min, "number"],
            [options, ["object", null]],
        ]);

        return this.#resolve({
            name: "toBeGreaterThan",
            acceptedType: "number",
            predicate: (actual) => min < actual,
            message: (pass) =>
                options?.message ||
                (pass
                    ? `%actual% is[! not] strictly greater than ${formatHumanReadable(min)}`
                    : `expected value[! not] to be strictly greater`),
            details: (actual) => [
                [Markup.green("Minimum:"), min],
                [Markup.red("Received:"), actual],
            ],
        });
    }

    /**
     * Expects the received value to be strictly less than `max`.
     *
     * @param {number} max
     * @param {ExpectOptions} [options]
     * @example
     *  expect(5).toBeLessThan(10);
     * @example
     *  expect(8 - 6).toBeLessThan(3);
     */
    toBeLessThan(max, options) {
        this.#saveStack();

        ensureArguments([
            [max, "number"],
            [options, ["object", null]],
        ]);

        return this.#resolve({
            name: "toBeLessThan",
            acceptedType: "number",
            predicate: (actual) => actual < max,
            message: (pass) =>
                options?.message ||
                (pass
                    ? `%actual% is[! not] strictly less than ${formatHumanReadable(max)}`
                    : `expected value[! not] to be strictly less`),
            details: (actual) => [
                [Markup.green("Maximum:"), max],
                [Markup.red("Received:"), actual],
            ],
        });
    }

    /**
     * Expects the received value to be of the given type.
     *
     * @param {ArgumentType} type
     * @param {ExpectOptions} [options]
     * @example
     *  expect("foo").toBeOfType("");
     * @example
     *  expect({ foo: 1 }).toBeOfType("object");
     */
    toBeOfType(type, options) {
        this.#saveStack();

        ensureArguments([
            [type, "string"],
            [options, ["object", null]],
        ]);

        return this.#resolve({
            name: "toBeOfType",
            acceptedType: "any",
            predicate: (actual) => isOfType(actual, type),
            message: (pass) =>
                options?.message ||
                (pass
                    ? `%actual% is[! not] of type ${formatHumanReadable(type)}`
                    : `expected value to be of the given type`),
            details: (actual) => [
                [Markup.green("Expected type:"), type],
                [Markup.red("Received value:"), actual],
            ],
        });
    }

    /**
     * Expects the received value to resolve to a truthy expression.
     *
     * @param {ExpectOptions} [options]
     * @example
     *  expect(true).toBeTruthy();
     * @example
     *  expect([]).toBeTruthy();
     */
    toBeTruthy(options) {
        this.#saveStack();

        ensureArguments([[options, ["object", null]]]);

        return this.#resolve({
            name: "toBeTruthy",
            acceptedType: "any",
            predicate: Boolean,
            message: (pass) =>
                options?.message ||
                (pass ? `%actual% is[! not] truthy` : `expected value[! not] to be truthy`),
            details: (actual) => [[Markup.red("Received:"), actual]],
        });
    }

    /**
     * Expects the received value to be strictly between `min` (inclusive) and
     * `max` (exclusive).
     *
     * @param {number} min (inclusive)
     * @param {number} max (exlusive)
     * @param {ExpectOptions} [options]
     * @example
     *  expect(3).toBeWithin(3, 9);
     * @example
     *  expect(-8).toBeWithin(-20, 0);
     * @example
     *  expect(100).not.toBeWithin(50, 100);
     */
    toBeWithin(min, max, options) {
        this.#saveStack();

        ensureArguments([
            [min, "number"],
            [max, "number"],
            [options, ["object", null]],
        ]);

        if (min > max) {
            [min, max] = [max, min];
        }
        if (min === max) {
            throw new HootError(`min and max cannot be equal (did you mean to use \`toBe()\`?)`);
        }

        return this.#resolve({
            name: "toBeWithin",
            acceptedType: "number",
            predicate: (actual) => min <= actual && actual < max,
            message: (pass) =>
                options?.message ||
                (pass
                    ? `%actual% is[! not] between ${formatHumanReadable(
                          min
                      )} and ${formatHumanReadable(max)}`
                    : `expected value[! not] to be between given range`),
            details: (actual) => [
                [Markup.green("Expected:"), `${min} - ${max}`],
                [Markup.red("Received:"), actual],
            ],
        });
    }

    /**
     * Expects the received value to be deeply equal to the `expected` value.
     *
     * @param {R} expected
     * @param {ExpectOptions} [options]
     * @example
     *  expect(["foo"]).toEqual(["foo"]);
     * @example
     *  expect({ foo: 1 }).toEqual({ foo: 1 });
     */
    toEqual(expected, options) {
        this.#saveStack();

        ensureArguments([
            [expected, "any"],
            [options, ["object", null]],
        ]);

        return this.#resolve({
            name: "toEqual",
            acceptedType: "any",
            predicate: (actual) => {
                if (strictEqual(actual, expected)) {
                    console.warn(
                        ...hootLog(
                            `Called \`'toEqual()\` on strictly equal values. Did you mean to use \`toBe()\`?`
                        )
                    );
                    return true;
                }
                return deepEqual(actual, expected);
            },
            message: (pass) =>
                options?.message ||
                (pass
                    ? `received value is[! not] deeply equal to %actual%`
                    : `expected values to be deeply equal`),
            details: (actual) => {
                const details = [
                    [Markup.green("Expected:"), expected],
                    [Markup.red("Received:"), actual],
                ];
                if (canDiff(actual) && canDiff(expected)) {
                    details.push([Markup.text("Diff:"), Markup.diff(expected, actual)]);
                }
                return details;
            },
        });
    }

    /**
     * Expects the received value to match the given matcher (string or RegExp).
     *
     * @param {import("../hoot_utils").Matcher} matcher
     * @param {ExpectOptions} [options]
     * @example
     *  expect(new Error("foo")).toMatch("foo");
     * @example
     *  expect("a foo value").toMatch(/fo.*ue/);
     */
    toMatch(matcher, options) {
        this.#saveStack();

        ensureArguments([
            [matcher, "any"],
            [options, ["object", null]],
        ]);

        return this.#resolve({
            name: "toMatch",
            acceptedType: "any",
            predicate: (actual) => match(actual, matcher),
            message: (pass) =>
                options?.message ||
                (pass
                    ? `%actual% [matches!does not match] ${formatHumanReadable(matcher)}`
                    : `expected value[! not] to match the given matcher`),
            details: (actual) => [
                [Markup.green("Matcher:"), matcher],
                [Markup.red("Received:"), actual],
            ],
        });
    }

    /**
     * Expects the received value to satisfy the given predicate, taking the received
     * value as argument.
     *
     * @param {(received: R) => boolean} predicate
     * @param {ExpectOptions} [options]
     * @example
     *  expect("foo").toSatisfy((value) => typeof value === "string");
     * @example
     *  expect(false).not.toSatisfy(Boolean);
     */
    toSatisfy(predicate, options) {
        this.#saveStack();

        ensureArguments([
            [predicate, "function"],
            [options, ["object", null]],
        ]);

        return this.#resolve({
            name: "toSatisfy",
            acceptedType: "any",
            predicate,
            message: (pass) =>
                options?.message ||
                (pass
                    ? `%actual% [satisfies!does not satisfy] the predicate ${formatHumanReadable(
                          predicate
                      )}`
                    : `expected value[! not] to satisfy the predicate`),
            details: (actual) => [
                [Markup.green("Expected:"), true],
                [Markup.red("Received:"), actual],
                [Markup.text("Predicate:"), predicate],
            ],
        });
    }

    /**
     * Expects the received value (`Function`) to throw an error after being called.
     *
     * @param {import("../hoot_utils").Matcher} [matcher=Error]
     * @param {ExpectOptions} [options]
     * @example
     *  expect(() => { throw new Error("Woops!") }).toThrow(/woops/i);
     * @example
     *  await expect(Promise.reject("foo")).rejects.toThrow("foo");
     */
    toThrow(matcher = Error, options) {
        this.#saveStack();

        ensureArguments([
            [matcher, "any"],
            [options, ["object", null]],
        ]);

        let name;
        return this.#resolve({
            name: "toThrow",
            acceptedType: ["function", "error"],
            transform: (received) => {
                name = received.name || "anonymous function";
                const { rejects, resolves } = this.#modifiers;
                if (rejects || resolves) {
                    return received;
                }
                try {
                    return received();
                } catch (error) {
                    return error;
                }
            },
            predicate: (actual) => match(actual, matcher),
            message: (pass) => {
                if (options?.message) {
                    return options.message;
                }
                const { rejects, resolves } = this.#modifiers;
                return pass
                    ? `${name} did[! not] ${
                          rejects || resolves ? "reject" : "throw"
                      } a matching value`
                    : `${name} ${
                          rejects || resolves ? "rejected" : "threw"
                      } a value that did not match the given matcher`;
            },
            details: (actual) => [
                [Markup.green("Matcher:"), matcher],
                [Markup.red("Received:"), actual],
            ],
        });
    }

    /**
     * Expects the received matchers to match the errors thrown since the start
     * of the test or the last call to {@link toVerifyErrors}. Calling this matcher
     * will reset the list of current errors.
     *
     * @param {ExpectOptions} [options]
     * @example
     *  expect([/RPCError/, /Invalid domain AST/]).toVerifyErrors();
     */
    toVerifyErrors(options) {
        this.#saveStack();

        ensureArguments([[options, ["object", null]]]);

        let receivedErrors;
        return this.#resolve({
            name: "toVerifyErrors",
            acceptedType: ["string[]", "regex[]"],
            predicate: (actual) => {
                receivedErrors = currentResult.errors;
                currentResult.errors = [];
                return receivedErrors.every((error, i) => !actual[i] || match(error, actual[i]));
            },
            message: (pass) =>
                options?.message ||
                (pass
                    ? receivedErrors.length
                        ? receivedErrors.map(formatHumanReadable).join(" > ")
                        : "no errors"
                    : `expected the following errors`),
            details: (actual) => [
                [Markup.green("Expected:"), actual],
                [Markup.red("Received:"), receivedErrors],
                [Markup.text("Diff:"), Markup.diff(actual, receivedErrors)],
            ],
        });
    }

    /**
     * Expects the received steps to be equal to the steps emitted since the start
     * of the test or the last call to {@link toVerifySteps}. Calling this matcher
     * will reset the list of current steps.
     *
     * @param {ExpectOptions} [options]
     * @example
     *  expect(["web_read_group", "web_search_read"]).toVerifySteps();
     */
    toVerifySteps(options) {
        this.#saveStack();

        ensureArguments([[options, ["object", null]]]);

        let receivedSteps;
        return this.#resolve({
            name: "toVerifySteps",
            acceptedType: "string[]",
            predicate: (actual) => {
                receivedSteps = currentResult.steps;
                currentResult.steps = [];
                return deepEqual(actual, receivedSteps);
            },
            message: (pass) =>
                options?.message ||
                (pass
                    ? receivedSteps.length
                        ? receivedSteps.map(formatHumanReadable).join(" -> ")
                        : "no steps"
                    : `expected the following steps`),
            details: (actual) => [
                [Markup.green("Expected:"), actual],
                [Markup.red("Received:"), receivedSteps],
                [Markup.text("Diff:"), Markup.diff(actual, receivedSteps)],
            ],
        });
    }

    //-------------------------------------------------------------------------
    // DOM matchers
    //-------------------------------------------------------------------------

    /**
     * Expects the received {@link Target} to be checked, or to be indeterminate
     * if the homonymous option is set to `true`.
     *
     * @param {ExpectOptions & { indeterminate?: boolean }} [options]
     * @example
     *  expect("input[type=checkbox]").toBeChecked();
     */
    toBeChecked(options) {
        this.#saveStack();

        ensureArguments([[options, ["object", null]]]);

        const prop = options?.indeterminate ? "indeterminate" : "checked";
        return this.#resolve({
            name: "toBeChecked",
            acceptedType: ["string", "node", "node[]"],
            transform: queryAll,
            predicate: each((node) => node.matches?.(":" + prop)),
            message: (pass) =>
                options?.message ||
                (pass
                    ? `%elements% are[! not] ${prop}`
                    : `expected %elements%[! not] to be ${prop}`),
            details: (actual) => [[Markup.red("Received:"), actual.map((node) => node[prop])]],
        });
    }

    /**
     * Expects the received {@link Target} to be displayed, meaning that:
     * - it has a bounding box;
     * - it is contained in the root document.
     *
     * @param {ExpectOptions} [options]
     * @example
     *  expect(document.body).toBeDisplayed();
     * @example
     *  expect(document.createElement("div")).not.toBeDisplayed();
     */
    toBeDisplayed(options) {
        this.#saveStack();

        ensureArguments([[options, ["object", null]]]);

        return this.#resolve({
            name: "toBeDisplayed",
            acceptedType: ["string", "node", "node[]"],
            transform: queryAll,
            predicate: isDisplayed,
            message: (pass) =>
                options?.message ||
                (pass
                    ? `%elements% are[! not] displayed`
                    : `expected %elements%[! not] to be displayed`),
            details: (actual) => {
                const displayed = [];
                const notDisplayed = [];
                for (const node of actual) {
                    if (isDisplayed(node)) {
                        displayed.push(node);
                    } else {
                        notDisplayed.push(node);
                    }
                }
                return [
                    [Markup.green("Displayed:"), displayed],
                    [Markup.red("Not displayed:"), notDisplayed],
                ];
            },
        });
    }

    /**
     * Expects the received {@link Target} to be enabled, meaning that it
     * matches the `:enabled` pseudo-selector.
     *
     * @param {ExpectOptions} [options]
     * @example
     *  expect("button").toBeEnabled();
     * @example
     *  expect("input[type=radio]").not.toBeEnabled();
     */
    toBeEnabled(options) {
        this.#saveStack();

        ensureArguments([[options, ["object", null]]]);

        return this.#resolve({
            name: "toBeEnabled",
            acceptedType: ["string", "node", "node[]"],
            transform: queryAll,
            predicate: each((node) => node.matches?.(":enabled")),
            message: (pass) =>
                options?.message ||
                (pass
                    ? `%elements% are [enabled!disabled]`
                    : `expected %elements% to be [enabled!disabled]`),
            details: (actual) => [[Markup.red("Received:"), actual]],
        });
    }

    /**
     * Expects the received {@link Target} to be focused in its owner document.
     *
     * @param {ExpectOptions} [options]
     */
    toBeFocused(options) {
        this.#saveStack();

        ensureArguments([[options, ["object", null]]]);

        return this.#resolve({
            name: "toBeFocused",
            acceptedType: ["string", "node", "node[]"],
            transform: queryAll,
            predicate: each((node) => node === getActiveElement(node)),
            message: (pass) =>
                options?.message ||
                (pass ? `%elements% are[! not] focused` : `%elements% should[! not] be focused`),
            details: (actual) => [
                [Markup.green("Focused:"), getActiveElement(actual)],
                [Markup.red("Received:"), actual],
            ],
        });
    }

    /**
     * Expects the received {@link Target} to be visible, meaning that:
     * - it has a bounding box;
     * - it is contained in the root document;
     * - it is not hidden by CSS properties.
     *
     * @param {ExpectOptions} [options]
     * @example
     *  expect(document.body).toBeVisible();
     * @example
     *  expect("[style='opacity: 0']").not.toBeVisible();
     */
    toBeVisible(options) {
        this.#saveStack();

        ensureArguments([[options, ["object", null]]]);

        return this.#resolve({
            name: "toBeVisible",
            acceptedType: ["string", "node", "node[]"],
            transform: queryAll,
            predicate: isVisible,
            message: (pass) =>
                options?.message ||
                (pass
                    ? `%elements% are [visible!hidden]`
                    : `expected %elements% to be [visible!hidden]`),
            details: (actual) => {
                const visible = [];
                const hidden = [];
                for (const node of actual) {
                    if (isDisplayed(node)) {
                        visible.push(node);
                    } else {
                        hidden.push(node);
                    }
                }
                const details = [];
                if (visible.length) {
                    details.push([Markup.green("Visible:"), visible]);
                }
                if (hidden.length) {
                    details.push([Markup.red("Hidden:"), hidden]);
                }
                return details;
            },
        });
    }

    /**
     * Expects the received {@link Target} to contain the given {@link Target}.
     *
     * @param {Target} target
     * @param {ExpectOptions} [options]
     * @example
     *  expect("ul").toContain(queryOne("li"));
     */
    toContain(target, options) {
        this.#saveStack();

        ensureArguments([
            [target, ["string", "node", "node[]"]],
            [options, ["object", null]],
        ]);

        const nodes = queryAll(target);
        return this.#resolve({
            name: "toContain",
            acceptedType: ["string", "node", "node[]"],
            transform: queryAll,
            predicate: each((node) => nodes.every((n) => node.contains(n))),
            message: (pass) =>
                options?.message ||
                (pass
                    ? `%elements% [contain!do not contain] ${formatHumanReadable(nodes)}`
                    : `expected %elements%[! not] to contain the given value`),
            details: (actual) => {
                const contained = [];
                const missing = [];
                for (const node of nodes) {
                    if (actual.some((n) => n.contains(node))) {
                        contained.push(node);
                    } else {
                        missing.push(node);
                    }
                }
                return [
                    [Markup.green("Contained:"), contained],
                    [Markup.red("Missing:"), missing],
                ];
            },
        });
    }

    /**
     * Expects the received {@link Target} to have the given attribute set on
     * itself, and for that attribute value to match the given `value` if any.
     *
     * @param {string} attribute
     * @param {import("../hoot_utils").Matcher} [value]
     * @param {ExpectOptions} [options]
     * @example
     *  expect("a").toHaveAttribute("href");
     * @example
     *  expect("script").toHaveAttribute("src", "./index.js");
     */
    toHaveAttribute(attribute, value, options) {
        this.#saveStack();

        ensureArguments([
            [attribute, ["string"]],
            [value, ["string", "number", "regex", null]],
            [options, ["object", null]],
        ]);

        const expectsValue = !isNil(value);
        return this.#resolve({
            name: "toHaveAttribute",
            acceptedType: ["string", "node", "node[]"],
            transform: queryAll,
            predicate: each((node) =>
                expectsValue
                    ? match(node.getAttribute(attribute), value)
                    : node.hasAttribute(attribute)
            ),
            message: (pass) =>
                options?.message ||
                (pass
                    ? `attribute ${formatHumanReadable(attribute)} on %actual% ${
                          expectsValue
                              ? `[matches!does not match] ${formatHumanReadable(value)}`
                              : "is[! not] set"
                      }`
                    : `element does not have the correct attribute${expectsValue ? " value" : ""}`),
            details: (actual) => {
                const attrValue = actual[0].getAttribute(attribute);
                const details = [
                    [Markup.green("Expected:"), value],
                    [Markup.red("Received:"), attrValue],
                ];
                if (canDiff(attrValue) && canDiff(value)) {
                    details.push([Markup.text("Diff:"), Markup.diff(value, attrValue)]);
                }
                return details;
            },
        });
    }

    /**
     * Expects the received {@link Target} to have the given class name(s).
     *
     * @param {string | string[]} className
     * @param {ExpectOptions} [options]
     * @example
     *  expect("button").toHaveClass("btn");
     * @example
     *  expect("body").toHaveClass(["o_webclient", "o_dark"]);
     */
    toHaveClass(className, options) {
        this.#saveStack();

        ensureArguments([
            [className, ["string", "string[]"]],
            [options, ["object", null]],
        ]);

        const rawClassNames = ensureArray(className);
        const classNames = rawClassNames.flatMap((cls) => cls.trim().split(/\s+/g));

        return this.#resolve({
            name: "toHaveClass",
            acceptedType: ["string", "node", "node[]"],
            transform: queryAll,
            predicate: each((node) => classNames.every((cls) => node.classList.contains(cls))),
            message: (pass) =>
                options?.message ||
                (pass
                    ? `%elements% [have!do not have] classes ${and(
                          ...classNames.map(formatHumanReadable)
                      )}`
                    : `expected %elements% [to have all!not to have any] of the given class names`),
            details: (actual) => [
                [Markup.green("Expected:"), classNames],
                [Markup.red("Received:"), actual.flatMap((node) => [...node.classList])],
            ],
        });
    }

    /**
     * Expects the received {@link Target} to contain a certain `amount` of elements:
     * - {@link Number}: exactly `<amount>` element(s)
     * - {@link false}: any amount of matching elements
     *
     * Note that the `amount` parameter can be omitted, in which case it will be
     * implicitly resolved as `false` (= any).
     *
     * @param {number | false} [amount]
     * @param {ExpectOptions} [options]
     * @example
     *  expect(".o_webclient").toHaveCount(1);
     * @example
     *  expect(".o_form_view .o_field_widget").toHaveCount();
     * @example
     *  expect("ul > li").toHaveCount(4);
     */
    toHaveCount(amount, options) {
        this.#saveStack();

        if (isNil(amount)) {
            amount = false;
        }

        ensureArguments([
            [amount, ["integer"]],
            [options, ["object", null]],
        ]);

        return this.#resolve({
            name: "toHaveCount",
            acceptedType: ["string", "node", "node[]"],
            transform: queryAll,
            predicate: (node) =>
                amount === false ? node.length > 0 : strictEqual(node.length, amount),
            message: (pass) =>
                options?.message ||
                (pass
                    ? `there are[! not] ${amount} %elements%`
                    : `there is an incorrect amount of %elements%`),
            details: (actual) => [
                [Markup.green("Expected:"), amount === false ? "any" : amount],
                [Markup.red("Received:"), actual.length],
                [Markup.red("Nodes:"), actual],
            ],
        });
    }

    /**
     * Expects the received {@link Target} to have the given attribute set on
     * itself, and for that attribute value to match the given `value` if any.
     *
     * @param {string} property
     * @param {string} [value]
     * @param {ExpectOptions} [options]
     * @example
     *  expect("button").toHaveProperty("tabIndex", 0);
     * @example
     *  expect("script").toHaveProperty("src", "./index.js");
     */
    toHaveProperty(property, value, options) {
        this.#saveStack();

        ensureArguments([
            [property, ["string"]],
            [value, ["any"]],
            [options, ["object", null]],
        ]);

        const expectsValue = !isNil(value);

        return this.#resolve({
            name: "toHaveAttribute",
            acceptedType: ["string", "node", "node[]"],
            transform: queryAll,
            predicate: each((node) =>
                expectsValue ? strictEqual(node[property], value) : !isNil(node[property])
            ),
            message: (pass) =>
                options?.message ||
                (pass
                    ? `property ${formatHumanReadable(property)} on %elements% ${
                          expectsValue
                              ? `[matches!does not match] ${formatHumanReadable(value)}`
                              : "is[! not] set"
                      }`
                    : `%elements% do not have the correct property${expectsValue ? " value" : ""}`),
            details: (actual) => {
                const propValue = actual[property];
                const details = [
                    [Markup.green("Expected:"), value],
                    [Markup.red("Received:"), propValue],
                ];
                if (canDiff(propValue) && canDiff(value)) {
                    details.push([Markup.text("Diff:"), Markup.diff(value, propValue)]);
                }
                return details;
            },
        });
    }

    /**
     * Expects the received {@link Target} to have the given class name(s).
     *
     * @param {string | string[]} style
     * @param {ExpectOptions} [options]
     * @example
     *  expect("button").toHaveStyle({ color: "red" });
     * @example
     *  expect("p").toHaveStyle("text-align: center");
     */
    toHaveStyle(style, options) {
        this.#saveStack();

        ensureArguments([
            [style, ["string", "object"]],
            [options, ["object", null]],
        ]);

        const styleDef = typeof style === "string" ? parseStyle(style) : style;
        return this.#resolve({
            name: "toHaveStyle",
            acceptedType: ["string", "node", "node[]"],
            transform: queryAll,
            predicate: each((node) => hasStyle(node, styleDef)),
            message: (pass) =>
                options?.message ||
                (pass
                    ? `%elements% have the expected style values for ${and(
                          ...Object.keys(styleDef).map(formatHumanReadable)
                      )}`
                    : `expected %elements% [to have all!not to have any] of the given style properties`),
            details: (actual) => [
                [Markup.green("Expected:"), styleDef],
                [Markup.red("Received:"), getStyleValues(actual, Object.keys(styleDef))],
            ],
        });
    }

    /**
     * Expects the text content of the received {@link Target} to either:
     * - be strictly equal to a given string,
     * - match a given regular expression;
     *
     * @param {string | RegExp} [text]
     * @param {ExpectOptions} [options]
     * @example
     *  expect("p").toHaveText("lorem ipsum dolor sit amet");
     * @example
     *  expect("header h1").toHaveText(/odoo/i);
     */
    toHaveText(text, options) {
        this.#saveStack();

        ensureArguments([
            [text, ["string", "regex", null]],
            [options, ["object", null]],
        ]);

        const texts = ensureArray(text);
        const expectsText = isNil(text);
        return this.#resolve({
            name: "toHaveText",
            acceptedType: ["string", "node", "node[]"],
            transform: queryAll,
            predicate: each((node) => {
                const nodeText = getNodeText(node);
                if (expectsText) {
                    return nodeText.length > 0;
                }
                return texts.every((text) => {
                    if (text instanceof RegExp) {
                        return text.test(nodeText);
                    }
                    return strictEqual(nodeText, text);
                });
            }),
            message: (pass) =>
                options?.message ||
                (pass
                    ? `%elements% [have!do not have] text ${formatHumanReadable(text)}`
                    : `expected %elements%[! not] to have the given text`),
            details: (actual) => {
                const nodeTexts = actual.map(getNodeText);
                const details = [
                    [Markup.green("Expected:"), texts],
                    [Markup.red("Received:"), nodeTexts],
                ];
                if (canDiff(texts) && canDiff(nodeTexts)) {
                    details.push([Markup.text("Diff:"), Markup.diff(texts, nodeTexts)]);
                }
                return details;
            },
        });
    }

    /**
     * Expects the value of the received {@link Target} to either:
     * - be strictly equal to a given string or number,
     * - match a given regular expression,
     * - contain file objects matching the given `files` list;
     *
     * @param {ReturnType<typeof getNodeValue>} [value]
     * @param {ExpectOptions} [options]
     * @example
     *  expect("input[type=email]").toHaveValue("john@doe.com");
     * @example
     *  expect("input[type=file]").toHaveValue(new File(["foo"], "foo.txt"));
     * @example
     *  expect("select[multiple]").toHaveValue(["foo", "bar"]);
     */
    toHaveValue(value, options) {
        this.#saveStack();

        ensureArguments([
            [value, ["string", "string[]", "number", "object[]", "regex", null]],
            [options, ["object", null]],
        ]);

        const values = ensureArray(value);
        const expectsValue = !isNil(value);
        return this.#resolve({
            name: "toHaveValue",
            acceptedType: ["string", "node", "node[]"],
            transform: queryAll,
            predicate: each((node) => {
                if (isCheckable(node)) {
                    throw new HootError(
                        `cannot call \`toHaveValue()\` on a checkbox or radio input: use \`toBeChecked()\` instead`
                    );
                }
                let nodeValue = getNodeValue(node);
                if (!expectsValue) {
                    return isIterable(nodeValue) ? [...nodeValue].length > 0 : node.value !== "";
                }
                if (isIterable(nodeValue)) {
                    if (isIterable(value)) {
                        return deepEqual(nodeValue, values);
                    }
                    nodeValue = node.value;
                }
                return values.every((value) => {
                    if (value instanceof RegExp) {
                        return value.test(nodeValue);
                    }
                    return strictEqual(nodeValue, value);
                });
            }),
            message: (pass) =>
                options?.message ||
                (pass
                    ? `%elements% [have!do not have] value ${formatHumanReadable(value)}`
                    : `expected %elements%[! not] to have the given value`),
            details: (actual) => {
                const nodeValues = actual.map(getNodeValue);
                const details = [
                    [Markup.green("Expected:"), values],
                    [Markup.red("Received:"), nodeValues],
                ];
                if (canDiff(values) && canDiff(nodeValues)) {
                    details.push([Markup.text("Diff:"), Markup.diff(values, nodeValues)]);
                }
                return details;
            },
        });
    }

    //-------------------------------------------------------------------------
    // Private methods
    //-------------------------------------------------------------------------

    /**
     * @param {MatcherSpecifications<R, A>} specs
     * @returns {Async extends true ? Promise<void> : void}
     */
    #resolve(specs) {
        if (this.#modifiers.rejects || this.#modifiers.resolves) {
            return Promise.resolve(this.#received)
                .then(
                    /** @param {PromiseFulfilledResult<R>} reason */
                    (result) => {
                        if (this.#modifiers.rejects) {
                            throw new HootError(
                                `expected promise to reject, instead resolved with: ${result}`
                            );
                        }
                        this.#received = result;
                        return this.#resolveFinalResult(specs);
                    }
                )
                .catch(
                    /** @param {PromiseRejectedResult} reason */
                    (reason) => {
                        if (this.#modifiers.resolves) {
                            throw new HootError(
                                `expected promise to resolve, instead rejected with: ${reason}`,
                                { cause: reason }
                            );
                        }
                        this.#received = reason;
                        return this.#resolveFinalResult(specs);
                    }
                );
        } else {
            return this.#resolveFinalResult(specs);
        }
    }

    /**
     * @param {MatcherSpecifications<R, A>} specs
     * @returns {void}
     */
    #resolveFinalResult({ acceptedType, name, details, message, predicate, transform }) {
        const received = this.#received;
        const types = ensureArray(acceptedType);
        if (!types.some((type) => isOfType(received, type))) {
            const strTypes = types.map(formatHumanReadable);
            const last = strTypes.pop();
            throw new TypeError(
                `expected received value to be of type ${[strTypes.join(", "), last]
                    .filter(Boolean)
                    .join(" or ")}, got ${formatHumanReadable(received)}`
            );
        }

        const actual = transform ? transform(received) : received;
        const { not } = this.#modifiers;
        let pass = predicate(actual);
        if (not) {
            pass = !pass;
        }

        const assertion = new Assertion({
            label: name,
            message: formatMessage(message(pass), { actual, not, received }),
            modifiers: this.#modifiers,
            pass,
        });
        if (!pass) {
            const formattedStack = formatStack(currentStack);
            const stackContent = Markup.text(formattedStack, { technical: true });
            assertion.info = [...details(actual), [Markup.red("Source:"), stackContent]];
        }

        registerAssertion(assertion);
    }

    #saveStack() {
        if (!this.#headless) {
            currentStack = new Error().stack;
        }
    }

    /**
     * Extends the available matchers methods with a given function.
     *
     * @param {(...args: any[]) => MatcherSpecifications<any>} matcher
     */
    static extend(matcher) {
        ensureArguments([[matcher, "function"]]);

        const { name } = matcher;
        if (!name) {
            throw new TypeError(`matcher must be a named function`);
        }
        if (this.registry[name]) {
            throw new HootError(`a matcher with the name "${name}" already exists`);
        }

        this.registry[name] = matcher;
    }
}

export class TestResult {
    aborted = false;
    /** @type {Assertion[]} */
    assertions = [];
    duration = 0;
    /** @type {Error[]} */
    errors = [];
    expectedAssertions = 0;
    expectedErrors = 0;
    pass = true;
    /** @type {string[]} */
    steps = [];
    ts = performance.now();
}
