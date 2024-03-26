/** @odoo-module */
/* eslint-disable no-restricted-syntax */

import {
    getActiveElement,
    getNodeAttribute,
    getNodeText,
    getNodeValue,
    getNodeRect,
    getStyle,
    isCheckable,
    isDisplayed,
    isEmpty,
    isNode,
    isVisible,
    queryAll,
    queryRect,
} from "@web/../lib/hoot-dom/helpers/dom";
import { isFirefox, isIterable } from "@web/../lib/hoot-dom/hoot_dom_utils";
import {
    HootError,
    Markup,
    deepEqual,
    ensureArguments,
    ensureArray,
    formatHumanReadable,
    isNil,
    isOfType,
    match,
    strictEqual,
} from "../hoot_utils";
import { logger } from "./logger";
import { Test } from "./test";

/**
 *
 * @typedef {{
 *  aborted?: boolean;
 *  debug?: boolean;
 * }} AfterTestOptions
 *
 * @typedef {import("../hoot_utils").ArgumentType} ArgumentType
 *
 * @typedef {{
 *  headless: boolean;
 * }} ExpectBuilderParams
 *
 * @typedef {{
 *  message?: string;
 * }} ExpectOptions
 *
 * @typedef {import("@odoo/hoot-dom").Dimensions} Dimensions
 * @typedef {import("@odoo/hoot-dom").Position} Position
 * @typedef {import("@odoo/hoot-dom").QueryRectOptions} QueryRectOptions
 * @typedef {import("@odoo/hoot-dom").QueryTextOptions} QueryTextOptions
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

const {
    Array: { isArray: $isArray },
    Boolean,
    Error,
    Object: { assign: $assign, fromEntries: $fromEntries, entries: $entries, keys: $keys },
    Promise,
    TypeError,
    performance,
} = globalThis;
/** @type {Performance["now"]} */
const $now = performance.now.bind(performance);

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @param {Test} test
 * @param {AfterTestOptions} options
 */
const afterTest = (test, options) => {
    currentResult.duration = $now() - currentResult.ts;

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
    const errorCount = currentResult.caughtErrors;
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

    if (options?.aborted) {
        registerAssertion(
            new Assertion({
                label: "aborted",
                message: `test was aborted, results may not be relevant`,
                pass: false,
            })
        );
    }

    // Set test status
    if (options?.aborted) {
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

    if (!options?.debug) {
        currentResult = null;
    }
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
 * @param {Test} test
 */
const beforeTest = (test) => {
    test.results.push(new TestResult(test));

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

/**
 * @param {Error} [error]
 */
const formatError = (error) => {
    let strError = error ? String(error) : "";
    if (error?.cause) {
        strError += `\n${formatError(error.cause)}`;
    }
    return strError;
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
 * @param {Iterable<any> | Record<any, any>} object
 */
const getLength = (object) => {
    if (typeof object === "string" || $isArray(object)) {
        return object.length;
    }
    if (isIterable(object)) {
        return [...object].length;
    }
    return $keys(object).length;
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
    return $fromEntries(
        keys.map((key) => [
            key,
            key.includes("-") ? nodeStyle.getPropertyValue(key) : nodeStyle[key],
        ])
    );
};

/**
 *
 * @param {Node} node
 * @param {Record<string, string | RegExp>} styleDef
 */
const hasStyle = (node, styleDef) => {
    const nodeStyle = getStyleValues(node, $keys(styleDef));
    for (const [prop, value] of $entries(styleDef)) {
        if (!regexMatchOrStrictEqual(nodeStyle[prop], value)) {
            return false;
        }
    }
    return true;
};

/**
 * @param {Iterable<any> | Record<any, any>} object
 * @param {any} item
 * @returns {boolean}
 */
const includes = (object, item) => {
    if (typeof object === "string") {
        return object.includes(item);
    }
    if ($isArray(object)) {
        // Standard case: array
        return object.some((i) => deepEqual(i, item));
    }
    if (isIterable(object)) {
        // Iterables: cast to array
        return includes([...object], item);
    }
    if ($isArray(item) && item.length === 2) {
        return includes($entries(object), item);
    }
    return includes($keys(object), item);
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
    $fromEntries(styleString.split(";").map((prop) => prop.split(":").map((v) => v.trim())));

/**
 * @param {unknown} value
 * @param {string | RegExp} matcher
 */
const regexMatchOrStrictEqual = (value, matcher) =>
    matcher instanceof RegExp ? matcher.test(value) : strictEqual(value, matcher);

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
 * @param {ExpectBuilderParams} params
 * @returns {[typeof enrichedExpect, typeof expectHooks]}
 */
export function makeExpect(params) {
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

        return new Matchers(received, {}, params.headless);
    }

    const enrichedExpect = $assign(expect, {
        assertions,
        errors,
        step,
    });
    const expectHooks = {
        after: afterTest,
        before: beforeTest,
    };

    return [enrichedExpect, expectHooks];
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
    ts = $now();

    /**
     * @param {Partial<Assertion>} values
     */
    constructor(values) {
        $assign(this, values);
    }
}

/**
 * @template R
 * @template [A=R]
 * @template [Async=false]
 */
export class Matchers {
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
     *  expect([1]).not.toBeEmpty();
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
            acceptedType: ["any"],
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
     * Expects the received value to be an instance of the given `cls`.
     *
     * @param {Function} cls
     * @param {ExpectOptions} [options]
     * @example
     *  expect({ foo: 1 }).not.toBeInstanceOf(Object);
     * @example
     *  expect(document.createElement("div")).toBeInstanceOf(HTMLElement);
     */
    toBeInstanceOf(cls, options) {
        this.#saveStack();

        ensureArguments([
            [cls, "function"],
            [options, ["object", null]],
        ]);

        return this.#resolve({
            name: "toBeInstanceOf",
            acceptedType: "any",
            predicate: (actual) => actual instanceof cls,
            message: (pass) =>
                options?.message ||
                (pass
                    ? `%actual% is[! not] an instance of ${cls.name}`
                    : `expected value[! not] to be an instance of the given class`),
            details: (actual) => [
                [Markup.green("Expected:"), cls],
                [Markup.red("Actual parent class:"), actual.constructor.name],
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
     *  expect("foo").toBeOfType("string");
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
                    logger.warn(
                        `Called \`'toEqual()\` on strictly equal values in "${currentResult.test.fullName}". Did you mean to use \`toBe()\`?`
                    );
                    return true;
                }
                return deepEqual(actual, expected);
            },
            message: (pass) =>
                options?.message ||
                (pass
                    ? `received value is[! not] deeply equal to %actual%`
                    : `expected values to[! not] be deeply equal`),
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
     * Expects the received value to have a length of the given `length`.
     *
     * Received value can be a string, an iterable or an object.
     *
     * @param {number} length
     * @param {ExpectOptions} options
     * @example
     *  expect("foo").toHaveLength(3);
     * @example
     *  expect([1, 2, 3]).toHaveLength(3);
     * @example
     *  expect({ foo: 1, bar: 2 }).toHaveLength(2);
     * @example
     *  expect(new Set([1, 2])).toHaveLength(2);
     */
    toHaveLength(length, options) {
        this.#saveStack();

        ensureArguments([
            [length, "integer"],
            [options, ["object", null]],
        ]);

        return this.#resolve({
            name: "toHaveLength",
            acceptedType: ["string", "array", "object"],
            predicate: (actual) => getLength(actual) === length,
            message: (pass) =>
                options?.message ||
                (pass
                    ? `%actual% has[! not] a length of ${formatHumanReadable(length)}`
                    : `expected value[! not] to have the given length`),
            details: (actual) => [
                [Markup.green("Expected length:"), length],
                [Markup.red("Received:"), getLength(actual)],
            ],
        });
    }

    /**
     * Expects the received value to include an `item` of a given shape.
     *
     * Received value can be an iterable or an object (in case it is an object,
     * the `item` should be a key or a tuple representing an entry in that object).
     *
     * Note that it is NOT a strict comparison: the item will be matched for deep
     * equality against each item of the iterable.
     *
     * @param {keyof R | R[number]} item
     * @param {ExpectOptions} options
     * @example
     *  expect([1, 2, 3]).toInclude(2);
     * @example
     *  expect({ foo: 1, bar: 2 }).toInclude("foo");
     * @example
     *  expect({ foo: 1, bar: 2 }).toInclude(["foo", 1]);
     * @example
     *  expect(new Set([{ foo: 1 }, { bar: 2 }])).toInclude({ bar: 2 });
     */
    toInclude(item, options) {
        this.#saveStack();

        ensureArguments([
            [item, "any"],
            [options, ["object", null]],
        ]);

        return this.#resolve({
            name: "toInclude",
            acceptedType: ["string", "any[]", "object"],
            predicate: (actual) => includes(actual, item),
            message: (pass) =>
                options?.message ||
                (pass
                    ? `%actual% [includes!does not include] ${formatHumanReadable(item)}`
                    : `expected object[! not] to include the given item`),
            details: (actual) => [
                [Markup.green("Object:"), actual],
                [Markup.red("Item:"), item],
            ],
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
            predicate: (expected) => {
                receivedErrors = currentResult.errors;
                currentResult.errors = [];
                return (
                    receivedErrors.length === expected.length &&
                    receivedErrors.every(
                        (error, i) =>
                            match(error, expected[i]) ||
                            (error.cause && match(error.cause, expected[i]))
                    )
                );
            },
            message: (pass) =>
                options?.message ||
                (pass
                    ? receivedErrors.length
                        ? receivedErrors.map(formatHumanReadable).join(" > ")
                        : "no errors"
                    : `expected the following errors`),
            details: (actual) => {
                const fActual = actual.map(formatError);
                const fReceived = receivedErrors.map(formatError);
                return [
                    [Markup.green("Expected:"), fActual],
                    [Markup.red("Received:"), fReceived],
                    [Markup.text("Diff:"), Markup.diff(fActual, fReceived)],
                ];
            },
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
            predicate: each((node) => {
                if (!expectsValue) {
                    return node.hasAttribute(attribute);
                }
                const attrValue = getNodeAttribute(node, attribute);
                return regexMatchOrStrictEqual(attrValue, value);
            }),
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
                const attrValue = getNodeAttribute(actual[0], attribute);
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
     *  expect("button").toHaveClass("btn btn-primary");
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
     * @param {any} [value]
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
            predicate: each((node) => {
                const propValue = node[property];
                if (!expectsValue) {
                    return isNil(propValue);
                }
                return regexMatchOrStrictEqual(propValue, value);
            }),
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
     * Expects the {@link DOMRect} of the received {@link Target} to match the given
     * `rect` object.
     *
     * The `rect` object can either be:
     * - a {@link DOMRect} object,
     * - a CSS selector string (to get the rect of the *only* matching element),
     * - a node.
     *
     * If the resulting `rect` value is a node, then both nodes' rects will be compared.
     *
     * @param {Partial<DOMRect> | Target} rect
     * @param {ExpectOptions & QueryRectOptions} options
     * @example
     *  expect("button").toHaveRect({ x: 20, width: 100, height: 50 });
     * @example
     *  expect("button").toHaveRect(".container");
     */
    toHaveRect(rect, options) {
        this.#saveStack();

        ensureArguments([
            [rect, ["object", "string", "node", "node[]"]],
            [options, ["object", null]],
        ]);

        let refRect;
        if (typeof rect === "string" || isNode(rect)) {
            refRect = queryRect(rect, options);
        } else {
            refRect = rect;
        }

        const entries = $entries(refRect);
        return this.#resolve({
            name: "toHaveRect",
            acceptedType: ["string", "node", "node[]"],
            transform: queryAll,
            predicate: each((node) => {
                const nodeRect = getNodeRect(node, options);
                return entries.every(([key, value]) => strictEqual(nodeRect[key], value));
            }),
            message: (pass) =>
                options?.message ||
                (pass
                    ? `%elements% have the expected DOM rect of ${formatHumanReadable(rect)}`
                    : `expected %elements% to have the given DOM rect`),
            details: (actual) => {
                return [
                    [Markup.green("Expected:"), rect],
                    [Markup.red("Received:"), getNodeRect(actual[0], options)],
                ];
            },
        });
    }

    /**
     * Expects the received {@link Target} to have the given class name(s).
     *
     * @param {string | Record<string, string | RegExp>} style
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
                          ...$keys(styleDef).map(formatHumanReadable)
                      )}`
                    : `expected %elements% [to have all!not to have any] of the given style properties`),
            details: (actual) => {
                const styleValues = getStyleValues(actual[0], $keys(styleDef));
                return [
                    [Markup.green("Expected:"), styleDef],
                    [Markup.red("Received:"), styleValues],
                    [Markup.text("Diff:"), Markup.diff(styleDef, styleValues)],
                ];
            },
        });
    }

    /**
     * Expects the text content of the received {@link Target} to either:
     * - be strictly equal to a given string,
     * - match a given regular expression;
     *
     * @param {string | RegExp} [text]
     * @param {ExpectOptions & QueryTextOptions} [options]
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
        const expectsText = !isNil(text);
        return this.#resolve({
            name: "toHaveText",
            acceptedType: ["string", "node", "node[]"],
            transform: queryAll,
            predicate: each((node) => {
                const nodeText = getNodeText(node, options);
                if (!expectsText) {
                    return nodeText.length > 0;
                }
                return texts.every((text) => regexMatchOrStrictEqual(nodeText, text));
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
                return values.every((value) => regexMatchOrStrictEqual(nodeValue, value));
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
            return Promise.resolve(this.#received).then(
                /** @param {PromiseFulfilledResult<R>} reason */
                (result) => {
                    if (this.#modifiers.rejects) {
                        throw new HootError(
                            `expected promise to reject, instead resolved with: ${result}`
                        );
                    }
                    this.#received = result;
                    return this.#resolveFinalResult(specs);
                },
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
}

export class TestResult {
    /** @type {Assertion[]} */
    assertions = [];
    caughtErrors = 0;
    duration = 0;
    /** @type {Error[]} */
    errors = [];
    expectedAssertions = 0;
    expectedErrors = 0;
    pass = true;
    /** @type {string[]} */
    steps = [];
    ts = $now();

    /**
     * @param {Test} test
     */
    constructor(test) {
        this.test = test;
    }
}
