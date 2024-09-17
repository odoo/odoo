/** @odoo-module */

import {
    formatXml,
    getActiveElement,
    getNodeAttribute,
    getNodeRect,
    getNodeText,
    getNodeValue,
    getStyle,
    isCheckable,
    isEmpty,
    isNode,
    isNodeDisplayed,
    isNodeVisible,
    queryAll,
    queryRect,
} from "@web/../lib/hoot-dom/helpers/dom";
import { isFirefox, isIterable } from "@web/../lib/hoot-dom/hoot_dom_utils";
import {
    HootError,
    Markup,
    RawString,
    deepCopy,
    deepEqual,
    ensureArguments,
    ensureArray,
    formatHumanReadable,
    isNil,
    isOfType,
    match,
    strictEqual,
} from "../hoot_utils";
import { Test } from "./test";

/**
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
 * @typedef {import("@odoo/hoot-dom").FormatXmlOptions} FormatXmlOptions
 * @typedef {import("@odoo/hoot-dom").QueryRectOptions} QueryRectOptions
 * @typedef {import("@odoo/hoot-dom").QueryTextOptions} QueryTextOptions
 * @typedef {import("@odoo/hoot-dom").Target} Target
 */

/**
 * @template [R=unknown]
 * @template [A=R]
 * @typedef {{
 *  acceptedType: ArgumentType | ArgumentType[];
 *  failedDetails: () => any[];
 *  message: (pass: boolean) => string;
 *  name: string;
 *  predicate: () => boolean;
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
    Math: { floor: $floor },
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
 * @template T
 * @param {Iterable<T>} iterable
 * @param {(item: T) => boolean} predicate
 */
const each = (iterable, predicate) => () => {
    let length = 0;
    for (const value of iterable) {
        length++;
        if (!predicate(value)) {
            return false;
        }
    }
    return length && true;
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
 * @param {boolean} not
 */
const formatMessage = (message, not) =>
    message.replace(R_NOT, (_, ifTrue, ifFalse) => (not ? ifFalse || "" : ifTrue || ""));

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

/** @type {StringConstructor["raw"]} */
const h = (template, ...substitutions) =>
    new RawString(String.raw(template, ...substitutions.map((s) => formatHumanReadable(s))));

/**
 * @param {string} separator
 * @param {string[]} values
 */
const hJoin = (separator, values) => {
    const hValues = values.map(formatHumanReadable);
    const last = hValues.pop();
    const str = hValues.length ? [hValues.join(", "), last].join(` ${separator} `) : last;
    return new RawString(str);
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
 * @param {...unknown} args
 */
const detailsFromValues = (...args) =>
    args.length > 1
        ? [Markup.green(LABEL_EXPECTED, args[0]), Markup.red(LABEL_RECEIVED, args[1])]
        : [Markup.red(LABEL_RECEIVED, args[0])];

/**
 * @param {...unknown} args
 */
const detailsFromValuesWithDiff = (...args) => [
    ...detailsFromValues(...args),
    Markup.diff(...args),
];

/**
 * @param {Record<string, unknown>} valuesObject
 */
const detailsFromObject = (valuesObject) => {
    const [expected, received] = Object.entries(valuesObject);
    return [
        Markup.green(expected[0] || LABEL_EXPECTED, expected[1]),
        Markup.red(received[0] || LABEL_RECEIVED, received[1]),
    ];
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
 * @template T
 * @param {Target} target
 * @param {(element: Element) => T} mapFn
 * @returns {[Element[], Map<Element, T>]}
 */
const queryAndMap = (target, mapFn) => {
    const elements = queryAll(target);
    const map = new Map();
    for (const el of elements) {
        map.set(el, mapFn(el));
    }
    return [elements, map];
};

/**
 * @param {unknown} value
 * @param {string | RegExp} matcher
 */
const regexMatchOrStrictEqual = (value, matcher) =>
    matcher instanceof RegExp ? matcher.test(value) : strictEqual(value, matcher);

/**
 * @param {TestResult} result
 * @param {Assertion} assertion
 */
const registerAssertion = (result, assertion) => {
    result.assertions.push(assertion);
    result.pass &&= assertion.pass;
};

/**
 * @param {number} value
 * @param {number} digits
 */
const roundTo = (value, digits) => {
    const divisor = 10 ** digits;
    return $floor(value * divisor) / divisor;
};

/**
 * @param {string} method
 */
const scopeError = (method) => new HootError(`cannot call \`${method}()\` outside of a test`);

const R_NOT = /\[([\w\s]*)!([\w\s]*)\]/;

const LABEL_EXPECTED = "Expected:";
const LABEL_RECEIVED = "Received:";

/** @type {Set<Matcher>} */
const unconsumedMatchers = new Set();

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
     * @param {AfterTestOptions} [options]
     */
    function afterTest(options) {
        const { test } = currentResult;

        currentResult.duration = $now() - currentResult.ts;

        // Expect without matchers
        if (unconsumedMatchers.size) {
            let times;
            switch (unconsumedMatchers.size) {
                case 1:
                    times = "once";
                    break;
                case 2:
                    times = "twice";
                    break;
                default:
                    times = `${unconsumedMatchers.size} times`;
            }
            registerAssertion(
                currentResult,
                new Assertion({
                    label: "expect",
                    message: `called ${times} without calling any matchers`,
                    pass: false,
                })
            );
            unconsumedMatchers.clear();
        }

        // Steps
        if (currentResult.steps.length) {
            registerAssertion(
                currentResult,
                new Assertion({
                    label: "step",
                    message: `unverified steps`,
                    pass: false,
                    failedDetails: [Markup.red("Steps:", currentResult.steps)],
                })
            );
        }

        // Assertions count
        if (!currentResult.assertions.length) {
            registerAssertion(
                currentResult,
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
                currentResult,
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
                    currentResult,
                    new Assertion({
                        label: "errors",
                        message: `expected ${currentResult.expectedErrors} errors, but ${errorCount} were thrown`,
                        pass: false,
                    })
                );
            }
        } else if (errorCount) {
            registerAssertion(
                currentResult,
                new Assertion({
                    label: "errors",
                    message: `${errorCount} unverified error(s)`,
                    pass: false,
                })
            );
        }

        // "Todo" tag
        if (test?.config.todo) {
            if (currentResult.pass) {
                registerAssertion(
                    currentResult,
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
                currentResult,
                new Assertion({
                    label: "aborted",
                    message: `test was aborted, results may not be relevant`,
                    pass: false,
                })
            );
        }

        if (test) {
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

            test.parent?.reporting.add(report);
        }

        const result = currentResult;
        if (!options?.debug) {
            currentResult = null;
        }

        return result;
    }

    /**
     * @param {number} expected
     */
    function assertions(expected) {
        if (!currentResult) {
            throw scopeError("expect.assertions");
        }
        ensureArguments(arguments, "integer");
        if (expected < 1) {
            throw new HootError(`expected assertions count should be more than 1`);
        }

        currentResult.expectedAssertions = expected;
    }

    /**
     * @param {Test} test
     */
    function beforeTest(test) {
        if (test) {
            test.results.push(new TestResult(test));

            // Must be retrieved from the list to be proxified
            currentResult = test.results.at(-1);
        } else {
            currentResult = new TestResult();
        }
    }

    /**
     * @param {number} expected
     */
    function errors(expected) {
        if (!currentResult) {
            throw scopeError("expect.errors");
        }
        ensureArguments(arguments, "integer");

        currentResult.expectedErrors = expected;
    }

    /**
     * @param {any} value
     */
    function step(value) {
        if (!currentResult) {
            throw scopeError("expect.step");
        }

        currentResult.steps.push(deepCopy(value));
    }

    /**
     * Expects the received matchers to match the errors thrown since the start
     * of the test or the last call to {@link verifyErrors}. Calling this matcher
     * will reset the list of current errors.
     *
     * @param {unknown[]} errors
     * @example
     *  expect.verifyErrors([/RPCError/, /Invalid domain AST/]);
     */
    function verifyErrors(errors) {
        if (!currentResult) {
            throw scopeError("expect.verifyErrors");
        }
        ensureArguments(arguments, "any[]");

        const actualErrors = currentResult.errors;
        currentResult.errors = [];
        const pass =
            actualErrors.length === errors.length &&
            actualErrors.every(
                (error, i) =>
                    match(error, errors[i]) || (error.cause && match(error.cause, errors[i]))
            );

        const message = pass
            ? errors.length
                ? errors.map(formatHumanReadable).join(" -> ")
                : "no errors"
            : `expected the following errors`;
        const assertion = new Assertion({
            label: "verifyErrors",
            message,
            pass,
        });

        if (!pass) {
            const fActual = actualErrors.map(formatError);
            const fExpected = errors.map(formatError);
            const formattedStack = formatStack(new Error().stack);
            assertion.failedDetails = [
                ...detailsFromValuesWithDiff(fExpected, fActual),
                Markup.red("Source:", Markup.text(formattedStack, { technical: true })),
            ];
        }

        registerAssertion(currentResult, assertion);
    }

    /**
     * Expects the received steps to be equal to the steps emitted since the start
     * of the test or the last call to {@link verifySteps}. Calling this matcher
     * will reset the list of current steps.
     *
     * @param {any[]} steps
     * @example
     *  expect.verifySteps(["web_read_group", "web_search_read"]);
     */
    function verifySteps(steps) {
        if (!currentResult) {
            throw scopeError("expect.verifySteps");
        }
        ensureArguments(arguments, "any[]");

        const actualSteps = currentResult.steps;
        currentResult.steps = [];
        const pass = deepEqual(actualSteps, steps);
        const message = pass
            ? steps.length
                ? steps.map(formatHumanReadable).join(" -> ")
                : "no steps"
            : `expected the following steps`;
        const assertion = new Assertion({
            label: "verifySteps",
            message,
            pass,
        });

        if (!pass) {
            const formattedStack = formatStack(new Error().stack);
            assertion.failedDetails = [
                ...detailsFromValuesWithDiff(steps, actualSteps),
                Markup.red("Source:", Markup.text(formattedStack, { technical: true })),
            ];
        }

        registerAssertion(currentResult, assertion);
    }

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
        if (arguments.length > 1) {
            throw new HootError(`\`expect()\` only accepts a single argument`);
        }

        if (!currentResult) {
            throw scopeError("expect");
        }

        return new Matcher(currentResult, received, {}, params.headless);
    }

    const enrichedExpect = $assign(expect, {
        assertions,
        errors,
        step,
        verifyErrors,
        verifySteps,
    });
    const expectHooks = {
        after: afterTest,
        before: beforeTest,
    };

    /** @type {TestResult | null} */
    let currentResult = null;

    return [enrichedExpect, expectHooks];
}

export class Assertion {
    static nextId = 1;

    id = Assertion.nextId++;
    /** @type {[any, any][] | null} */
    failedDetails = null;
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
export class Matcher {
    /**
     * @private
     * @type {R}
     */
    _received = null;
    /**
     * @private
     * @type {TestResult}
     */
    _result;
    /**
     * @private
     */
    _headless = false;
    /**
     * @private
     * @type {Modifiers<Async>}
     */
    _modifiers = {
        not: false,
        rejects: false,
        resolves: false,
    };

    /**
     * @param {TestResult} result
     * @param {R} received
     * @param {Modifiers<Async>} modifiers
     * @param {boolean} headless
     */
    constructor(result, received, modifiers, headless) {
        this._result = result;

        this._received = received;
        this._headless = headless;
        this._modifiers = modifiers;

        unconsumedMatchers.add(this);
    }

    //-------------------------------------------------------------------------
    // Modifiers
    //-------------------------------------------------------------------------

    /**
     * Returns a set of matchers expecting a result opposite to what normal matchers
     * would expect.
     *
     * @returns {Omit<Matcher<R, A, Async>, "not">}
     * @example
     *  expect([1]).not.toBeEmpty();
     * @example
     *  expect("foo").not.toBe("bar");
     */
    get not() {
        if (this._modifiers.not) {
            throw matcherModifierError("not", `matcher is already negated`);
        }
        return this._clone({ not: true });
    }

    /**
     * Returns a set of matchers which will await the received value as a promise
     * and will be applied to a value rejected by that promise. The matcher will
     * throw an error should the promise resolve instead of being rejected.
     *
     * @returns {Omit<Matcher<R, A, true>, "rejects" | "resolves">}
     * @example
     *  await expect(Promise.reject("foo")).rejects.toBe("foo");
     */
    get rejects() {
        if (this._modifiers.rejects || this._modifiers.resolves) {
            throw matcherModifierError(
                "rejects",
                `matcher value has already been wrapped in a promise resolver`
            );
        }
        return this._clone({ rejects: true });
    }

    /**
     * Returns a set of matchers which will await the received value as a promise
     * and will be applied to a value resolved by that promise. The matcher will
     * throw an error should the promise reject instead of being resolved.
     *
     * @returns {Omit<Matcher<R, A, true>, "rejects" | "resolves">}
     * @example
     *  await expect(Promise.resolve("foo")).resolves.toBe("foo");
     */
    get resolves() {
        if (this._modifiers.rejects || this._modifiers.resolves) {
            throw matcherModifierError(
                "resolves",
                `matcher value has already been wrapped in a promise resolver`
            );
        }
        return this._clone({ resolves: true });
    }

    //-------------------------------------------------------------------------
    // Standard matchers
    //-------------------------------------------------------------------------

    /**
     * Expects the received value to be *strictly* equal to the `expected` value.
     *
     * @param {R} expected
     * @param {ExpectOptions} [options]
     * @example
     *  expect("foo").toBe("foo");
     * @example
     *  expect({ foo: 1 }).not.toBe({ foo: 1 });
     */
    toBe(expected, options) {
        this._saveStack();

        ensureArguments(arguments, "any", ["object", null]);

        return this._resolve((received) => ({
            name: "toBe",
            acceptedType: "any",
            predicate: () => strictEqual(received, expected),
            message: (pass) =>
                options?.message ||
                (pass
                    ? h`received value is[! not] strictly equal to ${received}`
                    : h`expected values to be strictly equal`),
            failedDetails: () => detailsFromValuesWithDiff(expected, received),
        }));
    }

    /**
     * Expects the received value to be close to the `expected` value up to a given
     * amount of digits (default is 2).
     *
     * @param {R} expected
     * @param {ExpectOptions & { digits?: number }} [options]
     * @example
     *  expect(0.2 + 0.1).toBeCloseTo(0.3);
     * @example
     *  expect(3.51).toBeCloseTo(3.5, { digits: 1 });
     */
    toBeCloseTo(expected, options) {
        this._saveStack();

        ensureArguments(arguments, "number", ["object", null]);

        const digits = options?.digits ?? 2;
        return this._resolve((received) => {
            const rounded = roundTo(received, digits);
            return {
                name: "toBeCloseTo",
                acceptedType: "number",
                predicate: () => strictEqual(rounded, expected),
                message: (pass) =>
                    options?.message ||
                    (pass
                        ? h`received value is[! not] close to ${received}`
                        : h`expected values to be close to the given value`),
                failedDetails: () => detailsFromValuesWithDiff(expected, rounded),
            };
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
        this._saveStack();

        ensureArguments(arguments, ["object", null]);

        return this._resolve((received) => ({
            name: "toBeEmpty",
            acceptedType: ["any"],
            predicate: () => isEmpty(received),
            message: (pass) =>
                options?.message ||
                (pass ? h`${received} is[! not] empty` : h`${received} should[! not] be empty`),
            failedDetails: () => detailsFromValues(received),
        }));
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
        this._saveStack();

        ensureArguments(arguments, "number", ["object", null]);

        return this._resolve((received) => ({
            name: "toBeGreaterThan",
            acceptedType: "number",
            predicate: () => min < received,
            message: (pass) =>
                options?.message ||
                (pass
                    ? h`${received} is[! not] strictly greater than ${min}`
                    : h`expected value[! not] to be strictly greater`),
            failedDetails: () =>
                detailsFromObject({
                    "Minimum:": min,
                    [LABEL_RECEIVED]: received,
                }),
        }));
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
        this._saveStack();

        ensureArguments(arguments, "function", ["object", null]);

        return this._resolve((received) => ({
            name: "toBeInstanceOf",
            acceptedType: "any",
            predicate: () => received instanceof cls,
            message: (pass) =>
                options?.message ||
                (pass
                    ? h`${received} is[! not] an instance of ${cls.name}`
                    : h`expected value[! not] to be an instance of the given class`),
            failedDetails: () =>
                detailsFromObject({
                    [LABEL_EXPECTED]: cls,
                    "Actual parent class:": received.constructor.name,
                }),
        }));
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
        this._saveStack();

        ensureArguments(arguments, "number", ["object", null]);

        return this._resolve((received) => ({
            name: "toBeLessThan",
            acceptedType: "number",
            predicate: () => received < max,
            message: (pass) =>
                options?.message ||
                (pass
                    ? h`${received} is[! not] strictly less than ${max}`
                    : h`expected value[! not] to be strictly less`),
            failedDetails: () =>
                detailsFromObject({
                    "Maximum:": max,
                    [LABEL_RECEIVED]: received,
                }),
        }));
    }

    /**
     * Expects the received value to be of the given `type`.
     *
     * @param {ArgumentType} type
     * @param {ExpectOptions} [options]
     * @example
     *  expect("foo").toBeOfType("string");
     * @example
     *  expect({ foo: 1 }).toBeOfType("object");
     */
    toBeOfType(type, options) {
        this._saveStack();

        ensureArguments(arguments, "string", ["object", null]);

        return this._resolve((received) => ({
            name: "toBeOfType",
            acceptedType: "any",
            predicate: () => isOfType(received, type),
            message: (pass) =>
                options?.message ||
                (pass
                    ? h`${received} is[! not] of type ${type}`
                    : h`expected value to be of the given type`),
            failedDetails: () =>
                detailsFromObject({
                    "Expected type:": type,
                    "Received value:": received,
                }),
        }));
    }

    /**
     * Expects the received value to be strictly between `min` and `max` (both inclusive).
     *
     * @param {number} min (inclusive)
     * @param {number} max (inclusive)
     * @param {ExpectOptions} [options]
     * @example
     *  expect(3).toBeWithin(3, 9);
     * @example
     *  expect(-8.5).toBeWithin(-20, 0);
     * @example
     *  expect(100).toBeWithin(50, 100);
     */
    toBeWithin(min, max, options) {
        this._saveStack();

        ensureArguments(arguments, "number", "number", ["object", null]);

        if (min > max) {
            [min, max] = [max, min];
        }
        if (min === max) {
            throw new HootError(`min and max cannot be equal (did you mean to use \`toBe()\`?)`);
        }

        return this._resolve((received) => ({
            name: "toBeWithin",
            acceptedType: "number",
            predicate: () => min <= received && received <= max,
            message: (pass) =>
                options?.message ||
                (pass
                    ? h`${received} is[! not] between ${min} and ${max}`
                    : h`expected value[! not] to be between given range`),
            failedDetails: () => detailsFromValues(`${min} - ${max}`, received),
        }));
    }

    /**
     * Expects the received value to be *deeply* equal to the `expected` value.
     *
     * @param {R} expected
     * @param {ExpectOptions} [options]
     * @example
     *  expect(["foo"]).toEqual(["foo"]);
     * @example
     *  expect({ foo: 1 }).toEqual({ foo: 1 });
     */
    toEqual(expected, options) {
        this._saveStack();

        ensureArguments(arguments, "any", ["object", null]);

        return this._resolve((received) => ({
            name: "toEqual",
            acceptedType: "any",
            predicate: () => deepEqual(received, expected),
            message: (pass) =>
                options?.message ||
                (pass
                    ? h`received value is[! not] deeply equal to ${received}`
                    : h`expected values to[! not] be deeply equal`),
            failedDetails: () => detailsFromValuesWithDiff(expected, received),
        }));
    }

    /**
     * Expects the received value to have a length of the given `length`.
     *
     * Received value can be a string, an iterable or an object.
     *
     * @param {number} length
     * @param {ExpectOptions} [options]
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
        this._saveStack();

        ensureArguments(arguments, "integer", ["object", null]);

        return this._resolve((received) => {
            const receivedLength = getLength(received);
            return {
                name: "toHaveLength",
                acceptedType: ["string", "array", "object"],
                predicate: () => strictEqual(receivedLength, length),
                message: (pass) =>
                    options?.message ||
                    (pass
                        ? h`${received} has[! not] a length of ${length}`
                        : h`expected value[! not] to have the given length`),
                failedDetails: () =>
                    detailsFromObject({
                        "Expected length:": length,
                        [LABEL_RECEIVED]: receivedLength,
                    }),
            };
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
     * @param {ExpectOptions} [options]
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
        this._saveStack();

        ensureArguments(arguments, "any", ["object", null]);

        return this._resolve((received) => ({
            name: "toInclude",
            acceptedType: ["string", "any[]", "object"],
            predicate: () => includes(received, item),
            message: (pass) =>
                options?.message ||
                (pass
                    ? h`${received} [includes!does not include] ${item}`
                    : h`expected object[! not] to include the given item`),
            failedDetails: () =>
                detailsFromObject({
                    "Object:": received,
                    "Item:": item,
                }),
        }));
    }

    /**
     * Expects the received value to match the given `matcher`.
     *
     * @param {import("../hoot_utils").Matcher} matcher
     * @param {ExpectOptions} [options]
     * @example
     *  expect(new Error("foo")).toMatch("foo");
     * @example
     *  expect("a foo value").toMatch(/fo.*ue/);
     */
    toMatch(matcher, options) {
        this._saveStack();

        ensureArguments(arguments, "any", ["object", null]);

        return this._resolve((received) => ({
            name: "toMatch",
            acceptedType: "any",
            predicate: () => match(received, matcher),
            message: (pass) =>
                options?.message ||
                (pass
                    ? h`${received} [matches!does not match] ${matcher}`
                    : h`expected value[! not] to match the given matcher`),
            failedDetails: () =>
                detailsFromObject({
                    "Matcher:": matcher,
                    [LABEL_RECEIVED]: received,
                }),
        }));
    }

    /**
     * Expects the received {@link Function} to throw an error after being called.
     *
     * @param {import("../hoot_utils").Matcher} [matcher=Error]
     * @param {ExpectOptions} [options]
     * @example
     *  expect(() => { throw new Error("Woops!") }).toThrow(/woops/i);
     * @example
     *  await expect(Promise.reject("foo")).rejects.toThrow("foo");
     */
    toThrow(matcher = Error, options) {
        this._saveStack();

        ensureArguments(arguments, "any", ["object", null]);

        return this._resolve((received) => {
            const isAsync = this._modifiers.rejects || this._modifiers.resolves;
            const name = received.name || "anonymous function";
            let returnValue;
            if (isAsync) {
                returnValue = received;
            } else {
                try {
                    returnValue = received();
                } catch (error) {
                    returnValue = error;
                }
            }
            return {
                name: "toThrow",
                acceptedType: ["function", "error"],
                predicate: () => match(returnValue, matcher),
                message: (pass) =>
                    options?.message ||
                    (pass
                        ? h`${name} did[! not] ${isAsync ? h`reject` : h`throw`} a matching value`
                        : h`${name} ${
                              isAsync ? h`rejected` : h`threw`
                          } a value that did not match the given matcher`),
                failedDetails: () =>
                    detailsFromObject({
                        "Matcher:": matcher,
                        [LABEL_RECEIVED]: returnValue,
                    }),
            };
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
        this._saveStack();

        ensureArguments(arguments, ["object", null]);

        const prop = options?.indeterminate ? "indeterminate" : "checked";
        const pseudo = ":" + prop;

        return this._resolve((received) => {
            const [els, map] = queryAndMap(received, (el) => el.matches?.(pseudo));
            return {
                name: "toBeChecked",
                acceptedType: ["string", "node", "node[]"],
                predicate: each(map.values(), Boolean),
                message: (pass) =>
                    options?.message ||
                    (pass ? h`${els} are[! not] ${prop}` : h`expected ${els}[! not] to be ${prop}`),
                failedDetails: () => detailsFromValues([...map.values()]),
            };
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
        this._saveStack();

        ensureArguments(arguments, ["object", null]);

        return this._resolve((received) => {
            const elements = queryAll(received);
            const displayed = [];
            const notDisplayed = [];
            for (const el of elements) {
                if (isNodeDisplayed(el)) {
                    displayed.push(el);
                } else {
                    notDisplayed.push(el);
                }
            }
            return {
                name: "toBeDisplayed",
                acceptedType: ["string", "node", "node[]"],
                predicate: () => elements.length && elements.length === displayed.length,
                message: (pass) =>
                    options?.message ||
                    (pass
                        ? h`${elements} are[! not] displayed`
                        : h`expected ${elements}[! not] to be displayed`),
                failedDetails: () =>
                    detailsFromObject({
                        "Displayed:": displayed,
                        "Not displayed:": notDisplayed,
                    }),
            };
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
        this._saveStack();

        ensureArguments(arguments, ["object", null]);

        return this._resolve((received) => {
            const [els, map] = queryAndMap(received, (el) => el.matches?.(":enabled"));
            return {
                name: "toBeEnabled",
                acceptedType: ["string", "node", "node[]"],
                predicate: each(map.values(), Boolean),
                message: (pass) =>
                    options?.message ||
                    (pass
                        ? h`${els} are [enabled!disabled]`
                        : h`expected ${els} to be [enabled!disabled]`),
                failedDetails: () => detailsFromValues(els),
            };
        });
    }

    /**
     * Expects the received {@link Target} to be focused in its owner document.
     *
     * @param {ExpectOptions} [options]
     */
    toBeFocused(options) {
        this._saveStack();

        ensureArguments(arguments, ["object", null]);

        return this._resolve((received) => {
            const [els, map] = queryAndMap(received, (el) => getActiveElement(el));
            return {
                name: "toBeFocused",
                acceptedType: ["string", "node", "node[]"],
                predicate: each(map, ([el, activeEl]) => el === activeEl),
                message: (pass) =>
                    options?.message ||
                    (pass ? h`${els} are[! not] focused` : h`${els} should[! not] be focused`),
                failedDetails: () =>
                    detailsFromObject({
                        "Focused:": [...map.values()],
                        [LABEL_RECEIVED]: els,
                    }),
            };
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
        this._saveStack();

        ensureArguments(arguments, ["object", null]);

        return this._resolve((received) => {
            const elements = queryAll(received);
            const visible = [];
            const hidden = [];
            for (const el of elements) {
                if (isNodeVisible(el)) {
                    visible.push(el);
                } else {
                    hidden.push(el);
                }
            }
            return {
                name: "toBeVisible",
                acceptedType: ["string", "node", "node[]"],
                predicate: () => elements.length && elements.length === visible.length,
                message: (pass) =>
                    options?.message ||
                    (pass
                        ? h`${elements} are [visible!hidden]`
                        : h`expected ${elements} to be [visible!hidden]`),
                failedDetails: () =>
                    detailsFromObject({
                        "Visible:": visible,
                        "Hidden:": hidden,
                    }),
            };
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
        this._saveStack();

        ensureArguments(arguments, "string", ["string", "number", "regex", null], ["object", null]);

        const expectsValue = !isNil(value);
        const values = ensureArray(value);

        return this._resolve((received) => {
            const [els, map] = queryAndMap(received, (el) => getNodeAttribute(el, attribute));
            return {
                name: "toHaveAttribute",
                acceptedType: ["string", "node", "node[]"],
                predicate: each(map, ([el, elAttr]) =>
                    expectsValue
                        ? regexMatchOrStrictEqual(elAttr, value)
                        : el.hasAttribute(attribute)
                ),
                message: (pass) =>
                    options?.message ||
                    (pass
                        ? h`attribute ${attribute} on ${els} ${
                              expectsValue ? h`[matches!does not match] ${value}` : h`is[! not] set`
                          }`
                        : h`${els} do not have the correct attribute${
                              expectsValue ? h` value` : h``
                          }`),
                failedDetails: () => detailsFromValuesWithDiff(values, [...map.values()]),
            };
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
        this._saveStack();

        ensureArguments(arguments, ["string", "string[]"], ["object", null]);

        const rawClassNames = ensureArray(className);
        const classNames = rawClassNames.flatMap((cls) => cls.trim().split(/\s+/g));

        return this._resolve((received) => {
            const [els, map] = queryAndMap(received, (el) => [...el.classList]);
            return {
                name: "toHaveClass",
                acceptedType: ["string", "node", "node[]"],
                predicate: each(map.values(), (classes) =>
                    classNames.every((cls) => classes.includes(cls))
                ),
                message: (pass) =>
                    options?.message ||
                    (pass
                        ? h`${els} [have!do not have] classes ${hJoin("and", classNames)}`
                        : h`expected ${els} [to have all!not to have any] of the given class names`),
                failedDetails: () =>
                    detailsFromValues(
                        classNames.join(" "),
                        [...map.values()].map((classes) => classes.join(" "))
                    ),
            };
        });
    }

    /**
     * Expects the received {@link Target} to contain exactly `amount` element(s).
     * Note that the `amount` parameter can be omitted, in which case the function
     * will expect *at least* one element.
     *
     * @param {number} [amount]
     * @param {ExpectOptions} [options]
     * @example
     *  expect(".o_webclient").toHaveCount(1);
     * @example
     *  expect(".o_form_view .o_field_widget").toHaveCount();
     * @example
     *  expect("ul > li").toHaveCount(4);
     */
    toHaveCount(amount, options) {
        this._saveStack();

        ensureArguments(arguments, ["integer", null], ["object", null]);

        if (isNil(amount)) {
            amount = false;
        }

        return this._resolve((received) => {
            const elements = queryAll(received);
            return {
                name: "toHaveCount",
                acceptedType: ["string", "node", "node[]"],
                predicate: () =>
                    amount === false ? elements.length > 0 : strictEqual(elements.length, amount),
                message: (pass) =>
                    options?.message ||
                    (pass
                        ? h`there are[! not] ${amount} ${elements}`
                        : h`there is an incorrect amount of ${elements}`),
                failedDetails: () => [
                    ...detailsFromValues(amount === false ? "any" : amount, elements.length),
                    Markup.red("Elements:", elements),
                ],
            };
        });
    }

    /**
     * Expects the `innerHTML` of the received {@link Target} to match the `expected`
     * value (upon formatting).
     *
     * @param {string | RegExp} [expected]
     * @param {ExpectOptions & FormatXmlOptions} [options]
     * @example
     *  expect(".my_element").toHaveInnerHTML(`
     *      Some <strong>text</strong>
     *  `);
     */
    toHaveInnerHTML(expected, options) {
        this._saveStack();

        return this._toHaveHTML("toHaveInnerHTML", "innerHTML", ...arguments);
    }

    /**
     * Expects the `outerHTML` of the received {@link Target} to match the `expected`
     * value (upon formatting).
     *
     * @param {string | RegExp} [expected]
     * @param {ExpectOptions & FormatXmlOptions} [options]
     * @example
     *  expect(".my_element").toHaveOuterHTML(`
     *      <div class="my_element">
     *          Some <strong>text</strong>
     *      </div>
     *  `);
     */
    toHaveOuterHTML(expected, options) {
        this._saveStack();

        return this._toHaveHTML("toHaveOuterHTML", "outerHTML", ...arguments);
    }

    /**
     * Expects the received {@link Target} to have its given property value match
     * the given `value`.
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
        this._saveStack();

        ensureArguments(arguments, "string", "any", ["object", null]);

        const expectsValue = !isNil(value);
        const values = ensureArray(value);

        return this._resolve((received) => {
            const [els, map] = queryAndMap(received, (el) => el[property]);
            return {
                name: "toHaveProperty",
                acceptedType: ["string", "node", "node[]"],
                predicate: each(map.values(), (elProp) =>
                    expectsValue ? regexMatchOrStrictEqual(elProp, value) : isNil(elProp)
                ),
                message: (pass) =>
                    options?.message ||
                    (pass
                        ? h`property ${property} on ${els} ${
                              expectsValue ? h`[matches!does not match] ${value}` : h`is[! not] set`
                          }`
                        : h`${els} do not have the correct property${
                              expectsValue ? h` value` : h``
                          }`),
                failedDetails: () => detailsFromValuesWithDiff(values, [...map.values()]),
            };
        });
    }

    /**
     * Expects the {@link DOMRect} of the received {@link Target} to match the given
     * `rect` object.
     *
     * The `rect` object can either be:
     * - a {@link DOMRect} object;
     * - a CSS selector string (to get the rect of the *only* matching element);
     * - a node.
     *
     * If the resulting `rect` value is a node, then both nodes' rects will be compared.
     *
     * @param {Partial<DOMRect> | Target} rect
     * @param {ExpectOptions & QueryRectOptions} [options]
     * @example
     *  expect("button").toHaveRect({ x: 20, width: 100, height: 50 });
     * @example
     *  expect("button").toHaveRect(".container");
     */
    toHaveRect(rect, options) {
        this._saveStack();

        ensureArguments(arguments, ["object", "string", "node", "node[]"], ["object", null]);

        let refRect;
        if (typeof rect === "string" || isNode(rect)) {
            refRect = { ...queryRect(rect, options) };
        } else {
            refRect = rect;
        }

        const entries = $entries(refRect);

        return this._resolve((received) => {
            const [els, map] = queryAndMap(received, (el) => getNodeRect(el, options));
            return {
                name: "toHaveRect",
                acceptedType: ["string", "node", "node[]"],
                predicate: each(map.values(), (elRect) =>
                    entries.every(([key, value]) => strictEqual(elRect[key], value))
                ),
                message: (pass) =>
                    options?.message ||
                    (pass
                        ? h`${els} have the expected DOM rect of ${rect}`
                        : h`expected ${els} to have the given DOM rect`),
                failedDetails: () =>
                    detailsFromValuesWithDiff(
                        rect,
                        $fromEntries(entries.map(([key]) => [key, [...map.values()][0][key]]))
                    ),
            };
        });
    }

    /**
     * Expects the received {@link Target} to match the given style properties.
     *
     * @param {string | Record<string, string | RegExp>} style
     * @param {ExpectOptions} [options]
     * @example
     *  expect("button").toHaveStyle({ color: "red" });
     * @example
     *  expect("p").toHaveStyle("text-align: center");
     */
    toHaveStyle(style, options) {
        this._saveStack();

        ensureArguments(arguments, ["string", "object"], ["object", null]);

        const styleDef = typeof style === "string" ? parseStyle(style) : style;
        const entries = $entries(styleDef);

        return this._resolve((received) => {
            const [els, map] = queryAndMap(received, (el) => getStyleValues(el, $keys(styleDef)));
            return {
                name: "toHaveStyle",
                acceptedType: ["string", "node", "node[]"],
                predicate: each(map.values(), (elStyle) =>
                    entries.every(([prop, value]) => regexMatchOrStrictEqual(elStyle[prop], value))
                ),
                message: (pass) =>
                    options?.message ||
                    (pass
                        ? h`${els} have the expected style values for ${hJoin(
                              "and",
                              $keys(styleDef)
                          )}`
                        : h`expected ${els} [to have all!not to have any] of the given style properties`),
                failedDetails: () =>
                    detailsFromValuesWithDiff(
                        styleDef,
                        $fromEntries(entries.map(([key]) => [key, [...map.values()][0][key]]))
                    ),
            };
        });
    }

    /**
     * Expects the text content of the received {@link Target} to either:
     * - be strictly equal to a given string;
     * - match a given regular expression.
     *
     * @param {string | RegExp} [text]
     * @param {ExpectOptions & QueryTextOptions} [options]
     * @example
     *  expect("p").toHaveText("lorem ipsum dolor sit amet");
     * @example
     *  expect("header h1").toHaveText(/odoo/i);
     */
    toHaveText(text, options) {
        this._saveStack();

        ensureArguments(arguments, ["string", "regex", null], ["object", null]);

        const texts = ensureArray(text);
        const expectsText = !isNil(text);

        return this._resolve((received) => {
            const [els, map] = queryAndMap(received, (el) => getNodeText(el, options));
            return {
                name: "toHaveText",
                acceptedType: ["string", "node", "node[]"],
                predicate: each(map.values(), (elText) =>
                    expectsText
                        ? texts.every((text) => regexMatchOrStrictEqual(elText, text))
                        : elText.length > 0
                ),
                message: (pass) =>
                    options?.message ||
                    (pass
                        ? h`${els} [have!do not have] text ${text}`
                        : h`expected ${els}[! not] to have the given text`),
                failedDetails: () => detailsFromValuesWithDiff(texts, [...map.values()]),
            };
        });
    }

    /**
     * Expects the value of the received {@link Target} to either:
     * - be strictly equal to a given string or number;
     * - match a given regular expression;
     * - contain file objects matching the given `files` list.
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
        this._saveStack();

        ensureArguments(
            arguments,
            ["string", "string[]", "number", "object[]", "regex", null],
            ["object", null]
        );

        const values = ensureArray(value);
        const expectsValue = !isNil(value);

        return this._resolve((received) => {
            const [els, map] = queryAndMap(received, (el) => getNodeValue(el));
            return {
                name: "toHaveValue",
                acceptedType: ["string", "node", "node[]"],
                predicate: each(map, ([el, elValue]) => {
                    if (isCheckable(el)) {
                        throw new HootError(
                            `cannot call \`toHaveValue()\` on a checkbox or radio input: use \`toBeChecked()\` instead`
                        );
                    }
                    if (!expectsValue) {
                        return isIterable(elValue) ? [...elValue].length > 0 : el.value !== "";
                    }
                    if (isIterable(elValue)) {
                        if (isIterable(value)) {
                            return deepEqual(elValue, values);
                        }
                        elValue = el.value;
                    }
                    return values.every((value) => regexMatchOrStrictEqual(elValue, value));
                }),
                message: (pass) =>
                    options?.message ||
                    (pass
                        ? h`${els} [have!do not have] value ${value}`
                        : h`expected ${els}[! not] to have the given value`),
                failedDetails: () => detailsFromValuesWithDiff(values, [...map.values()]),
            };
        });
    }

    //-------------------------------------------------------------------------
    // Private methods
    //-------------------------------------------------------------------------

    /**
     * @private
     * @param {Modifiers} modifiers
     */
    _clone(modifiers) {
        unconsumedMatchers.delete(this);
        return new this.constructor(
            this._result,
            this._received,
            { ...this._modifiers, ...modifiers },
            this._headless
        );
    }

    /**
     * @private
     * @param {() => MatcherSpecifications<R, A>} specCallback
     * @returns {Async extends true ? Promise<void> : void}
     */
    _resolve(specCallback) {
        unconsumedMatchers.delete(this);
        if (this._modifiers.rejects || this._modifiers.resolves) {
            return Promise.resolve(this._received).then(
                /** @param {PromiseFulfilledResult<R>} reason */
                (result) => {
                    if (this._modifiers.rejects) {
                        registerAssertion(
                            this._result,
                            new Assertion({
                                label: "rejects",
                                message: h`expected promise to reject, instead resolved with: ${result}`,
                                pass: false,
                            })
                        );
                    } else {
                        this._received = result;
                        this._resolveFinalResult(specCallback);
                    }
                },
                /** @param {PromiseRejectedResult} reason */
                (reason) => {
                    if (this._modifiers.resolves) {
                        registerAssertion(
                            this._result,
                            new Assertion({
                                label: "resolves",
                                message: h`expected promise to resolve, instead rejected with: ${reason}`,
                                pass: false,
                            })
                        );
                    } else {
                        this._received = reason;
                        this._resolveFinalResult(specCallback);
                    }
                }
            );
        } else {
            this._resolveFinalResult(specCallback);
        }
    }

    /**
     * @private
     * @param {() => MatcherSpecifications<R, A>} specCallback
     * @returns {void}
     */
    _resolveFinalResult(specCallback) {
        const { acceptedType, name, failedDetails, message, predicate } = specCallback(
            this._received
        );

        const types = ensureArray(acceptedType);
        if (!types.some((type) => isOfType(this._received, type))) {
            throw new TypeError(
                h`expected received value to be of type ${hJoin("or", types)}, got ${
                    this._received
                }`
            );
        }

        const { not } = this._modifiers;
        let pass = predicate();
        if (not) {
            pass = !pass;
        }

        const assertion = new Assertion({
            label: name,
            message: formatMessage(message(pass), not),
            modifiers: this._modifiers,
            pass,
        });
        if (!pass) {
            const formattedStack = formatStack(currentStack);
            assertion.failedDetails = [
                ...failedDetails(),
                Markup.red("Source:", Markup.text(formattedStack, { technical: true })),
            ].filter(Boolean);
        }

        registerAssertion(this._result, assertion);
    }

    /**
     * @private
     */
    _saveStack() {
        if (!this._headless) {
            currentStack = new Error().stack;
        }
    }

    /**
     * @private
     * @param {"toHaveInnerHTML" | "toHaveOuterHTML"} name
     * @param {"innerHTML" | "outerHTML"} property
     * @param {string | RegExp} expected
     * @param {ExpectOptions & FormatXmlOptions} [options]
     */
    _toHaveHTML(name, property, expected, options) {
        ensureArguments(arguments, "string", "string", ["string", "regex"], ["object", null]);

        options = { type: "html", ...options };
        if (!(expected instanceof RegExp)) {
            expected = formatXml(expected, options);
        }

        return this._resolve((received) => {
            const [els, map] = queryAndMap(received, (el) => formatXml(el[property], options));
            return {
                name,
                acceptedType: ["string", "node", "node[]"],
                predicate: each(map.values(), (elHtml) =>
                    regexMatchOrStrictEqual(elHtml, expected)
                ),
                message: (pass) =>
                    options?.message ||
                    (pass
                        ? h`${property} of ${els} is[! not] equal to expected value`
                        : h`expected ${property} of ${els} to match the given value`),
                failedDetails: () => detailsFromValuesWithDiff(expected, [...map.values()]),
            };
        });
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
    /** @type {Test | null} */
    test = null;
    ts = $now();

    /**
     * @param {Test | null} [test]
     */
    constructor(test) {
        if (test) {
            this.test = test;
        }
    }
}
