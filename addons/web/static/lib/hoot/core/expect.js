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
 *  failedDetails: (actual: A) => any[];
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
 * @param  {string[]} values
 */
const and = (values) => {
    const last = values.pop();
    if (values.length) {
        return [values.join(", "), last].join(" and ");
    } else {
        return last;
    }
};

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
        .replace(R_NOT, (_, ifTrue, ifFalse) => (not ? ifFalse || "" : ifTrue || ""))
        .replace(R_RECEIVED, formatHumanReadable(received))
        .replace(R_ACTUAL, formatHumanReadable(actual))
        .replace(R_ELEMENTS, (_, elements) =>
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
 * @param {...unknown} args
 */
const detailsFromValues = (...args) =>
    args.length > 1
        ? [Markup.green(LABEL_EXPECTED, args[0]), Markup.red(LABEL_ACTUAL, args[1])]
        : [Markup.red(LABEL_ACTUAL, args[0])];

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
    const [expected, actual] = Object.entries(valuesObject);
    return [
        Markup.green(expected[0] || LABEL_EXPECTED, expected[1]),
        Markup.red(actual[0] || LABEL_ACTUAL, actual[1]),
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

const R_ACTUAL = /%(actual)%/i;
const R_ELEMENTS = /%(elements?)%/i;
const R_NOT = /\[([\w\s]*)!([\w\s]*)\]/;
const R_RECEIVED = /%(received)%/i;

const LABEL_ACTUAL = "Received:";
const LABEL_EXPECTED = "Expected:";

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

        return this._resolve({
            name: "toBe",
            acceptedType: "any",
            predicate: (actual) => strictEqual(actual, expected),
            message: (pass) =>
                options?.message ||
                (pass
                    ? `received value is[! not] strictly equal to %actual%`
                    : `expected values to be strictly equal`),
            failedDetails: (actual) => detailsFromValuesWithDiff(expected, actual),
        });
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
        return this._resolve({
            name: "toBeCloseTo",
            acceptedType: "number",
            transform: (value) => roundTo(value, digits),
            predicate: (actual) => strictEqual(actual, expected),
            message: (pass) =>
                options?.message ||
                (pass
                    ? `received value is[! not] close to %actual%`
                    : `expected values to be close to the given value`),
            failedDetails: (actual) => detailsFromValuesWithDiff(expected, actual),
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

        return this._resolve({
            name: "toBeEmpty",
            acceptedType: ["any"],
            predicate: isEmpty,
            message: (pass) =>
                options?.message ||
                (pass ? `%actual% is[! not] empty` : `%actual% should[! not] be empty`),
            failedDetails: (actual) => detailsFromValues(actual),
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
        this._saveStack();

        ensureArguments(arguments, "number", ["object", null]);

        return this._resolve({
            name: "toBeGreaterThan",
            acceptedType: "number",
            predicate: (actual) => min < actual,
            message: (pass) =>
                options?.message ||
                (pass
                    ? `%actual% is[! not] strictly greater than ${formatHumanReadable(min)}`
                    : `expected value[! not] to be strictly greater`),
            failedDetails: (actual) =>
                detailsFromObject({
                    "Minimum:": min,
                    [LABEL_ACTUAL]: actual,
                }),
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
        this._saveStack();

        ensureArguments(arguments, "function", ["object", null]);

        return this._resolve({
            name: "toBeInstanceOf",
            acceptedType: "any",
            predicate: (actual) => actual instanceof cls,
            message: (pass) =>
                options?.message ||
                (pass
                    ? `%actual% is[! not] an instance of ${cls.name}`
                    : `expected value[! not] to be an instance of the given class`),
            failedDetails: (actual) =>
                detailsFromObject({
                    [LABEL_EXPECTED]: cls,
                    "Actual parent class:": actual.constructor.name,
                }),
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
        this._saveStack();

        ensureArguments(arguments, "number", ["object", null]);

        return this._resolve({
            name: "toBeLessThan",
            acceptedType: "number",
            predicate: (actual) => actual < max,
            message: (pass) =>
                options?.message ||
                (pass
                    ? `%actual% is[! not] strictly less than ${formatHumanReadable(max)}`
                    : `expected value[! not] to be strictly less`),
            failedDetails: (actual) =>
                detailsFromObject({
                    "Maximum:": max,
                    [LABEL_ACTUAL]: actual,
                }),
        });
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

        return this._resolve({
            name: "toBeOfType",
            acceptedType: "any",
            predicate: (actual) => isOfType(actual, type),
            message: (pass) =>
                options?.message ||
                (pass
                    ? `%actual% is[! not] of type ${formatHumanReadable(type)}`
                    : `expected value to be of the given type`),
            failedDetails: (actual) =>
                detailsFromObject({
                    "Expected type:": type,
                    "Received value:": actual,
                }),
        });
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

        return this._resolve({
            name: "toBeWithin",
            acceptedType: "number",
            predicate: (actual) => min <= actual && actual <= max,
            message: (pass) =>
                options?.message ||
                (pass
                    ? `%actual% is[! not] between ${formatHumanReadable(
                          min
                      )} and ${formatHumanReadable(max)}`
                    : `expected value[! not] to be between given range`),
            failedDetails: (actual) => detailsFromValues(`${min} - ${max}`, actual),
        });
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

        return this._resolve({
            name: "toEqual",
            acceptedType: "any",
            predicate: (actual) => deepEqual(actual, expected),
            message: (pass) =>
                options?.message ||
                (pass
                    ? `received value is[! not] deeply equal to %actual%`
                    : `expected values to[! not] be deeply equal`),
            failedDetails: (actual) => detailsFromValuesWithDiff(expected, actual),
        });
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

        return this._resolve({
            name: "toHaveLength",
            acceptedType: ["string", "array", "object"],
            predicate: (actual) => getLength(actual) === length,
            message: (pass) =>
                options?.message ||
                (pass
                    ? `%actual% has[! not] a length of ${formatHumanReadable(length)}`
                    : `expected value[! not] to have the given length`),
            failedDetails: (actual) =>
                detailsFromObject({
                    "Expected length:": length,
                    [LABEL_ACTUAL]: getLength(actual),
                }),
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

        return this._resolve({
            name: "toInclude",
            acceptedType: ["string", "any[]", "object"],
            predicate: (actual) => includes(actual, item),
            message: (pass) =>
                options?.message ||
                (pass
                    ? `%actual% [includes!does not include] ${formatHumanReadable(item)}`
                    : `expected object[! not] to include the given item`),
            failedDetails: (actual) =>
                detailsFromObject({
                    "Object:": actual,
                    "Item:": item,
                }),
        });
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

        return this._resolve({
            name: "toMatch",
            acceptedType: "any",
            predicate: (actual) => match(actual, matcher),
            message: (pass) =>
                options?.message ||
                (pass
                    ? `%actual% [matches!does not match] ${formatHumanReadable(matcher)}`
                    : `expected value[! not] to match the given matcher`),
            failedDetails: (actual) =>
                detailsFromObject({
                    "Matcher:": matcher,
                    [LABEL_ACTUAL]: actual,
                }),
        });
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

        let name;
        return this._resolve({
            name: "toThrow",
            acceptedType: ["function", "error"],
            transform: (received) => {
                name = received.name || "anonymous function";
                const { rejects, resolves } = this._modifiers;
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
                const { rejects, resolves } = this._modifiers;
                return pass
                    ? `${name} did[! not] ${
                          rejects || resolves ? "reject" : "throw"
                      } a matching value`
                    : `${name} ${
                          rejects || resolves ? "rejected" : "threw"
                      } a value that did not match the given matcher`;
            },
            failedDetails: (actual) =>
                detailsFromObject({
                    "Matcher:": matcher,
                    [LABEL_ACTUAL]: actual,
                }),
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
        return this._resolve({
            name: "toBeChecked",
            acceptedType: ["string", "node", "node[]"],
            transform: queryAll,
            predicate: each((node) => node.matches?.(":" + prop)),
            message: (pass) =>
                options?.message ||
                (pass
                    ? `%elements% are[! not] ${prop}`
                    : `expected %elements%[! not] to be ${prop}`),
            failedDetails: (actual) => detailsFromValues(actual.map((node) => node[prop])),
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

        return this._resolve({
            name: "toBeDisplayed",
            acceptedType: ["string", "node", "node[]"],
            transform: queryAll,
            predicate: isDisplayed,
            message: (pass) =>
                options?.message ||
                (pass
                    ? `%elements% are[! not] displayed`
                    : `expected %elements%[! not] to be displayed`),
            failedDetails: (actual) => {
                const displayed = [];
                const notDisplayed = [];
                for (const node of actual) {
                    if (isDisplayed(node)) {
                        displayed.push(node);
                    } else {
                        notDisplayed.push(node);
                    }
                }
                return detailsFromObject({
                    "Displayed:": displayed,
                    "Not displayed:": notDisplayed,
                });
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
        this._saveStack();

        ensureArguments(arguments, ["object", null]);

        return this._resolve({
            name: "toBeEnabled",
            acceptedType: ["string", "node", "node[]"],
            transform: queryAll,
            predicate: each((node) => node.matches?.(":enabled")),
            message: (pass) =>
                options?.message ||
                (pass
                    ? `%elements% are [enabled!disabled]`
                    : `expected %elements% to be [enabled!disabled]`),
            failedDetails: (actual) => detailsFromValues(actual),
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

        return this._resolve({
            name: "toBeFocused",
            acceptedType: ["string", "node", "node[]"],
            transform: queryAll,
            predicate: each((node) => node === getActiveElement(node)),
            message: (pass) =>
                options?.message ||
                (pass ? `%elements% are[! not] focused` : `%elements% should[! not] be focused`),
            failedDetails: (actual) =>
                detailsFromObject({
                    "Focused:": getActiveElement(actual),
                    [LABEL_ACTUAL]: actual,
                }),
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

        return this._resolve({
            name: "toBeVisible",
            acceptedType: ["string", "node", "node[]"],
            transform: queryAll,
            predicate: isVisible,
            message: (pass) =>
                options?.message ||
                (pass
                    ? `%elements% are [visible!hidden]`
                    : `expected %elements% to be [visible!hidden]`),
            failedDetails: (actual) => {
                const visible = [];
                const hidden = [];
                for (const node of actual) {
                    if (isVisible(node)) {
                        visible.push(node);
                    } else {
                        hidden.push(node);
                    }
                }
                return detailsFromObject({
                    "Visible:": visible,
                    "Hidden:": hidden,
                });
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
        this._saveStack();

        ensureArguments(arguments, "string", ["string", "number", "regex", null], ["object", null]);

        const expectsValue = !isNil(value);
        return this._resolve({
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
            failedDetails: (actual) =>
                detailsFromValuesWithDiff(value, getNodeAttribute(actual[0], attribute)),
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

        return this._resolve({
            name: "toHaveClass",
            acceptedType: ["string", "node", "node[]"],
            transform: queryAll,
            predicate: each((node) => classNames.every((cls) => node.classList.contains(cls))),
            message: (pass) =>
                options?.message ||
                (pass
                    ? `%elements% [have!do not have] classes ${and(
                          classNames.map(formatHumanReadable)
                      )}`
                    : `expected %elements% [to have all!not to have any] of the given class names`),
            failedDetails: (actual) =>
                detailsFromValues(
                    classNames,
                    actual.flatMap((node) => [...node.classList])
                ),
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

        return this._resolve({
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
            failedDetails: (actual) => [
                ...detailsFromValues(amount === false ? "any" : amount, actual.length),
                Markup.red("Nodes:", actual),
            ],
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

        ensureArguments(arguments, ["string", "regex"], ["object", null]);

        return this._toHaveHTML("innerHTML", expected, options);
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

        ensureArguments(arguments, ["string", "regex"], ["object", null]);

        return this._toHaveHTML("outerHTML", expected, options);
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

        return this._resolve({
            name: "toHaveProperty",
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
            failedDetails: (actual) => detailsFromValuesWithDiff(value, actual[0][property]),
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
        const nodeRects = [];
        return this._resolve({
            name: "toHaveRect",
            acceptedType: ["string", "node", "node[]"],
            transform: queryAll,
            predicate: each((node) => {
                const nodeRect = getNodeRect(node, options);
                nodeRects.push(nodeRect);
                return entries.every(([key, value]) => strictEqual(nodeRect[key], value));
            }),
            message: (pass) =>
                options?.message ||
                (pass
                    ? `%elements% have the expected DOM rect of ${formatHumanReadable(rect)}`
                    : `expected %elements% to have the given DOM rect`),
            failedDetails: () =>
                detailsFromValuesWithDiff(
                    rect,
                    $fromEntries(entries.map(([key]) => [key, nodeRects[0][key]]))
                ),
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
        return this._resolve({
            name: "toHaveStyle",
            acceptedType: ["string", "node", "node[]"],
            transform: queryAll,
            predicate: each((node) => hasStyle(node, styleDef)),
            message: (pass) =>
                options?.message ||
                (pass
                    ? `%elements% have the expected style values for ${and(
                          $keys(styleDef).map(formatHumanReadable)
                      )}`
                    : `expected %elements% [to have all!not to have any] of the given style properties`),
            failedDetails: (actual) =>
                detailsFromValuesWithDiff(styleDef, getStyleValues(actual[0], $keys(styleDef))),
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
        return this._resolve({
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
            failedDetails: (actual) => detailsFromValuesWithDiff(texts, actual.map(getNodeText)),
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
        return this._resolve({
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
            failedDetails: (actual) => detailsFromValuesWithDiff(values, actual.map(getNodeValue)),
        });
    }

    //-------------------------------------------------------------------------
    // Private methods
    //-------------------------------------------------------------------------

    /**
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
     * @param {MatcherSpecifications<R, A>} specs
     * @returns {Async extends true ? Promise<void> : void}
     */
    _resolve(specs) {
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
                                message: `expected promise to reject, instead resolved with: ${formatHumanReadable(
                                    result
                                )}`,
                                pass: false,
                            })
                        );
                    } else {
                        this._received = result;
                        this._resolveFinalResult(specs);
                    }
                },
                /** @param {PromiseRejectedResult} reason */
                (reason) => {
                    if (this._modifiers.resolves) {
                        registerAssertion(
                            this._result,
                            new Assertion({
                                label: "resolves",
                                message: `expected promise to resolve, instead rejected with: ${formatHumanReadable(
                                    reason
                                )}`,
                                pass: false,
                            })
                        );
                    } else {
                        this._received = reason;
                        this._resolveFinalResult(specs);
                    }
                }
            );
        } else {
            this._resolveFinalResult(specs);
        }
    }

    /**
     * @private
     * @param {MatcherSpecifications<R, A>} specs
     * @returns {void}
     */
    _resolveFinalResult({ acceptedType, name, failedDetails, message, predicate, transform }) {
        const received = this._received;
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
        const { not } = this._modifiers;
        let pass = predicate(actual);
        if (not) {
            pass = !pass;
        }

        const assertion = new Assertion({
            label: name,
            message: formatMessage(message(pass), { actual, not, received }),
            modifiers: this._modifiers,
            pass,
        });
        if (!pass) {
            const formattedStack = formatStack(currentStack);
            assertion.failedDetails = [
                ...failedDetails(deepCopy(actual)),
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
     * @param {"innerHTML" | "outerHTML"} property
     * @param {string | RegExp} expected
     * @param {ExpectOptions & FormatXmlOptions} [options]
     */
    _toHaveHTML(property, expected, options) {
        options = { type: "html", ...options };
        if (!(expected instanceof RegExp)) {
            expected = formatXml(expected, options);
        }

        return this._resolve({
            name: `toHave${property[0].toUpperCase()}${property.slice(1)}`,
            acceptedType: ["string", "node", "node[]"],
            transform: queryAll,
            predicate: each((node) =>
                regexMatchOrStrictEqual(formatXml(node[property], options), expected)
            ),
            message: (pass) =>
                options?.message ||
                (pass
                    ? `${property} of node is[! not] equal to expected value`
                    : `expected ${property} of node to match the given value`),
            failedDetails: (actual) =>
                detailsFromValuesWithDiff(expected, formatXml(actual[0][property], options)),
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
