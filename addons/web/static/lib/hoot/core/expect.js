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
import { Deferred } from "@web/../lib/hoot-dom/helpers/time";
import {
    addInteractionListener,
    getColorHex,
    isFirefox,
    isIterable,
    R_WHITE_SPACE,
} from "@web/../lib/hoot-dom/hoot_dom_utils";
import {
    CASE_EVENT_TYPES,
    deepCopy,
    deepEqual,
    ElementMap,
    ensureArguments,
    ensureArray,
    formatHumanReadable,
    getConstructor,
    HootError,
    isLabel,
    isNil,
    isOfType,
    makeLabel,
    makeLabelIcon,
    Markup,
    match,
    S_ANY,
    S_NONE,
    strictEqual,
} from "../hoot_utils";
import { logger } from "./logger";
import { Test } from "./test";

/**
 * @typedef {{
 *  aborted?: boolean;
 *  debug?: boolean;
 * }} AfterTestOptions
 *
 * @typedef {import("../hoot_utils").ArgumentType} ArgumentType
 *
 * @typedef {string | ((pass: boolean) => string)} AssertionMessage
 *
 * @typedef {string | string[] | ((pass: boolean, raw: typeof String["raw"]) => string | string[])} AssertionReportMessage
 *
 * @typedef {VerifierOptions & {
 *  timeout?: number;
 * }} AsyncVerifierOptions
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
 *  not?: boolean;
 *  rejects?: boolean;
 *  resolves?: boolean;
 *  silent?: boolean;
 * }} ExpectOptions
 *
 * @typedef {DeepEqualOptions & {
 *  message?: AssertionMessage;
 * }} VerifierOptions
 *
 * @typedef {import("../hoot_utils").DeepEqualOptions} DeepEqualOptions
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
 * @template T
 * @typedef {T & {
 *  deferred: Deferred<boolean>;
 *  options: VerifierOptions
 *  timeout: number;
 * }} AsyncResolver
 */

/**
 * @template [R=unknown]
 * @template [A=R]
 * @typedef {{
 *  acceptedType: ArgumentType | ArgumentType[];
 *  getFailedDetails: () => unknown[];
 *  mapElements: (received: Target) => ElementMap;
 *  message: AssertionMessage;
 *  name: string;
 *  onFail: AssertionReportMessage;
 *  onPass: AssertionReportMessage;
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
    clearTimeout,
    Error,
    Math: { abs: $abs, floor: $floor },
    Object: { assign: $assign, create: $create, entries: $entries, keys: $keys },
    parseFloat,
    performance,
    Promise,
    setTimeout,
    TypeError,
    WeakMap,
} = globalThis;
/** @type {Performance["now"]} */
const $now = performance.now.bind(performance);

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @param {[string, unknown][]} entries
 */
function detailsFromEntries(entries) {
    const result = [];
    const expected = entries.at(-2);
    if (expected) {
        result.push(Markup.expected(expected[0] || LABEL_EXPECTED, expected[1]));
    }
    const received = entries.at(-1);
    if (received) {
        result.push(Markup.received(received[0] || LABEL_RECEIVED, received[1]));
    }
    return result;
}

/**
 * @param {...unknown} args
 */
function detailsFromValues(...args) {
    return detailsFromEntries(args.map((arg) => [null, arg]));
}

/**
 * @param {...unknown} args
 */
function detailsFromValuesWithDiff(...args) {
    return [...detailsFromValues(...args), Markup.diff(...args)];
}

/**
 * @param {Error} [error]
 */
function formatError(error) {
    let strError = error ? String(error) : "";
    if (error?.cause) {
        strError += `\n${formatError(error.cause)}`;
    }
    return strError;
}

/**
 * @param {string} message
 * @param {boolean} plural
 * @param {boolean} not
 */
function formatMessage(message, plural, not) {
    return message.replaceAll(R_PLURAL, plural ? "$2" : "$1").replaceAll(R_NOT, not ? "$2" : "$1");
}

/**
 * @param {Iterable<unknown> | Record<unknown, unknown>} object
 */
function getLength(object) {
    if (typeof object === "string" || $isArray(object)) {
        return object.length;
    }
    if (isIterable(object)) {
        return [...object].length;
    }
    return $keys(object).length;
}

/**
 * @param {number} depth amount of lines to remove from the stack
 */
function getStack(depth) {
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
}

/**
 * @param {Node} node
 * @param {string[]} keys
 * @returns {Record<string, string>}
 */
function getStyleValues(node, keys) {
    const nodeStyle = getStyle(node);
    const styleValues = $create(null);
    if (nodeStyle) {
        for (const key of keys) {
            styleValues[key] = nodeStyle.getPropertyValue(key) || nodeStyle[key];
        }
    }
    return styleValues;
}

/**
 * @param {Iterable<unknown> | Record<unknown, unknown>} object
 * @param {unknown} item
 * @returns {boolean}
 */
function includes(object, item) {
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
    return item in object;
}

/**
 * @template T
 * @param {T[]} list
 * @param {string} separator
 * @param {string} [lastSeparator]
 * @returns {(T | string)[]}
 */
function listJoin(list, separator, lastSeparator) {
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
}

/** @type {typeof makeLabel} */
function makeLabelOrString(...args) {
    const label = makeLabel(...args);
    if (logger.allows("debug")) {
        debugLabelCache.set(label, args[0]);
    }
    return label[1] === null ? label[0] : label;
}

/**
 * @param {string} modifier
 * @param {string} message
 */
function matcherModifierError(modifier, message) {
    return new HootError(`cannot use modifier "${modifier}": ${message}`);
}

/**
 * @param {string | Record<string, unknown>} style
 * @param {unknown} [defaultValue]
 */
function parseInlineStyle(style, defaultValue) {
    /** @type {Record<string, string>} */
    const styleObject = $create(null);
    if (typeof style === "string") {
        for (const styleProperty of style.split(";")) {
            const [key, value] = styleProperty.split(":");
            if (key && (value ?? defaultValue)) {
                styleObject[key.trim()] = value?.trim() || defaultValue;
            }
        }
    } else {
        for (const key in style) {
            styleObject[key] = style[key];
        }
    }
    return styleObject;
}

/** @type {StringConstructor["raw"]} */
function r(template, ...substitutions) {
    return makeLabel(String.raw(template, ...substitutions), null);
}

/**
 * @param {string} method
 */
function scopeError(method) {
    return new HootError(`cannot call \`${method}()\` outside of a test`);
}

/**
 * @param {unknown} value
 * @param {string | number | RegExp} matcher
 */
function valueMatches(value, matcher) {
    if (matcher === S_ANY) {
        return !isNil(value);
    }
    if (matcher instanceof RegExp) {
        return matcher.test(value);
    }
    if (typeof matcher === "number") {
        value = parseFloat(value);
    }
    return strictEqual(value, matcher);
}

const AMPERSAND = makeLabel("&", null);
const ARROW_RIGHT = makeLabelIcon("fa fa-arrow-right text-sm");

const R_LINE_RETURN = /\n+/g;
const R_NOT = /\[([\w\s]*)!([\w\s]*)\]/g;
const R_PLURAL = /\[([\w\s]*)%([\w\s]*)\]/g;

const FLAGS = {
    error: 0b1,
    headless: 0b10,
    not: 0b100,
    rejects: 0b1000,
    resolves: 0b10000,
    silent: 0b100000,
};
const LABEL_EXPECTED = "Expected:";
const LABEL_RECEIVED = "Received:";
/** @type {CaseEventType[]} */
const CASE_EVENT_LOG_COLORS = ["assertion", "query", "step", "time"];
const MAX_STACK_LENGTH = 10;

/** @type {WeakMap<any, any>} */
const debugLabelCache = new WeakMap();
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
                pass: false,
                reportMessage: [r`called`, ...times, r`without calling any matchers`],
            });
            unconsumedMatchers.clear();
        }

        // Unverified steps
        if (currentResult.currentSteps.length) {
            currentResult.registerEvent("assertion", {
                label: "step",
                pass: false,
                failedDetails: detailsFromEntries([["Steps:", currentResult.currentSteps]]),
                reportMessage: [r`unverified steps`],
            });
        }

        // Assertion & query event count
        if (!(assertionCount + queryCount)) {
            currentResult.registerEvent("assertion", {
                label: "assertions",
                pass: false,
                reportMessage: [
                    r`expected at least`,
                    1,
                    r`assertion or query event, but none were run`,
                ],
            });
        } else if (
            currentResult.expectedAssertions &&
            currentResult.expectedAssertions !== assertionCount
        ) {
            currentResult.registerEvent("assertion", {
                label: "assertions",
                pass: false,
                reportMessage: [
                    r`expected`,
                    currentResult.expectedAssertions,
                    r`assertions, but`,
                    assertionCount,
                    r`were run`,
                ],
            });
        }

        // Unverified errors
        if (currentResult.currentErrors.length) {
            currentResult.registerEvent("assertion", {
                label: "errors",
                pass: false,
                reportMessage: [currentResult.currentErrors.length, r`unverified error(s)`],
            });
        }

        // Error count
        if (currentResult.expectedErrors && currentResult.expectedErrors !== errorCount) {
            currentResult.registerEvent("assertion", {
                label: "errors",
                pass: false,
                reportMessage: [
                    r`expected`,
                    currentResult.expectedErrors,
                    r`errors, but`,
                    errorCount,
                    r`were thrown`,
                ],
            });
        }

        // "Todo" tag
        if (test?.config.todo) {
            if (currentResult.pass) {
                currentResult.registerEvent("assertion", {
                    label: "TODO",
                    pass: false,
                    reportMessage: [r`all assertions passed: remove "todo" test modifier`],
                });
            } else {
                currentResult.pass = true;
            }
        }

        // Abort status
        if (options?.aborted) {
            currentResult.registerEvent("assertion", {
                label: "aborted",
                pass: false,
                reportMessage: [r`test was aborted, results may not be relevant`],
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
            listenedEvents.push("interaction", "server", "time");
        }
        removeInteractionListener = addInteractionListener(listenedEvents, onInteraction);
    }

    /**
     * @param {{ errors: unknown[]; options: VerifierOptions }} resolver
     * @param {boolean} forceCheck
     */
    function checkErrors(resolver, forceCheck) {
        if (!resolver) {
            return false;
        }
        const { errors, options } = resolver;
        const actualErrors = currentResult.currentErrors;
        const pass =
            actualErrors.length === errors.length &&
            actualErrors.every(
                (error, i) =>
                    match(error, errors[i]) || (error.cause && match(error.cause, errors[i]))
            );

        if (pass || forceCheck) {
            currentResult.consumeErrors();

            const reportMessage = pass
                ? errors.length
                    ? listJoin(errors, ARROW_RIGHT)
                    : "no errors"
                : "expected the following errors";
            const assertion = {
                label: "verifyErrors",
                message: options?.message,
                pass,
                reportMessage,
            };
            if (!pass) {
                const fActual = actualErrors.map(formatError);
                const fExpected = errors.map(formatError);
                assertion.failedDetails = detailsFromValuesWithDiff(fExpected, fActual);
                assertion.stack = getStack(1);
            }
            currentResult.registerEvent("assertion", assertion);
        }

        return pass;
    }

    /**
     * @param {{ steps: unknown[]; options: VerifierOptions } | null} resolver
     * @param {boolean} forceCheck
     */
    function checkSteps(resolver, forceCheck) {
        if (!resolver) {
            return false;
        }
        const { steps, options } = resolver;
        const receivedSteps = currentResult.currentSteps;
        const pass = deepEqual(steps, receivedSteps, options);

        if (pass || forceCheck) {
            currentResult.consumeSteps();

            const separator = options?.ignoreOrder ? AMPERSAND : ARROW_RIGHT;
            const reportMessage = pass
                ? receivedSteps.length
                    ? listJoin(receivedSteps, separator)
                    : "no steps"
                : "expected the following steps";
            const assertion = {
                label: "verifySteps",
                message: options?.message,
                pass,
                reportMessage,
            };
            if (!pass) {
                assertion.failedDetails = detailsFromValuesWithDiff(steps, receivedSteps);
                assertion.stack = getStack(1);
            }
            currentResult.registerEvent("assertion", assertion);
        }

        return pass;
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

        checkErrors(currentResult.errorResolver, false);

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
     * @param {unknown} value
     */
    function step(value) {
        if (!currentResult) {
            throw scopeError("expect.step");
        }

        currentResult.registerEvent("step", value);

        checkSteps(currentResult.stepResolver, false);
    }

    /**
     * Expects the received matchers to match the errors thrown since the start
     * of the test or the last call to {@link verifyErrors}. Calling this matcher
     * will reset the list of current errors.
     *
     * @param {unknown[]} errors
     * @param {VerifierOptions} [options]
     * @returns {boolean}
     * @example
     *  expect.verifyErrors([/RPCError/, /Invalid domain AST/]);
     */
    function verifyErrors(errors, options) {
        if (!currentResult) {
            throw scopeError("expect.verifyErrors");
        }
        ensureArguments(arguments, "any[]", ["object", null]);

        return checkErrors({ errors, options }, true);
    }

    /**
     * Expects the received steps to be equal to the steps emitted since the start
     * of the test or the last call to {@link verifySteps}. Calling this matcher
     * will reset the list of current steps.
     *
     * @param {unknown[]} steps
     * @param {VerifierOptions} [options]
     * @returns {boolean}
     * @example
     *  expect.verifySteps(["web_read_group", "web_search_read"]);
     */
    function verifySteps(steps, options) {
        if (!currentResult) {
            throw scopeError("expect.verifySteps");
        }
        ensureArguments(arguments, "any[]", ["object", null]);

        return checkSteps({ steps, options }, true);
    }

    /**
     * Same as {@link verifyErrors}, but will not immediatly fail if errors are
     * not caught yet, and will instead wait for a certain timeout (default: 2000ms)
     * to allow errors to be caught later.
     *
     * Checks are performed initially, at the end of the timeout, and each time
     * an error is detected.
     *
     * @param {unknown[]} errors
     * @param {AsyncVerifierOptions} [options]
     * @returns {Promise<boolean>}
     * @example
     *  fetch("invalid/url");
     *  await expect.waitForErrors([/RPCError/]);
     */
    function waitForErrors(errors, options) {
        if (!currentResult) {
            throw scopeError("expect.waitForErrors");
        }
        ensureArguments(arguments, "any[]", ["object", null]);

        // Run check for any current resolver (if any)
        checkErrors(currentResult.errorResolver, true);

        // Run early check if conditions are already met
        if (checkErrors({ errors, options }, false)) {
            return true;
        }

        currentResult.errorResolver = {
            errors,
            options,
            deferred: new Deferred(),
            timeout: setTimeout(
                () => checkErrors(currentResult.errorResolver, true),
                options?.timeout ?? 2000
            ),
        };
        return currentResult.errorResolver.deferred;
    }

    /**
     * Same as {@link verifySteps}, but will not immediatly fail if steps have not
     * been registered yet, and will instead wait for a certain timeout (default:
     * 2000ms) to allow steps to be registered later.
     *
     * Checks are performed initially, at the end of the timeout, and each time
     * a step is registered.
     *
     * @param {unknown[]} steps
     * @param {AsyncVerifierOptions} [options]
     * @returns {Promise<boolean>}
     * @example
     *  fetch(".../call_kw/web_read_group");
     *  await expect.waitForSteps(["web_read_group"]);
     */
    async function waitForSteps(steps, options) {
        if (!currentResult) {
            throw scopeError("expect.waitForSteps");
        }
        ensureArguments(arguments, "any[]", ["object", null]);

        // Run check for any current resolver (if any)
        checkSteps(currentResult.stepResolver, true);

        // Run early check if conditions are already met
        if (checkSteps({ steps, options }, false)) {
            return true;
        }

        currentResult.stepResolver = {
            steps,
            options,
            deferred: new Deferred(),
            timeout: setTimeout(
                () => checkSteps(currentResult.stepResolver, true),
                options?.timeout ?? 2000
            ),
        };
        return currentResult.stepResolver.deferred;
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
        waitForErrors,
        waitForSteps,
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
    counts = $create(null);

    expectedAssertions = 0;
    expectedErrors = 0;

    currentErrors = [];
    currentSteps = [];
    /** @type {AsyncResolver<{ errors: unknown[] }> | null} */
    errorResolver = null;
    /** @type {AsyncResolver<{ steps: unknown[] }> | null} */
    stepResolver = null;

    /**
     * @param {Test | null} [test]
     * @param {boolean} [headless]
     */
    constructor(test, headless) {
        if (test) {
            this.test = test;
        }

        this.headless = !!headless;

        markRaw(this);
    }

    consumeErrors() {
        if (this.errorResolver) {
            clearTimeout(this.errorResolver.timeout);
            this.errorResolver.deferred.resolve(true);
            this.errorResolver = null;
        }
        this.currentErrors = [];
    }

    consumeSteps() {
        if (this.stepResolver) {
            clearTimeout(this.stepResolver.timeout);
            this.stepResolver.deferred.resolve(true);
            this.stepResolver = null;
        }
        this.currentSteps = [];
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
     * @param {unknown} value
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
            if (logger.allows("debug") && CASE_EVENT_LOG_COLORS.includes(type)) {
                const colorName = caseEvent.pass === false ? "rose" : CASE_EVENT_TYPES[type].color;
                const logArgs = [[caseEvent.label, getColorHex(colorName)]];
                for (const part of caseEvent.message) {
                    if (isLabel(part)) {
                        // Get and consume cached original values
                        logArgs.push(debugLabelCache.get(part) ?? part[0]);
                        debugLabelCache.delete(part);
                    } else {
                        logArgs.push(part);
                    }
                }
                if (caseEvent.additionalMessage) {
                    logArgs.push("\n", { message: caseEvent.additionalMessage });
                }
                logger.logTestEvent(...logArgs);
            }
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
        if (this._flags & FLAGS.not) {
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
        this._ensureArguments(arguments, "any");

        return this._resolve(() => ({
            name: "toBe",
            acceptedType: "any",
            predicate: (received) => strictEqual(expected, received),
            message: options?.message,
            onPass: () => [r`received value is[! not] strictly equal to`, this._received],
            onFail: () => [r`expected values to be strictly equal`],
            getFailedDetails: (received) => detailsFromValuesWithDiff(expected, received),
        }));
    }

    /**
     * Expects the received value to be close to the `expected` value by a given
     * margin (i.e. the maximum difference allowed between the 2, default is 1).
     *
     * Note: the margin is exclusive; it should be strictly larger than the diff.
     *
     * @param {R} expected
     * @param {ExpectOptions & { margin?: number }} [options]
     * @example
     *  expect(0.2 + 0.1).toBeCloseTo(0.3);
     * @example
     *  expect(3.51).toBeCloseTo(3.5, { margin: 0.1 });
     */
    toBeCloseTo(expected, options) {
        this._ensureArguments(arguments, "number");

        const margin = options?.margin ?? 1;
        return this._resolve(() => ({
            name: "toBeCloseTo",
            acceptedType: "number",
            predicate: (received) => $abs(expected - received) < margin,
            message: options?.message,
            onPass: () => [r`received value is[! not] close to`, this._received],
            onFail: () => [r`expected values to be close to the given value`],
            getFailedDetails: (received) => detailsFromValuesWithDiff(expected, received),
        }));
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
        this._ensureArguments(arguments);

        return this._resolve(() => ({
            name: "toBeEmpty",
            acceptedType: ["any"],
            predicate: (received) => isEmpty(received),
            message: options?.message,
            onPass: () => [this._received, r`should[! not] be empty`],
            onFail: () => [this._received, r`is[! not] empty`],
            getFailedDetails: detailsFromValues,
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
        this._ensureArguments(arguments, "number");

        return this._resolve(() => ({
            name: "toBeGreaterThan",
            acceptedType: "number",
            predicate: (received) => min < received,
            message: options?.message,
            onPass: () => [this._received, r`is[! not] strictly greater than`, min],
            onFail: () => [r`expected value[! not] to be strictly greater`],
            getFailedDetails: (received) =>
                detailsFromEntries([
                    ["Minimum:", min],
                    [null, received],
                ]),
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
        this._ensureArguments(arguments, "function");

        return this._resolve(() => ({
            name: "toBeInstanceOf",
            acceptedType: "any",
            predicate: (received) => received instanceof cls,
            message: options?.message,
            onPass: () => [this._received, r`is[! not] an instance of`, cls],
            onFail: () => [r`expected value[! not] to be an instance of the given class`],
            getFailedDetails: (received) =>
                detailsFromEntries([
                    [null, cls],
                    ["Actual parent class:", getConstructor(received).name],
                ]),
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
        this._ensureArguments(arguments, "number");

        return this._resolve(() => ({
            name: "toBeLessThan",
            acceptedType: "number",
            predicate: (received) => received < max,
            message: options?.message,
            onPass: () => [this._received, r`is[! not] strictly less than`, max],
            onFail: () => [r`expected value[! not] to be strictly less`],
            getFailedDetails: (received) =>
                detailsFromEntries([
                    ["Maximum:", max],
                    [null, received],
                ]),
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
        this._ensureArguments(arguments, "string");

        return this._resolve(() => ({
            name: "toBeOfType",
            acceptedType: "any",
            predicate: (received) => isOfType(received, type),
            message: options?.message,
            onPass: () => [this._received, r`is[! not] of type`, type],
            onFail: () => [r`expected value to be of the given type`],
            getFailedDetails: (received) =>
                detailsFromEntries([
                    ["Expected type:", type],
                    ["Received value:", received],
                ]),
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
        this._ensureArguments(arguments, "number", "number");

        if (min > max) {
            [min, max] = [max, min];
        }
        if (min === max) {
            throw new HootError(`min and max cannot be equal (did you mean to use \`toBe()\`?)`);
        }

        return this._resolve(() => ({
            name: "toBeWithin",
            acceptedType: "number",
            predicate: (received) => min <= received && received <= max,
            message: options?.message,
            onPass: () => [this._received, r`is[! not] between`, min, r`and`, max],
            onFail: () => [r`expected value[! not] to be between given range`],
            getFailedDetails: (received) => detailsFromValues(`${min} - ${max}`, received),
        }));
    }

    /**
     * Expects the received value to be *deeply* equal to the `expected` value.
     *
     * @param {R} expected
     * @param {ExpectOptions & DeepEqualOptions} [options]
     * @example
     *  expect(["foo"]).toEqual(["foo"]);
     * @example
     *  expect({ foo: 1 }).toEqual({ foo: 1 });
     */
    toEqual(expected, options) {
        this._ensureArguments(arguments, "any");

        return this._resolve(() => ({
            name: "toEqual",
            acceptedType: "any",
            predicate: (received) => deepEqual(expected, received, options),
            message: options?.message,
            onPass: () => [r`received value is[! not] deeply equal to`, this._received],
            onFail: () => [r`expected values to[! not] be deeply equal`],
            getFailedDetails: (received) => detailsFromValuesWithDiff(expected, received),
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
        this._ensureArguments(arguments, "integer");

        return this._resolve(() => {
            const receivedLength = getLength(this._received);
            return {
                name: "toHaveLength",
                acceptedType: ["string", "array", "object"],
                predicate: () => strictEqual(receivedLength, length),
                message: options?.message,
                onPass: () => [this._received, r`has[! not] a length of`, length],
                onFail: () => [r`expected value[! not] to have the given length`],
                getFailedDetails: () =>
                    detailsFromEntries([
                        ["Expected length:", length],
                        [null, receivedLength],
                    ]),
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
        this._ensureArguments(arguments, "any");

        return this._resolve(() => ({
            name: "toInclude",
            acceptedType: ["string", "any[]", "object"],
            predicate: (received) => includes(received, item),
            message: options?.message,
            onPass: () => [this._received, r`[includes!does not include]`, item],
            onFail: () => [r`expected object[! not] to include the given item`],
            getFailedDetails: (received) =>
                detailsFromEntries([
                    ["Item:", item],
                    ["Object:", received],
                ]),
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
        this._ensureArguments(arguments, "any");

        return this._resolve(() => ({
            name: "toMatch",
            acceptedType: "any",
            predicate: (received) => match(received, matcher),
            message: options?.message,
            onPass: () => [this._received, r`[matches!does not match]`, matcher],
            onFail: () => [r`expected value[! not] to match the given matcher`],
            getFailedDetails: (received) =>
                detailsFromEntries([
                    ["Matcher:", matcher],
                    [null, received],
                ]),
        }));
    }

    /**
     * Expects the received value to include the given object shape.
     *
     * A *partial* deep equality is performed, meaning that only the keys included
     * in `partialObject` will be checked on the received value.
     *
     * This partial matching is only applied to non-iterable object, and not to
     * arrays and other iterables; these are checked for deep equality. Although,
     * non-iterable objects contained in iterables will be partially checked again.
     *
     * @param {Partial<R>} partialObject
     * @param {ExpectOptions} [options]
     * @example
     *  // Partial equality can be performed on nested objects
     *  expect({
     *      company: {
     *          name: "Odoo",
     *          location: "Belgium",
     *      },
     *      employees: new Set([
     *          {
     *              name: "Julien",
     *              age: 28,
     *          },
     *      ]),
     *  }).toMatchObject({
     *      company: { name: "Odoo" }
     *      employees: new Set([{ age: 28 }]),
     *  });
     * @example
     *  // Iterables should have an (deep) equal content
     *  expect({ list: [1, 2, 3], other: "property" }).not.toMatchObject({ list: [1, 2] });
     *  // ... as expected in the following assertion
     *  expect({ list: [1, 2, 3], other: "property" }).toMatchObject({ list: [1, 2, 3] });
     */
    toMatchObject(partialObject, options) {
        this._ensureArguments(arguments, "object");

        return this._resolve(() => ({
            name: "toMatchObject",
            acceptedType: ["object"],
            predicate: (received) => deepEqual(received, partialObject, { partial: true }),
            message: options?.message,
            onPass: () => [this._received, r`[matches!does not match] object`, partialObject],
            onFail: () => [r`expected object[! not] to match the given shape`],
            getFailedDetails: (received) =>
                detailsFromEntries([
                    ["Partial object:", partialObject],
                    ["Object:", received],
                ]),
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
        this._ensureArguments(arguments, "any");

        return this._resolve(() => {
            const isAsync = this._flags & (FLAGS.rejects | FLAGS.resolves);
            let returnValue;
            if (isAsync) {
                returnValue = this._received;
            } else {
                try {
                    returnValue = this._received();
                } catch (error) {
                    returnValue = error;
                }
            }
            return {
                name: "toThrow",
                acceptedType: ["function", "error"],
                predicate: () => match(returnValue, matcher),
                message: options?.message,
                onPass: () => [
                    this._received,
                    r`did[! not] ${isAsync ? "reject" : "throw"} a matching value`,
                ],
                onFail: () => [
                    this._received,
                    r`${
                        isAsync ? "rejected" : "threw"
                    } a value that did not match the given matcher`,
                ],
                getFailedDetails: () =>
                    detailsFromEntries([
                        ["Matcher:", matcher],
                        [null, returnValue],
                    ]),
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
        this._ensureArguments(arguments);

        const prop = options?.indeterminate ? "indeterminate" : "checked";
        const pseudo = ":" + prop;

        return this._resolve(() => ({
            name: "toBeChecked",
            acceptedType: ["string", "node", "node[]"],
            mapElements: (el) => el.matches?.(pseudo),
            predicate: (checked) => !!checked,
            message: options?.message,
            onPass: () => [this._received, r`[is%are][! not] ${prop}`],
            onFail: () => [r`expected`, this._received, r`[! not] to be ${prop}`],
            getFailedDetails: (checked) => detailsFromEntries([["Checked:", checked]]),
        }));
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
        this._ensureArguments(arguments);

        return this._resolve(() => ({
            name: "toBeDisplayed",
            acceptedType: ["string", "node", "node[]"],
            mapElements: isNodeDisplayed,
            predicate: (displayed) => !!displayed,
            message: options?.message,
            onPass: () => [this._received, r`[is%are][! not] displayed`],
            onFail: () => [r`expected`, this._received, r`[! not] to be displayed`],
            getFailedDetails: (displayed) => detailsFromEntries([["Displayed:", displayed]]),
        }));
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
        this._ensureArguments(arguments);

        return this._resolve(() => ({
            name: "toBeEnabled",
            acceptedType: ["string", "node", "node[]"],
            mapElements: (el) => el.matches?.(":enabled"),
            predicate: (enabled) => !!enabled,
            message: options?.message,
            onPass: () => [this._received, r`[is%are] [enabled!disabled]`],
            onFail: () => [r`expected`, this._received, r`to be [enabled!disabled]`],
            getFailedDetails: (enabled) => detailsFromEntries([["Enabled:", enabled]]),
        }));
    }

    /**
     * Expects the received {@link Target} to be focused in its owner document.
     *
     * @param {ExpectOptions} [options]
     */
    toBeFocused(options) {
        this._ensureArguments(arguments);

        return this._resolve(() => ({
            name: "toBeFocused",
            acceptedType: ["string", "node", "node[]"],
            mapElements: (el) => getActiveElement(el),
            predicate: (activeEl, el) => strictEqual(el, activeEl),
            message: options?.message,
            onPass: () => [this._received, r`[is%are][! not] focused`],
            onFail: () => [this._received, r`should[! not] be focused`],
            getFailedDetails: (focused) => detailsFromEntries([["Focused:", focused]]),
        }));
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
        this._ensureArguments(arguments);

        return this._resolve(() => ({
            name: "toBeVisible",
            acceptedType: ["string", "node", "node[]"],
            mapElements: isNodeVisible,
            predicate: (visible) => !!visible,
            message: options?.message,
            onPass: () => [this._received, r`[is%are] [visible!hidden]`],
            onFail: () => [r`expected`, this._received, r`to be [visible!hidden]`],
            getFailedDetails: (visible) => detailsFromEntries([["Visible:", visible]]),
        }));
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
        this._ensureArguments(arguments, "string", ["string", "number", "regex", null]);

        const expectsValue = !isNil(value);

        return this._resolve(() => ({
            name: "toHaveAttribute",
            acceptedType: ["string", "node", "node[]"],
            mapElements: (el) => getNodeAttribute(el, attribute),
            predicate: (elAttr, el) =>
                expectsValue ? valueMatches(elAttr, value) : el.hasAttribute(attribute),
            message: options?.message,
            onPass: () => [
                r`attribute`,
                attribute,
                r`on`,
                this._received,
                ...(expectsValue ? [r`[matches!does not match]`, value] : [r`is[! not] set`]),
            ],
            onFail: () => [
                this._received,
                r`[does%do] not have the correct attribute${expectsValue ? " value" : ""}`,
            ],
            getFailedDetails: (elAttr) =>
                detailsFromValuesWithDiff(expectsValue ? value : attribute, elAttr),
        }));
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
        this._ensureArguments(arguments, ["string", "string[]"]);

        const rawClassNames = ensureArray(className);
        const classNames = rawClassNames.flatMap((cls) => cls.trim().split(R_WHITE_SPACE));

        return this._resolve(() => ({
            name: "toHaveClass",
            acceptedType: ["string", "node", "node[]"],
            mapElements: (el) => [...el.classList].sort(),
            predicate: (classes) =>
                options?.exact
                    ? deepEqual(classNames, classes, { ignoreOrder: true })
                    : classNames.every((cls) => classes.includes(cls)),
            message: options?.message,
            onPass: () => [
                this._received,
                r`[[has%have]![does%do] not have] class${classNames.length === 1 ? "" : "es"}`,
                ...listJoin(classNames, ",", "and"),
            ],
            onFail: () => [
                r`expected`,
                this._received,
                r`[to have all!not to have any] of the given class names`,
            ],
            getFailedDetails: (classes) =>
                detailsFromValues(classNames.join(" "), classes.join(" ")),
        }));
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
        this._ensureArguments(arguments, ["integer", null]);

        const anyAmount = isNil(amount);
        return this._resolve(() => {
            const elMap = new ElementMap(this._received);
            return {
                name: "toHaveCount",
                acceptedType: ["string", "node", "node[]"],
                predicate: () => (anyAmount ? elMap.size > 0 : strictEqual(elMap.size, amount)),
                message: options?.message,
                onPass: () => [r`found`, elMap],
                onFail: () => [
                    r`found`,
                    elMap,
                    ...(anyAmount ? [r`and expected [any amount!none]`] : []),
                ],
                getFailedDetails: () => [
                    ...detailsFromValues(
                        anyAmount ? (this._flags & FLAGS.not ? S_NONE : S_ANY) : amount,
                        elMap.size
                    ),
                    Markup.text("Elements:", [...elMap.keys()]),
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
        this._ensureArguments(arguments, ["string", "regex"]);

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
        this._ensureArguments(arguments, ["string", "regex"]);

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
        this._ensureArguments(arguments, "string", "any");

        const expectsValue = !isNil(value);
        return this._resolve(() => ({
            name: "toHaveProperty",
            acceptedType: ["string", "node", "node[]"],
            mapElements: (el) => el[property],
            predicate: (elProp, el) =>
                expectsValue ? valueMatches(elProp, value) : property in el,
            message: options?.message,
            onPass: () => [
                r`property`,
                property,
                r`on`,
                this._received,
                ...(expectsValue ? [r`[matches!does not match]`, value] : [r`is[! not] set`]),
            ],
            onFail: () => [
                this._received,
                r`[does%do] not have the correct property${expectsValue ? " value" : ""}`,
            ],
            getFailedDetails: (elProp) =>
                detailsFromValuesWithDiff(expectsValue ? value : property, elProp),
        }));
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
        this._ensureArguments(arguments, ["object", "string", "node", "node[]"]);

        let refRect;
        if (typeof rect === "string" || isNode(rect)) {
            refRect = { ...queryRect(rect, options) };
        } else {
            refRect = rect;
        }

        const entries = $entries(refRect);

        return this._resolve(() => ({
            name: "toHaveRect",
            acceptedType: ["string", "node", "node[]"],
            mapElements: (el) => getNodeRect(el, options),
            predicate: (elRect) => entries.every(([key, val]) => strictEqual(elRect[key], val)),
            message: options?.message,
            onPass: () => [this._received, r`[has%have] the expected DOM rect of`, rect],
            onFail: () => [r`expected`, this._received, r`to have the given DOM rect`],
            getFailedDetails: (elRect) => detailsFromValuesWithDiff(rect, elRect),
        }));
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
        this._ensureArguments(arguments, ["string", "object"]);

        const styleDef = parseInlineStyle(style, S_ANY);
        const styleKeys = $keys(styleDef);

        return this._resolve(() => ({
            name: "toHaveStyle",
            acceptedType: ["string", "node", "node[]"],
            mapElements: (el) =>
                options?.inline
                    ? parseInlineStyle(el.getAttribute("style"))
                    : getStyleValues(el, $keys(styleDef)),
            predicate: (elStyle) =>
                styleKeys.every((key) => valueMatches(elStyle[key], styleDef[key])) &&
                (!options?.exact || deepEqual(styleKeys, $keys(elStyle), { ignoreOrder: true })),
            message: options?.message,
            onPass: () => [
                this._received,
                r`[has%have] the expected style values for`,
                ...listJoin($keys(styleDef), ",", "and"),
            ],
            onFail: () => [
                r`expected`,
                this._received,
                r`[to have all!not to have any] of the given style properties`,
            ],
            getFailedDetails: (elStyle) => detailsFromValuesWithDiff(styleDef, elStyle),
        }));
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
        this._ensureArguments(arguments, ["string", "regex", null]);

        const expectsText = !isNil(text);

        return this._resolve(() => ({
            name: "toHaveText",
            acceptedType: ["string", "node", "node[]"],
            mapElements: (el) => getNodeText(el, options),
            predicate: (elText) => (expectsText ? valueMatches(elText, text) : elText.length > 0),
            message: options?.message,
            onPass: () => [this._received, r`[[has%have]![does%do] not have] text`, text],
            onFail: () => [r`expected`, this._received, r`[! not] to have the given text`],
            getFailedDetails: (elText) => detailsFromValuesWithDiff(text, elText),
        }));
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
        this._ensureArguments(arguments, [
            "string",
            "string[]",
            "number",
            "object[]",
            "regex",
            null,
        ]);

        const expectsValue = !isNil(value);

        return this._resolve(() => ({
            name: "toHaveValue",
            acceptedType: ["string", "node", "node[]"],
            mapElements: (el) => getNodeValue(el),
            predicate: (elValue, el) => {
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
            },
            message: options?.message,
            onPass: () => [this._received, r`[[has%have]![does%do] not have] value`, value],
            onFail: () => [r`expected`, this._received, r`[! not] to have the given value`],
            getFailedDetails: (elValue) => detailsFromValuesWithDiff(value, elValue),
        }));
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
     * Validates the given `arguments` object, with an implicitly added `options`
     * validator at the end (optional).
     *
     * Flags are then modified based on these options, and the current stack is
     * saved for error reporting.
     *
     * @private
     * @param {any[]} argumentsObject
     * @param {...(ArgumentType | ArgumentType[])} argumentsDefs
     */
    _ensureArguments(argumentsObject, ...argumentsDefs) {
        if (!unconsumedMatchers.has(this)) {
            throw new HootError(`cannot use multiple matchers on the same \`expect()\` call`);
        }
        unconsumedMatchers.delete(this);

        const args = [...argumentsObject];
        ensureArguments(args, ...argumentsDefs, ["object", null]);

        const options = args[argumentsDefs.length] || {};
        for (const flag in FLAGS) {
            if (flag in options) {
                if (options[flag]) {
                    this._flags |= FLAGS[flag];
                } else {
                    this._flags &= ~FLAGS[flag];
                }
            }
        }

        if (!(this._flags & FLAGS.headless)) {
            currentStack = getStack(1);
        }
    }

    /**
     * @private
     * @param {() => MatcherSpecifications<R, A>} specCallback
     * @returns {Async extends true ? Promise<boolean> : boolean}
     */
    _resolve(specCallback) {
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
                        return false;
                    } else {
                        this._received = result;
                        return this._resolveFinalResult(specCallback);
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
                        return false;
                    } else {
                        this._received = reason;
                        return this._resolveFinalResult(specCallback);
                    }
                }
            );
        } else {
            return this._resolveFinalResult(specCallback);
        }
    }

    /**
     * @private
     * @param {() => MatcherSpecifications<R, A>} specCallback
     * @returns {boolean}
     */
    _resolveFinalResult(specCallback) {
        let {
            acceptedType,
            getFailedDetails,
            mapElements,
            message,
            name,
            onFail,
            onPass,
            predicate,
        } = specCallback();

        const types = ensureArray(acceptedType);
        if (!types.some((type) => isOfType(this._received, type))) {
            throw new TypeError(
                `expected received value to be of type ${listJoin(types, ",", "or").join(
                    " "
                )}, got ${formatHumanReadable(this._received)}`
            );
        }

        if (mapElements) {
            this._received = new ElementMap(this._received, mapElements);
        }
        function passPredicate(...args) {
            return not ? !predicate(...args) : predicate(...args);
        }
        const not = this._flags & FLAGS.not;
        let pass;
        if (mapElements) {
            pass = this._received.every(passPredicate);
            if (!pass && !this._received.size) {
                onFail = [r`expected at least`, 1, r`element and got`, this._received];
            }
        } else {
            pass = passPredicate(this._received);
        }

        if (!(this._flags & FLAGS.silent)) {
            const assertion = {
                flags: this._flags,
                label: name,
                message,
                pass,
                reportMessage: pass ? onPass : onFail,
            };
            if (!pass) {
                if (mapElements) {
                    assertion.failedDetails = this._received.mapFailedDetails(
                        getFailedDetails,
                        passPredicate
                    );
                } else {
                    assertion.failedDetails = getFailedDetails(this._received);
                }
                assertion.stack = currentStack;
            }
            this._result.registerEvent("assertion", assertion);
        }

        return pass;
    }

    /**
     * @private
     * @param {"toHaveInnerHTML" | "toHaveOuterHTML"} name
     * @param {"innerHTML" | "outerHTML"} property
     * @param {string | RegExp} expected
     * @param {ExpectOptions & FormatXmlOptions} [options]
     */
    _toHaveHTML(name, property, expected, options) {
        options = { type: "html", ...options };
        if (!(expected instanceof RegExp)) {
            expected = formatXml(expected, options);
        }

        return this._resolve(() => ({
            name,
            acceptedType: ["string", "node", "node[]"],
            mapElements: (el) =>
                // Force HTML type here as it will be returned by outer/inner HTML
                formatXml(el[property], { ...options, type: "html" }),
            predicate: (elHtml) => valueMatches(elHtml, expected),
            message: options?.message,
            onPass: () => [property, r`of`, this._received, r`is[! not] equal to expected value`],
            onFail: () => [
                r`expected`,
                property,
                r`of`,
                this._received,
                r`to match the given value`,
            ],
            getFailedDetails: (val) => detailsFromValuesWithDiff(expected, val),
        }));
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
    /** @type {string | null | undefined} */
    additionalMessage;
    type = CASE_EVENT_TYPES.assertion.value;

    /**
     * @param {number} number
     * @param {Partial<Assertion & {
     *  message: AssertionMessage,
     *  reportMessage: AssertionReportMessage,
     * }>} values
     */
    constructor(number, values) {
        super();

        this.label = values.label;
        this.flags = values.flags || 0;
        this.pass = values.pass || false;
        this.number = number;

        if (!this.pass) {
            /** @type {[any, any][] | null} */
            this.failedDetails = Markup.resolveDetails(values.failedDetails || []);
            /** @type {string} */
            this.stack = values.stack;
        }

        let { message, reportMessage } = values;

        // Message
        if (typeof message === "function") {
            this.additionalMessage = message();
        } else {
            this.additionalMessage = message;
        }

        // Reporting message
        if (typeof reportMessage === "function") {
            reportMessage = reportMessage(this.pass, r);
        }
        const parts =
            $isArray(reportMessage) && !isLabel(reportMessage)
                ? reportMessage
                : [makeLabel(reportMessage, null)];
        const plural = parts.some((p) => p instanceof ElementMap && p.size !== 1);
        const not = this.flags & FLAGS.not;
        for (const part of parts) {
            if (part instanceof ElementMap) {
                const subject = part.size === 1 ? "element" : "elements";
                if (part.selector) {
                    this.message.push(
                        makeLabelOrString(part.size),
                        `${subject} matching`,
                        makeLabelOrString(part.selector)
                    );
                } else {
                    const elements = part.keys();
                    this.message.push(
                        subject,
                        makeLabelOrString(part.size === 1 ? elements.next().value : [...elements])
                    );
                }
            } else if (isLabel(part)) {
                if (part[1] === "icon") {
                    this.message.push(part);
                } else {
                    this.message.push(
                        makeLabelOrString(formatMessage(part[0], plural, not), part[1])
                    );
                }
            } else if (typeof part === "string") {
                this.message.push(makeLabelOrString(formatMessage(part, plural, not)));
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
