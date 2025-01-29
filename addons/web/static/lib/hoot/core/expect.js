/** @odoo-module */

import { markRaw } from "@odoo/owl";
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
    queryRect,
} from "@web/../lib/hoot-dom/helpers/dom";
import { addInteractionListener, isFirefox, isIterable } from "@web/../lib/hoot-dom/hoot_dom_utils";
import {
    CASE_EVENT_TYPES,
    ElementMap,
    HootError,
    Markup,
    deepCopy,
    deepEqual,
    ensureArguments,
    ensureArray,
    formatHumanReadable,
    isLabel,
    isNil,
    isOfType,
    makeLabel,
    makeLabelIcon,
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
 * @typedef {string | string[] | ((pass: boolean, raw: typeof String["raw"]) => string | string[])} AssertionMessage
 *
 * @typedef {InteractionType | "assertion" | "error" | "step"} CaseEventType
 *
 * @typedef {{ exact?: boolean }} ClassListOptions
 *
 * @typedef {{ exact?: boolean; inline?: boolean }} DOMStyleOptions
 *
 * @typedef {{
 *  headless: boolean;
 * }} ExpectBuilderParams
 *
 * @typedef {{
 *  message?: AssertionMessage;
 * }} ExpectOptions
 *
 * @typedef {import("../hoot_utils").Label} Label
 *
 * @typedef {import("@odoo/hoot-dom").Dimensions} Dimensions
 * @typedef {import("@odoo/hoot-dom").FormatXmlOptions} FormatXmlOptions
 * @typedef {import("@web/../lib/hoot-dom/hoot_dom_utils").InteractionDetails} InteractionDetails
 * @typedef {import("@web/../lib/hoot-dom/hoot_dom_utils").InteractionType} InteractionType
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
 *  message: AssertionMessage;
 *  name: string;
 *  predicate: () => boolean;
 * }} MatcherSpecifications
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
    parseFloat,
    performance,
    Promise,
    TypeError,
} = globalThis;
/** @type {Performance["now"]} */
const $now = performance.now.bind(performance);

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

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
 * @param {number} flags
 */
const formatMessage = (message, flags) =>
    message.replace(R_NOT, (_, ifTrue, ifFalse) =>
        flags & FLAGS.not ? ifFalse || "" : ifTrue || ""
    );

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
 * @param {number} depth amount of lines to remove from the stack
 */
const getStack = (depth) => {
    const error = new Error();
    if (!isFirefox()) {
        // remove ´Error´ in chrome
        depth++;
    }
    const lines = error.stack.split(R_LINE_RETURN).slice(depth + 1); // Remove `getStack`
    const hidden = lines.splice(MAX_STACK_LENGTH);
    if (hidden.length) {
        lines.push(`… ${hidden.length} more`);
    }
    return lines.join("\n");
};

/**
 * @param {Node} node
 * @param {string[]} keys
 * @returns {Record<string, string>}
 */
const getStyleValues = (node, keys) => {
    const nodeStyle = getStyle(node);
    const styleValues = Object.create(null);
    if (nodeStyle) {
        for (const key of keys) {
            styleValues[key] = nodeStyle.getPropertyValue(key) || nodeStyle[key];
        }
    }
    return styleValues;
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
 * @template T
 * @param {T[]} list
 * @param {string} separator
 * @param {string} [lastSeparator]
 * @returns {(T | string)[]}
 */
const listJoin = (list, separator, lastSeparator) => {
    if (list.length <= 1) {
        return list;
    }

    const rSeparator = isLabel(separator) ? separator : makeLabel(separator, null);
    const rLastSeparator = lastSeparator
        ? isLabel(lastSeparator)
            ? lastSeparator
            : makeLabel(lastSeparator, null)
        : rSeparator;

    const result = [];
    for (let i = 0; i < list.length; i++) {
        if (i === list.length - 1) {
            result.push(rLastSeparator);
        } else if (i > 0) {
            result.push(rSeparator);
        }
        result.push(list[i]);
    }
    return result;
};

/** @type {typeof makeLabel} */
const makeLabelOrString = (...args) => {
    const label = makeLabel(...args);
    return label[1] === null ? label[0] : label;
};

/**
 * @param {string} modifier
 * @param {string} message
 */
const matcherModifierError = (modifier, message) =>
    new HootError(`cannot use modifier "${modifier}": ${message}`);

/**
 * @param {string | Record<string, any>} style
 * @returns {Record<string, string>}
 */
const parseInlineStyle = (style) => {
    const styleObject = Object.create(null);
    if (typeof style === "string") {
        for (const styleProperty of style.split(";")) {
            const [key, value] = styleProperty.split(":");
            if (key && value) {
                styleObject[key.trim()] = value.trim();
            }
        }
    } else {
        for (const key in style) {
            styleObject[key] = style[key];
        }
    }
    return styleObject;
};

/** @type {StringConstructor["raw"]} */
const r = (template, ...substitutions) => makeLabel(String.raw(template, ...substitutions), null);

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

/**
 * @param {unknown} value
 * @param {string | number | RegExp} matcher
 */
const valueMatches = (value, matcher) => {
    if (matcher instanceof RegExp) {
        return matcher.test(value);
    }
    if (typeof matcher === "number") {
        value = parseFloat(value);
    }
    return strictEqual(value, matcher);
};

const ARROW_RIGHT = makeLabelIcon("fa fa-arrow-right text-sm");

const R_LINE_RETURN = /\n+/g;
const R_NOT = /\[([\w\s]*)!([\w\s]*)\]/;
const R_WHITE_SPACE = /\s+/g;

const FLAGS = {
    error: 0b1,
    headless: 0b10,
    not: 0b100,
    rejects: 0b1000,
    resolves: 0b10000,
};
const LABEL_EXPECTED = "Expected:";
const LABEL_RECEIVED = "Received:";
const MAX_STACK_LENGTH = 10;

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

        removeInteractionListener?.();

        currentResult.done();

        const {
            assertion: assertionCount = 0,
            error: errorCount = 0,
            query: queryCount = 0,
        } = currentResult.counts;

        // Expect without matchers
        if (unconsumedMatchers.size) {
            let times;
            switch (unconsumedMatchers.size) {
                case 1:
                    times = [r`once`];
                    break;
                case 2:
                    times = [r`twice`];
                    break;
                default:
                    times = [unconsumedMatchers.size, r`times`];
            }
            currentResult.registerEvent("assertion", {
                label: "expect",
                message: [r`called`, ...times, r`without calling any matchers`],
                pass: false,
            });
            unconsumedMatchers.clear();
        }

        // Unverified steps
        if (currentResult.currentSteps.length) {
            currentResult.registerEvent("assertion", {
                label: "step",
                message: [r`unverified steps`],
                pass: false,
                failedDetails: [Markup.red("Steps:", currentResult.currentSteps)],
            });
        }

        // Assertion & query event count
        if (!(assertionCount + queryCount)) {
            currentResult.registerEvent("assertion", {
                label: "assertions",
                message: [r`expected at least`, 1, r`assertion or query event, but none were run`],
                pass: false,
            });
        } else if (
            currentResult.expectedAssertions &&
            currentResult.expectedAssertions !== assertionCount
        ) {
            currentResult.registerEvent("assertion", {
                label: "assertions",
                message: [
                    r`expected`,
                    currentResult.expectedAssertions,
                    r`assertions, but`,
                    assertionCount,
                    r`were run`,
                ],
                pass: false,
            });
        }

        // Unverified errors
        if (currentResult.currentErrors.length) {
            currentResult.registerEvent("assertion", {
                label: "errors",
                message: [currentResult.currentErrors.length, r`unverified error(s)`],
                pass: false,
            });
        }

        // Error count
        if (currentResult.expectedErrors && currentResult.expectedErrors !== errorCount) {
            currentResult.registerEvent("assertion", {
                label: "errors",
                message: [
                    r`expected`,
                    currentResult.expectedErrors,
                    r`errors, but`,
                    errorCount,
                    r`were thrown`,
                ],
                pass: false,
            });
        }

        // "Todo" tag
        if (test?.config.todo) {
            if (currentResult.pass) {
                currentResult.registerEvent("assertion", {
                    label: "TODO",
                    message: [r`all assertions passed: remove "todo" test modifier`],
                    pass: false,
                });
            } else {
                currentResult.pass = true;
            }
        }

        // Abort status
        if (options?.aborted) {
            currentResult.registerEvent("assertion", {
                label: "aborted",
                message: [r`test was aborted, results may not be relevant`],
                pass: false,
            });
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
                assertions: assertionCount,
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
            currentResultInErrorState = false;
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
            test.results.push(new CaseResult(test, params.headless));

            // Must be retrieved from the list to be proxified
            currentResult = test.results.at(-1);
        } else {
            currentResult = new CaseResult(null, params.headless);
        }
        currentResultInErrorState = false;
        const listenedEvents = ["query"];
        if (!params.headless) {
            listenedEvents.push("interaction", "server");
        }
        removeInteractionListener = addInteractionListener(listenedEvents, onInteraction);
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
     * @param {Error} error
     * @returns {boolean} `true` if the error can be ignored
     */
    function onError(error) {
        if (!currentResult) {
            return false;
        }

        currentResult.registerEvent("error", error);
        currentResultInErrorState =
            currentResult.expectedErrors < (currentResult.counts.error || 0);

        return !currentResultInErrorState;
    }

    /**
     * @param {CustomEvent<InteractionDetails>} event
     */
    function onInteraction({ detail, type }) {
        if (!currentResult) {
            return;
        }

        currentResult.registerEvent(type, detail);
    }

    /**
     * @param {any} value
     */
    function step(value) {
        if (!currentResult) {
            throw scopeError("expect.step");
        }

        currentResult.registerEvent("step", value);
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

        const actualErrors = currentResult.consumeErrors();
        const pass =
            actualErrors.length === errors.length &&
            actualErrors.every(
                (error, i) =>
                    match(error, errors[i]) || (error.cause && match(error.cause, errors[i]))
            );

        const message = pass
            ? errors.length
                ? listJoin(errors, ARROW_RIGHT)
                : "no errors"
            : "expected the following errors";
        const assertion = {
            label: "verifyErrors",
            message,
            pass,
        };
        if (!pass) {
            const fActual = actualErrors.map(formatError);
            const fExpected = errors.map(formatError);
            assertion.failedDetails = detailsFromValuesWithDiff(fExpected, fActual);
            assertion.stack = getStack(0);
        }
        currentResult.registerEvent("assertion", assertion);
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

        const actualSteps = currentResult.consumeSteps();
        const pass = deepEqual(actualSteps, steps);
        const message = pass
            ? steps.length
                ? listJoin(steps, ARROW_RIGHT)
                : "no steps"
            : "expected the following steps";
        const assertion = {
            label: "verifySteps",
            message,
            pass,
        };
        if (!pass) {
            assertion.failedDetails = detailsFromValuesWithDiff(steps, actualSteps);
            assertion.stack = getStack(0);
        }
        currentResult.registerEvent("assertion", assertion);
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
     *  expect([1, 2, 3]).toEqual([1, 2, 3]);
     */
    function expect(received) {
        if (arguments.length > 1) {
            throw new HootError(`\`expect()\` only accepts a single argument`);
        }

        if (!currentResult) {
            throw scopeError("expect");
        }

        let flags = 0;
        if (currentResultInErrorState) {
            flags |= FLAGS.error;
        }
        if (params.headless) {
            flags |= FLAGS.headless;
        }

        return new Matcher(currentResult, received, flags);
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
        error: onError,
    };

    /** @type {CaseResult | null} */
    let currentResult = null;
    let currentResultInErrorState = false;

    let removeInteractionListener;

    return [enrichedExpect, expectHooks];
}

export class CaseResult {
    duration = 0;
    pass = true;
    /** @type {Test | null} */
    test = null;
    ts = $floor($now());

    /** @type {CaseEvent[]} */
    events = [];
    /** @type {Partial<Record<CaseEventType, number>>} */
    counts = Object.create(null);

    expectedAssertions = 0;
    expectedErrors = 0;

    currentErrors = [];
    currentSteps = [];

    /**
     * @param {Test | null} [test]
     * @param {boolean} [headless]
     */
    constructor(test, headless) {
        if (test) {
            this.test = test;
        }

        this.headless = Boolean(headless);

        markRaw(this);
    }

    consumeErrors() {
        const errors = this.currentErrors;
        this.currentErrors = [];
        return errors;
    }

    consumeSteps() {
        const steps = this.currentSteps;
        this.currentSteps = [];
        return steps;
    }

    /**
     * @param {CaseEventType} type
     */
    getEvents(type) {
        const nType = typeof type === "number" ? type : CASE_EVENT_TYPES[type].value;
        return this.events.filter((event) => event.type & nType);
    }

    done() {
        this.duration = $floor($now()) - this.ts;
    }

    /**
     *
     * @param {CaseEventType} type
     * @param {any} value
     */
    registerEvent(type, value) {
        let caseEvent;
        this.counts[type] ||= 0;
        this.counts[type]++;
        switch (type) {
            case "assertion": {
                caseEvent = new Assertion(this.counts.assertion, value);
                this.pass &&= caseEvent.pass;
                break;
            }
            case "error": {
                caseEvent = new CaseError(value);
                this.currentErrors.push(value);
                break;
            }
            case "step": {
                if (!this.headless) {
                    caseEvent = new Step(value);
                }
                this.currentSteps.push(deepCopy(value));
                break;
            }
            default: {
                if (!this.headless || type === "query") {
                    caseEvent = new DOMCaseEvent(type, value);
                }
                break;
            }
        }
        if (caseEvent) {
            this.events.push(caseEvent);
        }
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
     * @type {number}
     */
    _flags = 0;
    /**
     * @private
     * @type {R}
     */
    _received = null;
    /**
     * @private
     * @type {CaseResult}
     */
    _result;

    /**
     * @param {CaseResult} result
     * @param {R} received
     * @param {number} flags
     */
    constructor(result, received, flags) {
        this._flags = flags;
        this._result = result;
        this._received = received;

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
        if (this.flags & FLAGS.not) {
            throw matcherModifierError("not", `matcher is already negated`);
        }
        return this._clone(FLAGS.not);
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
        if (this._flags & (FLAGS.rejects | FLAGS.resolves)) {
            throw matcherModifierError(
                "rejects",
                `matcher value has already been wrapped in a promise resolver`
            );
        }
        return this._clone(FLAGS.rejects);
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
        if (this._flags & (FLAGS.rejects | FLAGS.resolves)) {
            throw matcherModifierError(
                "resolves",
                `matcher value has already been wrapped in a promise resolver`
            );
        }
        return this._clone(FLAGS.resolves);
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
            message:
                options?.message ||
                ((pass) =>
                    pass
                        ? [r`received value is[! not] strictly equal to`, received]
                        : [r`expected values to be strictly equal`]),
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
                message:
                    options?.message ||
                    ((pass) =>
                        pass
                            ? [r`received value is[! not] close to`, received]
                            : [r`expected values to be close to the given value`]),
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
            message:
                options?.message ||
                ((pass) =>
                    pass ? [received, r`is[! not] empty`] : [received, r`should[! not] be empty`]),
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
            message:
                options?.message ||
                ((pass) =>
                    pass
                        ? [received, r`is[! not] strictly greater than`, min]
                        : [r`expected value[! not] to be strictly greater`]),
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
            message:
                options?.message ||
                ((pass) =>
                    pass
                        ? [received, r`is[! not] an instance of`, cls]
                        : [r`expected value[! not] to be an instance of the given class`]),
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
            message:
                options?.message ||
                ((pass) =>
                    pass
                        ? [received, r`is[! not] strictly less than`, max]
                        : [r`expected value[! not] to be strictly less`]),
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
            message:
                options?.message ||
                ((pass) =>
                    pass
                        ? [received, r`is[! not] of type`, type]
                        : [r`expected value to be of the given type`]),
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
            message:
                options?.message ||
                ((pass) =>
                    pass
                        ? [received, r`is[! not] between`, min, r`and`, max]
                        : [r`expected value[! not] to be between given range`]),
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
            message:
                options?.message ||
                ((pass) =>
                    pass
                        ? [r`received value is[! not] deeply equal to`, received]
                        : [r`expected values to[! not] be deeply equal`]),
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
                message:
                    options?.message ||
                    ((pass) =>
                        pass
                            ? [received, r`has[! not] a length of`, length]
                            : [r`expected value[! not] to have the given length`]),
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
            message:
                options?.message ||
                ((pass) =>
                    pass
                        ? [received, r`[includes!does not include]`, item]
                        : [r`expected object[! not] to include the given item`]),
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
            message:
                options?.message ||
                ((pass) =>
                    pass
                        ? [received, r`[matches!does not match]`, matcher]
                        : [r`expected value[! not] to match the given matcher`]),
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
            const isAsync = this._flags & (FLAGS.rejects | FLAGS.resolves);
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
                message:
                    options?.message ||
                    ((pass) =>
                        pass
                            ? [
                                  received,
                                  r`did[! not] ${isAsync ? "reject" : "throw"} a matching value`,
                              ]
                            : [
                                  received,
                                  r`${
                                      isAsync ? "rejected" : "threw"
                                  } a value that did not match the given matcher`,
                              ]),
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
            const elMap = new ElementMap(received, (el) => el.matches?.(pseudo));
            return {
                name: "toBeChecked",
                acceptedType: ["string", "node", "node[]"],
                predicate: each(elMap.values(), Boolean),
                message:
                    options?.message ||
                    ((pass) =>
                        pass
                            ? [elMap, r`are[! not] ${prop}`]
                            : [r`expected`, elMap, r`[! not] to be ${prop}`]),
                failedDetails: () => detailsFromValues(elMap.getValues()),
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
            const elMap = new ElementMap(received);
            const displayed = [];
            const notDisplayed = [];
            for (const [el] of elMap) {
                if (isNodeDisplayed(el)) {
                    displayed.push(el);
                } else {
                    notDisplayed.push(el);
                }
            }
            return {
                name: "toBeDisplayed",
                acceptedType: ["string", "node", "node[]"],
                predicate: () => elMap.size && elMap.size === displayed.length,
                message:
                    options?.message ||
                    ((pass) =>
                        pass
                            ? [elMap, r`are[! not] displayed`]
                            : [r`expected`, elMap, r`[! not] to be displayed`]),
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
            const elMap = new ElementMap(received, (el) => el.matches?.(":enabled"));
            return {
                name: "toBeEnabled",
                acceptedType: ["string", "node", "node[]"],
                predicate: each(elMap.values(), Boolean),
                message:
                    options?.message ||
                    ((pass) =>
                        pass
                            ? [elMap, r`are [enabled!disabled]`]
                            : [r`expected`, elMap, r`to be [enabled!disabled]`]),
                failedDetails: () => detailsFromValues(elMap.getElements()),
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
            const elMap = new ElementMap(received, (el) => getActiveElement(el));
            return {
                name: "toBeFocused",
                acceptedType: ["string", "node", "node[]"],
                predicate: each(elMap, ([el, activeEl]) => el === activeEl),
                message:
                    options?.message ||
                    ((pass) =>
                        pass
                            ? [elMap, r`are[! not] focused`]
                            : [elMap, r`should[! not] be focused`]),
                failedDetails: () =>
                    detailsFromObject({
                        "Focused:": elMap.getValues(),
                        [LABEL_RECEIVED]: elMap.getElements(),
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
            const elMap = new ElementMap(received);
            const visible = [];
            const hidden = [];
            for (const [el] of elMap) {
                if (isNodeVisible(el)) {
                    visible.push(el);
                } else {
                    hidden.push(el);
                }
            }
            return {
                name: "toBeVisible",
                acceptedType: ["string", "node", "node[]"],
                predicate: () => elMap.size && elMap.size === visible.length,
                message:
                    options?.message ||
                    ((pass) =>
                        pass
                            ? [elMap, r`are [visible!hidden]`]
                            : [r`expected`, elMap, r`to be [visible!hidden]`]),
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

        return this._resolve((received) => {
            const elMap = new ElementMap(received, (el) => getNodeAttribute(el, attribute));
            return {
                name: "toHaveAttribute",
                acceptedType: ["string", "node", "node[]"],
                predicate: each(elMap, ([el, elAttr]) =>
                    expectsValue ? valueMatches(elAttr, value) : el.hasAttribute(attribute)
                ),
                message:
                    options?.message ||
                    ((pass) =>
                        pass
                            ? [
                                  r`attribute`,
                                  attribute,
                                  r`on`,
                                  elMap,
                                  ...(expectsValue
                                      ? [r`[matches!does not match]`, value]
                                      : [r`is[! not] set`]),
                              ]
                            : [
                                  elMap,
                                  r`do not have the correct attribute${
                                      expectsValue ? " value" : ""
                                  }`,
                              ]),

                failedDetails: () =>
                    elMap.getValues((val) =>
                        detailsFromValuesWithDiff(expectsValue ? value : attribute, val)
                    ),
            };
        });
    }

    /**
     * Expects the received {@link Target} to have the given class name(s).
     *
     * @param {string | string[]} className
     * @param {ExpectOptions & ClassListOptions} [options]
     * @example
     *  expect("inline").toHaveClass("btn btn-primary");
     * @example
     *  expect("body").toHaveClass(["o_webclient", "o_dark"]);
     */
    toHaveClass(className, options) {
        this._saveStack();

        ensureArguments(arguments, ["string", "string[]"], ["object", null]);

        const rawClassNames = ensureArray(className);
        const classNames = rawClassNames.flatMap((cls) => cls.trim().split(R_WHITE_SPACE)).sort();

        return this._resolve((received) => {
            const elMap = new ElementMap(received, (el) => [...el.classList].sort());
            return {
                name: "toHaveClass",
                acceptedType: ["string", "node", "node[]"],
                predicate: each(elMap.values(), (classes) =>
                    options?.exact
                        ? deepEqual(classNames, classes)
                        : classNames.every((cls) => classes.includes(cls))
                ),
                message:
                    options?.message ||
                    ((pass) =>
                        pass
                            ? [
                                  elMap,
                                  r`[have!do not have] class${classNames.length === 1 ? "" : "es"}`,
                                  ...listJoin(classNames, ",", "and"),
                              ]
                            : [
                                  r`expected`,
                                  elMap,
                                  r`[to have all!not to have any] of the given class names`,
                              ]),
                failedDetails: () =>
                    elMap.getValues((classes) =>
                        detailsFromValues(classNames.join(" "), classes.join(" "))
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

        const anyAmount = isNil(amount);
        return this._resolve((received) => {
            const elMap = new ElementMap(received);
            return {
                name: "toHaveCount",
                acceptedType: ["string", "node", "node[]"],
                predicate: () => (anyAmount ? elMap.size > 0 : strictEqual(elMap.size, amount)),
                message:
                    options?.message ||
                    ((pass) =>
                        pass
                            ? [
                                  r`there are[${anyAmount ? " some" : ""}! ${
                                      anyAmount ? "no" : "not"
                                  }]`,
                                  ...(anyAmount ? [] : [amount]),
                                  elMap,
                              ]
                            : [r`there is an incorrect amount of`, elMap]),
                failedDetails: () => [
                    ...detailsFromValues(anyAmount ? "any" : amount, elMap.size),
                    Markup.red("Elements:", elMap.getElements()),
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
        return this._resolve((received) => {
            const elMap = new ElementMap(received, (el) => el[property]);
            return {
                name: "toHaveProperty",
                acceptedType: ["string", "node", "node[]"],
                predicate: each(elMap, ([el, elProp]) =>
                    expectsValue ? valueMatches(elProp, value) : property in el
                ),
                message:
                    options?.message ||
                    ((pass) =>
                        pass
                            ? [
                                  r`property`,
                                  property,
                                  r`on`,
                                  elMap,
                                  ...(expectsValue
                                      ? [r`[matches!does not match]`, value]
                                      : [r`is[! not] set`]),
                              ]
                            : [
                                  elMap,
                                  r`do not have the correct property${
                                      expectsValue ? " value" : ""
                                  }`,
                              ]),
                failedDetails: () =>
                    elMap.getValues((val) =>
                        detailsFromValuesWithDiff(expectsValue ? value : property, val)
                    ),
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
            const elMap = new ElementMap(received, (el) => getNodeRect(el, options));
            return {
                name: "toHaveRect",
                acceptedType: ["string", "node", "node[]"],
                predicate: each(elMap.values(), (elRect) =>
                    entries.every(([key, value]) => strictEqual(elRect[key], value))
                ),
                message:
                    options?.message ||
                    ((pass) =>
                        pass
                            ? [elMap, r`have the expected DOM rect of`, rect]
                            : [r`expected`, elMap, r`to have the given DOM rect`]),
                failedDetails: () =>
                    detailsFromValuesWithDiff(
                        rect,
                        $fromEntries(entries.map(([key]) => [key, elMap.first[key]]))
                    ),
            };
        });
    }

    /**
     * Expects the received {@link Target} to match the given style properties.
     *
     * @param {string | Record<string, string | RegExp>} style
     * @param {ExpectOptions & DOMStyleOptions} [options]
     * @example
     *  expect("button").toHaveStyle({ color: "red" });
     * @example
     *  expect("p").toHaveStyle("text-align: center");
     */
    toHaveStyle(style, options) {
        this._saveStack();

        ensureArguments(arguments, ["string", "object"], ["object", null]);

        const styleDef = parseInlineStyle(style);
        const styleKeys = $keys(styleDef).sort();

        return this._resolve((received) => {
            const elMap = new ElementMap(received, (el) =>
                options?.inline
                    ? parseInlineStyle(el.getAttribute("style"))
                    : getStyleValues(el, $keys(styleDef))
            );
            return {
                name: "toHaveStyle",
                acceptedType: ["string", "node", "node[]"],
                predicate: each(
                    elMap.values(),
                    (elStyle) =>
                        styleKeys.every((key) => valueMatches(elStyle[key], styleDef[key])) &&
                        (!options?.exact || deepEqual(styleKeys, $keys(elStyle)))
                ),
                message:
                    options?.message ||
                    ((pass) =>
                        pass
                            ? [
                                  elMap,
                                  r`have the expected style values for`,
                                  ...listJoin($keys(styleDef), ",", "and"),
                              ]
                            : [
                                  r`expected`,
                                  elMap,
                                  r`[to have all!not to have any] of the given style properties`,
                              ]),
                failedDetails: () =>
                    detailsFromValuesWithDiff(
                        styleDef,
                        $fromEntries(styleKeys.map((key) => [key, elMap.first[key]]))
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

        const expectsText = !isNil(text);

        return this._resolve((received) => {
            const elMap = new ElementMap(received, (el) => getNodeText(el, options));
            return {
                name: "toHaveText",
                acceptedType: ["string", "node", "node[]"],
                predicate: each(elMap.values(), (elText) =>
                    expectsText ? valueMatches(elText, text) : elText.length > 0
                ),
                message:
                    options?.message ||
                    ((pass) =>
                        pass
                            ? [elMap, r`[have!do not have] text`, text]
                            : [r`expected`, elMap, r`[! not] to have the given text`]),
                failedDetails: () => elMap.getValues((val) => detailsFromValuesWithDiff(text, val)),
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

        const expectsValue = !isNil(value);

        return this._resolve((received) => {
            const elMap = new ElementMap(received, (el) => getNodeValue(el));
            return {
                name: "toHaveValue",
                acceptedType: ["string", "node", "node[]"],
                predicate: each(elMap, ([el, elValue]) => {
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
                            return deepEqual(elValue, value);
                        }
                        elValue = el.value;
                    }
                    return valueMatches(elValue, value);
                }),
                message:
                    options?.message ||
                    ((pass) =>
                        pass
                            ? [elMap, r`[have!do not have] value`, value]
                            : [r`expected`, elMap, r`[! not] to have the given value`]),
                failedDetails: () =>
                    elMap.getValues((val) => detailsFromValuesWithDiff(value, val)),
            };
        });
    }

    //-------------------------------------------------------------------------
    // Private methods
    //-------------------------------------------------------------------------

    /**
     * @private
     * @param {number} flags
     */
    _clone(flags) {
        unconsumedMatchers.delete(this);
        return new this.constructor(this._result, this._received, this._flags | flags);
    }

    /**
     * @private
     * @param {() => MatcherSpecifications<R, A>} specCallback
     * @returns {Async extends true ? Promise<void> : void}
     */
    _resolve(specCallback) {
        unconsumedMatchers.delete(this);
        const isAsync = this._flags & (FLAGS.rejects | FLAGS.resolves);
        if (this._flags & FLAGS.error) {
            // Prevent further assertions in error state
            return isAsync ? new Promise(() => {}) : undefined;
        }
        if (isAsync) {
            return Promise.resolve(this._received).then(
                /** @param {PromiseFulfilledResult<R>} reason */
                (result) => {
                    if (this._flags & FLAGS.rejects) {
                        this._result.registerEvent("assertion", {
                            label: "rejects",
                            message: [
                                r`expected promise to reject, instead resolved with:`,
                                result,
                            ],
                            pass: false,
                        });
                    } else {
                        this._received = result;
                        this._resolveFinalResult(specCallback);
                    }
                },
                /** @param {PromiseRejectedResult} reason */
                (reason) => {
                    if (this._flags & FLAGS.resolves) {
                        this._result.registerEvent("assertion", {
                            label: "resolves",
                            message: [
                                r`expected promise to resolve, instead rejected with:`,
                                reason,
                            ],
                            pass: false,
                        });
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
                `expected received value to be of type ${listJoin(types, ",", "or").join(
                    " "
                )}, got ${formatHumanReadable(this._received)}`
            );
        }

        const not = this._flags & FLAGS.not;
        let pass = predicate();
        if (not) {
            pass = !pass;
        }
        const assertion = {
            label: name,
            message,
            flags: this._flags,
            pass,
        };
        if (!pass) {
            assertion.failedDetails = failedDetails().filter(Boolean);
            assertion.stack = currentStack;
        }
        this._result.registerEvent("assertion", assertion);
    }

    /**
     * @private
     */
    _saveStack() {
        if (!this._flags & FLAGS.headless) {
            currentStack = getStack(1);
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
            const elMap = new ElementMap(received, (el) =>
                // Force HTML type here as it will be returned by outer/inner HTML
                formatXml(el[property], { ...options, type: "html" })
            );
            return {
                name,
                acceptedType: ["string", "node", "node[]"],
                predicate: each(elMap.values(), (elHtml) => valueMatches(elHtml, expected)),
                message:
                    options?.message ||
                    ((pass) =>
                        pass
                            ? [property, r`of`, elMap, r`is[! not] equal to expected value`]
                            : [r`expected`, property, r`of`, elMap, r`to match the given value`]),
                failedDetails: () =>
                    elMap.getValues((val) => detailsFromValuesWithDiff(expected, val)),
            };
        });
    }
}

//-----------------------------------------------------------------------------
// Case events
//-----------------------------------------------------------------------------

export class CaseEvent {
    label = "";
    /** @type {(string | Label)[]} */
    message = [];
    ts = $floor($now());
    /** @type {number} */
    type;
}

export class Assertion extends CaseEvent {
    type = CASE_EVENT_TYPES.assertion.value;

    /**
     * @param {number} number
     * @param {Partial<Assertion & { message: AssertionMessage }>} values
     */
    constructor(number, values) {
        super();

        this.label = values.label;
        /** @type {[any, any][] | null} */
        this.failedDetails = values.failedDetails || null;
        this.flags = values.flags || 0;
        this.pass = values.pass || false;
        this.number = number;
        /** @type {string} */
        this.stack = values.stack;

        let { message } = values;
        if (typeof message === "function") {
            message = message(this.pass, r);
        }

        const parts = $isArray(message) && !isLabel(message) ? message : [makeLabel(message, null)];
        for (const part of parts) {
            if (part instanceof ElementMap) {
                if (typeof part.selector === "string") {
                    this.message.push("elements matching", makeLabelOrString(part.selector));
                } else {
                    const elements = part.keys();
                    this.message.push(
                        "elements",
                        makeLabelOrString(part.size === 1 ? elements.next().value : [...elements])
                    );
                }
            } else if (isLabel(part)) {
                if (part[1] === "icon") {
                    this.message.push(part);
                } else {
                    this.message.push(
                        makeLabelOrString(formatMessage(part[0], this.flags & FLAGS.not), part[1])
                    );
                }
            } else if (typeof part === "string") {
                this.message.push(makeLabelOrString(formatMessage(part, this.flags & FLAGS.not)));
            } else {
                this.message.push(makeLabelOrString(part));
            }
        }
    }

    /**
     * @param {keyof typeof FLAGS} name
     */
    hasFlag(name) {
        return this.flags & FLAGS[name];
    }
}

export class DOMCaseEvent extends CaseEvent {
    /**
     * @param {InteractionType} type
     * @param {InteractionDetails} details
     */
    constructor(type, [name, args, returnValue]) {
        super();

        this.type = CASE_EVENT_TYPES[type].value;
        this.label = name;
        for (let i = 0; i < args.length; i++) {
            if (args[i] !== undefined && (i === 0 || typeof args[i] !== "object")) {
                this.message.push(makeLabelOrString(args[i]));
            }
        }
        if (returnValue && type === "query" && returnValue !== args[0]) {
            this.message.push(ARROW_RIGHT, makeLabelOrString(returnValue));
        }
    }
}

export class CaseError extends CaseEvent {
    type = CASE_EVENT_TYPES.error.value;

    /**
     * @param {Error} error
     */
    constructor(error) {
        super();

        /** @type {Error | null} */
        this.cause = error.cause || null;
        this.label = error.name;
        this.message = error.message.split(R_WHITE_SPACE);
        /** @type {string} */
        this.stack = error.stack;
    }
}

export class Step extends CaseEvent {
    type = CASE_EVENT_TYPES.step.value;
    label = "step";

    /**
     * @param {any} value
     */
    constructor(value) {
        super();

        this.message = [makeLabel(value)];
    }
}
