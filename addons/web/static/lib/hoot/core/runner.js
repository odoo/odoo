/** @odoo-module */

import { on, setFrameRate } from "@odoo/hoot-dom";
import { cleanupDOM, defineRootNode } from "@odoo/hoot-dom-helpers-dom";
import { cleanupEvents, enableEventLogs } from "@odoo/hoot-dom-helpers-events";
import { cleanupTime, setupTime } from "@odoo/hoot-dom-helpers-time";
import { markRaw, reactive, toRaw } from "@odoo/owl";

const __nativeTimers = globalThis.odoo?.__nativeTimers ?? globalThis;
const { setTimeout: nativeSetTimeout, clearTimeout: nativeClearTimeout } =
    __nativeTimers;
import * as _hootDom from "@odoo/hoot-dom";
import { exposeHelpers, isInstanceOf, isIterable } from "@odoo/hoot-dom-utils";

import {
    batch,
    Callbacks,
    CASE_EVENT_TYPES,
    createReporting,
    deepEqual,
    ensureArray,
    ensureError,
    formatHumanReadable,
    formatTechnical,
    formatTime,
    HootError,
    INCLUDE_LEVEL,
    isLabel,
    Markup,
    normalize,
    parseQuery,
    STORAGE,
    storageGet,
    storageSet,
    stringify,
} from "../hoot_utils.js";
import { cleanupAnimations } from "../mock/animation.js";
import * as _animation from "../mock/animation.js";
import { cleanupDate } from "../mock/date.js";
import * as _date from "../mock/date.js";
import { internalRandom } from "../mock/math.js";
import * as _math from "../mock/math.js";
import { cleanupNavigator } from "../mock/navigator.js";
import * as _navigator from "../mock/navigator.js";
import { cleanupNetwork, throttleNetwork } from "../mock/network.js";
import * as _network from "../mock/network.js";
import * as _notification from "../mock/notification.js";
import {
    cleanupWindow,
    getViewPortHeight,
    getViewPortWidth,
    mockTouch,
    setupWindow,
} from "../mock/window.js";
import * as _window from "../mock/window.js";
import { DEFAULT_CONFIG, FILTER_KEYS } from "./config.js";
import { makeExpect } from "./expect.js";
import { destroy, makeFixtureManager } from "./fixture.js";
import { logger } from "./logger.js";
import { Suite, suiteError } from "./suite.js";
import { getTags, getTagSimilarities, Tag } from "./tag.js";
import { Test, testError } from "./test.js";
import { createUrlFromId, EXCLUDE_PREFIX, setParams } from "./url.js";

const { isPrevented, mockPreventDefault } = _window;

/**
 * @typedef {{
 *  readonly config: (config: JobConfig) => CurrentConfigurators;
 *  readonly debug: () => CurrentConfigurators;
 *  readonly multi: (count: number) => CurrentConfigurators;
 *  readonly only: () => CurrentConfigurators;
 *  readonly skip: () => CurrentConfigurators;
 *  readonly tags: (...tags: string[]) => CurrentConfigurators;
 *  readonly timeout: (ms: number) => CurrentConfigurators;
 *  readonly todo: () => CurrentConfigurators;
 * }} CurrentConfigurators
 * @typedef {{
 *  count: number;
 *  message: string;
 *  name: string;
 * }} GlobalIssueReport
 * @typedef {Suite | Test} Job
 * @typedef {import("./job").JobConfig} JobConfig
 * @typedef {{
 *  icon?: string;
 *  label: string;
 *  platform?: import("../mock/navigator").Platform;
 *  size?: [number, number];
 *  tags?: string[];
 *  touch?: boolean;
 * }} Preset
 * @typedef {import("./config").SearchFilter} SearchFilter
 */

/**
 * @template T
 * @typedef {(payload: T) => MaybePromise<any>} Callback
 */

/**
 * @template {unknown[]} T
 * @typedef {import("../hoot_utils").DropFirst} DropFirst
 */

/**
 * @template T
 * @typedef {T | PromiseLike<T>} MaybePromise
 */

const {
    console: { error: $error },
    EventTarget,
    Map,
    Math: { abs: $abs, floor: $floor },
    Number: { parseFloat: $parseFloat },
    Object: {
        assign: $assign,
        defineProperty: $defineProperty,
        entries: $entries,
        freeze: $freeze,
        fromEntries: $fromEntries,
        keys: $keys,
        values: $values,
    },
    performance,
    Promise,
    removeEventListener,
    Set,
    window,
} = globalThis;
/** @type {Performance["now"]} */
const $now = performance.now.bind(performance);

/** @param {Job[]} jobs */
function filterReady(jobs) {
    return jobs.filter((job) => {
        if (job instanceof Suite) {
            job.setCurrentJobs(filterReady(job.currentJobs));
            return job.currentJobs.length;
        }
        return job.run;
    });
}

/** @param {Record<string, number>} values */
function formatIncludes(values) {
    return $entries(values)
        .filter(([, value]) => $abs(value) === INCLUDE_LEVEL.url)
        .map(([id, value]) => (value >= 0 ? id : `${EXCLUDE_PREFIX}${id}`));
}

/** @param {import("./expect").Assertion[]} assertions */
function formatAssertions(assertions) {
    const lines = [];
    for (const {
        additionalMessage,
        failedDetails,
        label,
        message,
        number,
    } of assertions) {
        const formattedMessage = message.map((part) =>
            isLabel(part) ? part[0] : String(part),
        );
        if (additionalMessage) {
            formattedMessage.push(`(${additionalMessage})`);
        }
        lines.push(`\n${number}. [${label}] ${formattedMessage.join(" ")}`);
        if (failedDetails) {
            for (const detail of failedDetails) {
                if (Markup.isMarkup(detail, "group")) {
                    lines.push(
                        `${number}.${detail.groupIndex}. (${formatHumanReadable(detail.content)})`,
                    );
                    continue;
                }
                if (!detail || typeof detail[Symbol.iterator] !== "function") {
                    lines.push(`> ${String(detail)}`);
                    continue;
                }
                let [key, value] = detail;
                if (Markup.isMarkup(key)) {
                    key = key.content;
                }
                if (Markup.isMarkup(value)) {
                    if (value.type === "technical") {
                        continue;
                    }
                    value = value.content;
                }
                lines.push(`> ${key} ${formatTechnical(value)}`);
            }
        }
    }
    return lines;
}

/**
 * @template T
 * @param {T[]} array
 */
function shuffle(array) {
    const copy = [...array];
    let randIndex;
    for (let i = 0; i < copy.length; i++) {
        randIndex = $floor(internalRandom() * copy.length);
        [copy[i], copy[randIndex]] = [copy[randIndex], copy[i]];
    }
    return copy;
}

/**
 * @param {Test} test
 * @param {boolean} shouldSuppress
 */
function handleConsoleIssues(test, shouldSuppress) {
    if (shouldSuppress && test.config.todo) {
        return logger.setIssueLevel("suppressed");
    } else {
        const cleanups = [];
        if (isInstanceOf(globalThis.console, EventTarget)) {
            cleanups.push(
                on(globalThis.console, "error", () => test.logs.error++),
                on(globalThis.console, "warn", () => test.logs.warn++),
            );
        }

        return function offConsoleEvents() {
            while (cleanups.length) {
                cleanups.pop()();
            }
        };
    }
}

/** @param {Event} ev */
function warnUserEvent(ev) {
    if (!ev.isTrusted) {
        return;
    }

    logger.global.warn(
        `User event detected: "${ev.type}"\n\n`,
        `This kind of interaction can interfere with the current test and should be avoided.`,
    );

    removeEventListener(ev.type, warnUserEvent);
}

const WARNINGS = {
    viewport: "Viewport size does not match the expected size for the current preset",
    tagNames:
        "The following tag names are very similar to each other and may be confusing for other developers:",
};
const RESIZE_OBSERVER_MESSAGE =
    "ResizeObserver loop completed with undelivered notifications";
const handledErrors = new WeakSet();
/** @type {string | null} */
let lastPresetWarn = null;

export class Runner {
    static URL_SPEC = 1;
    static TAG_SPEC = 2;
    static PRESET_SPEC = 3;

    aborted = false;
    /** @type {boolean | Test | Suite} */
    debug = false;
    dry = false;
    /** @type {ReturnType<typeof makeExpect>[0]} */
    expect;
    /** @type {ReturnType<typeof makeExpect>[1]} */
    expectHooks;
    headless = false;
    /** @type {Set<Suite>} */
    emptiedWhileDeclaring = new Set();
    /** @type {Record<string, Preset>} */
    presets = {
        [""]: { label: "No preset" },
    };
    reporting = createReporting();
    /** @type {Suite[]} */
    rootSuites = [];
    state = {
        /** @type {Test | null} */
        currentTest: null,
        /** @type {Set<Test>} */
        done: new Set(),
        failedIds: new Set(storageGet(STORAGE.failed)),
        /** @type {Record<string, GlobalIssueReport>} */
        globalErrors: {},
        /** @type {Record<string, GlobalIssueReport>} */
        globalWarnings: {},
        /** @type {Record<"id" | "tag", Record<string, number>>} */
        includeSpecs: {
            id: {},
            tag: {},
        },
        /** @type {"ready" | "running" | "done"} */
        status: "ready",
        /** @type {Suite[]} */
        suites: [],
        /** @type {Test[]} */
        tests: [],
    };
    /** @type {Map<string, Suite>} */
    suites = new Map();
    /** @type {Suite[]} */
    suiteStack = [];
    /** @type {Map<string, Tag>} */
    tags = new Map();
    /** @type {Map<string, Test>} */
    tests = new Map();
    /** @type {import("../hoot_utils").QueryPart[]} */
    queryExclude = [];
    /** @type {import("../hoot_utils").QueryPart[]} */
    queryInclude = [];
    totalTime = "n/a";

    /** @type {boolean} */
    get hasFilter() {
        for (const includeValues of $values(this.state.includeSpecs)) {
            if ($keys(includeValues).length > 0) {
                return true;
            }
        }
        return false;
    }

    /** @type {boolean} */
    get hasRemovableFilter() {
        return this._removableFilterCount > 0;
    }

    _callbacks = new Callbacks();
    /** @type {Job[]} */
    _currentJobs = [];
    _failed = 0;
    _includeFilterCount = 0;
    /** @type {(() => MaybePromise<void>)[]} */
    _missedCallbacks = [];
    _populateState = false;
    _prepared = false;
    /** @type {() => void} */
    _pushPendingTest = () => {};
    /** @type {(test: Test) => void} */
    _pushTest = () => {};
    _removableFilterCount = 0;
    _started = false;
    _startTime = 0;

    /** @type {null | ((value?: any) => any)} */
    _resolveCurrent = null;

    /** @param {typeof DEFAULT_CONFIG} [config] */
    constructor(config) {
        this.describe = this._addConfigurators(this.addSuite, () =>
            this.suiteStack.at(-1),
        );
        this.fixture = makeFixtureManager(this);
        this.test = this._addConfigurators(this.addTest, false);

        this.initialConfig = { ...DEFAULT_CONFIG, ...config };
        this.headless = this.initialConfig.headless;
        if (this.headless) {
            this.config = { ...this.initialConfig };
        } else {
            this.presets = reactive(this.presets);
            this.state = reactive(this.state);
            this.config = reactive({ ...this.initialConfig }, () => {
                setParams(
                    $fromEntries(
                        $entries(this.config).map(([key, value]) => [
                            key,
                            deepEqual(value, DEFAULT_CONFIG[key]) ? null : value,
                        ]),
                    ),
                );
            });

            [this._pushTest, this._pushPendingTest] = batch((test) =>
                this.state.done.add(test),
            );
        }

        [this.expect, this.expectHooks] = makeExpect({ headless: this.headless });

        for (const key in this.config) {
            this.config[key];
        }

        this.debug = Boolean(this.config.debugTest);

        if (this.config.filter) {
            for (const queryPart of parseQuery(this.config.filter)) {
                if (queryPart.exclude) {
                    this.queryExclude.push(queryPart);
                } else {
                    this.queryInclude.push(queryPart);
                }
            }
            this._filterCount += this.queryInclude.length;
            this._includeFilterCount += this.queryInclude.length;
        }

        if (this.config.id?.length) {
            this._include(
                this.state.includeSpecs.id,
                this.config.id,
                INCLUDE_LEVEL.url,
            );
        }

        if (this.config.tag?.length) {
            this._include(
                this.state.includeSpecs.tag,
                this.config.tag,
                INCLUDE_LEVEL.url,
            );
        }

        if (this.config.networkDelay) {
            const values = this.config.networkDelay
                .split("-")
                .map((val) => $parseFloat(val) || 0);
            throttleNetwork(...values);
        }

        if (this.config.random) {
            internalRandom.seed = this.config.random;
        }

        on(window, "error", this._handleError.bind(this));
        on(window, "unhandledrejection", this._handleError.bind(this));
    }

    /**
     * @param {JobConfig} config
     * @param {string | Iterable<string>} name
     * @param {(() => void) | string} fn
     */
    addSuite(config, name, fn) {
        if (!name) {
            throw new HootError(`a suite name must not be empty, got ${name}`, {
                level: "critical",
            });
        }
        const names = ensureArray(name).flatMap((n) =>
            normalize(n).split("/").filter(Boolean),
        );
        const [suiteName, ...otherNames] = names;
        if (names.length > 1) {
            let targetSuite;
            this.addSuite([], suiteName, () => {
                targetSuite = this.addSuite(config, otherNames, fn);
            });
            return targetSuite;
        }
        const parentSuite = this.suiteStack.at(-1);
        if (typeof fn !== "function") {
            throw suiteError(
                { name: suiteName, parent: parentSuite },
                `expected second argument to be a function and got ${String(fn)}`,
            );
        }
        if (this.state.status === "running") {
            throw suiteError(
                { name: suiteName, parent: parentSuite },
                `cannot add a suite after the test runner started`,
            );
        }
        let suite = markRaw(new Suite(parentSuite, suiteName, config));
        const originalSuite = this.suites.get(suite.id);
        if (originalSuite) {
            suite = originalSuite;
        } else {
            this.suites.set(suite.id, suite);
            if (parentSuite) {
                parentSuite.addJob(suite);
                suite.reporting = createReporting(parentSuite.reporting);
            } else {
                this.rootSuites.push(suite);
                suite.reporting = createReporting(this.reporting);
            }
        }
        this.suiteStack.push(suite);

        this._applyTagModifiers(suite);
        if (suite.config.skip && this.headless) {
            return this._erase(suite, true);
        }

        let error, result;
        if (!this._prepared || suite.currentJobs.length) {
            try {
                result = fn();
            } catch (err) {
                if (err instanceof HootError) {
                    throw err;
                } else {
                    error = err;
                }
            }
        }

        this.suiteStack.pop();
        if (error) {
            throw suiteError(suite, error);
        } else if (result !== undefined) {
            throw suiteError(suite, `the suite function cannot return a value`);
        }
        if (this.emptiedWhileDeclaring.delete(suite) && !suite.jobs.length) {
            this._erase(suite);
        }

        return suite;
    }

    /**
     * @param {JobConfig} config
     * @param {string} name
     * @param {() => void | PromiseLike<void>} fn
     */
    addTest(config, name, fn) {
        if (!name) {
            throw new HootError(`a test name must not be empty, got ${name}`, {
                level: "critical",
            });
        }
        const parentSuite = this.suiteStack.at(-1);
        if (!parentSuite) {
            throw testError(
                { name, parent: null },
                `cannot register a test outside of a suite.`,
            );
        }
        if (typeof fn !== "function") {
            throw testError(
                { name, parent: parentSuite },
                `expected second argument to be a function and got ${String(fn)}`,
            );
        }
        if (this.state.status === "running") {
            throw testError(
                { name, parent: parentSuite },
                `cannot add a test after the test runner started.`,
            );
        }
        const runFn = this.dry ? null : fn;
        let test = markRaw(new Test(parentSuite, name, config));
        const originalTest = this.tests.get(test.id);
        if (originalTest && !originalTest.isMinimized) {
            if (this.dry || originalTest.run) {
                throw testError(
                    test,
                    `a test with that name already exists in the suite ${stringify(
                        parentSuite.name,
                    )}`,
                );
            }
            test = originalTest;
        } else {
            if (!this.dry && this._prepared) {
                return null;
            }
            parentSuite.addJob(test);
            this.tests.set(test.id, test);
        }

        test.setRunFn(runFn);

        this._applyTagModifiers(test);
        if (test.config.skip && this.headless) {
            return this._erase(test, true);
        }

        return test;
    }

    /** @param {...Callback<Job>} callbacks */
    after(...callbacks) {
        const { suite, test } = this.getCurrent();
        if (test) {
            for (const callback of callbacks) {
                suite.callbacks.add("after-test", callback, true);
            }
        } else {
            const callbackRegistry = suite ? suite.callbacks : this._callbacks;
            for (const callback of callbacks) {
                callbackRegistry.add("after-suite", callback);
            }
        }
    }

    /** @param {...Callback<never>} callbacks */
    afterAll(...callbacks) {
        for (const callback of callbacks) {
            this._callbacks.add("after-all", callback);
        }
    }

    /** @param {...Callback<Test>} callbacks */
    afterEach(...callbacks) {
        const { suite, test } = this.getCurrent();
        if (test) {
            throw testError(test, `cannot call hook "afterEach" inside of a test`);
        }
        const callbackRegistry = suite ? suite.callbacks : this._callbacks;
        for (const callback of callbacks) {
            callbackRegistry.add("after-test", callback);
        }
    }

    /** @param {...Callback<Test>} callbacks */
    afterPostTest(...callbacks) {
        for (const callback of callbacks) {
            this._callbacks.add("after-post-test", callback);
        }
    }

    /** @param {...Callback<Job>} callbacks */
    before(...callbacks) {
        const { suite, test } = this.getCurrent();
        if (test) {
            for (const callback of callbacks) {
                suite.callbacks.add("after-test", callback(test), true);
            }
        } else {
            const callbackRegistry = suite ? suite.callbacks : this._callbacks;
            for (const callback of callbacks) {
                callbackRegistry.add("before-suite", callback);
            }
        }
    }

    /** @param {...Callback<never>} callbacks */
    beforeAll(...callbacks) {
        for (const callback of callbacks) {
            this._callbacks.add("before-all", callback);
        }
    }

    /** @param {...Callback<Test>} callbacks */
    beforeEach(...callbacks) {
        const { suite, test } = this.getCurrent();
        if (test) {
            throw testError(test, `cannot call hook "beforeEach" inside of a test`);
        }
        const callbackRegistry = suite ? suite.callbacks : this._callbacks;
        for (const callback of callbacks) {
            callbackRegistry.add("before-test", callback);
        }
    }

    checkPresetForViewPort() {
        const presetId = this.config.preset;
        const preset = this.presets[presetId];
        if (!preset.size) {
            return true;
        }
        const innerWidth = getViewPortWidth();
        const innerHeight = getViewPortHeight();
        const [width, height] = preset.size;
        if (width === innerWidth && height === innerHeight) {
            lastPresetWarn = null;
            delete this.state.globalWarnings[WARNINGS.viewport];
        } else {
            if (lastPresetWarn !== presetId) {
                this._handleGlobalWarning(WARNINGS.viewport);
                logger.global.warn(
                    WARNINGS.viewport,
                    `\n> expected:`,
                    width,
                    "x",
                    height,
                    `\n> current:`,
                    innerWidth,
                    "x",
                    innerHeight,
                    `\n\nHint: you can use the "device toolbar" in your devtools to manually set the size of your viewport`,
                );
            }
            lastPresetWarn = presetId;
            return false;
        }
        return true;
    }

    /**
     * @param {string} key
     * @param {Preset} preset
     */
    definePreset(key, preset) {
        this.presets[key] = preset;
    }

    /** @param {() => Promise<void>} callback */
    /**
     * @param {Test} test
     * @param {string[]} failReasons
     */
    _reportFailedTest(test, failReasons) {
        logger.global.error(
            [`Test ${stringify(test.fullName)} failed:`, ...failReasons].join("\n"),
        );
    }

    async dryRun(callback) {
        if (this.state.status !== "ready") {
            throw new HootError("cannot run a dry run after the test runner started", {
                level: "global",
            });
        }
        if (this._prepared) {
            throw new HootError(
                "cannot run a dry run: runner has already been prepared",
                {
                    level: "global",
                },
            );
        }

        this.dry = true;

        await callback();

        const result = this._prepareRunner();

        this.dry = false;

        return result;
    }

    /**
     * @template {(...args: any[]) => any} T
     * @param {T} fn
     * @returns {T}
     */
    exportFn(fn) {
        return fn.bind(this);
    }

    /**
     * @returns {{
     *  suite: Suite | null;
     *  test: Test | null;
     * }}
     */
    getCurrent() {
        return {
            suite: this.suiteStack.at(-1) || null,
            test: this.state.currentTest,
        };
    }

    /**
     * @param {SearchFilter} type
     * @param {string} id
     * @param {number} value
     */
    include(type, id, value) {
        this._include(this.state.includeSpecs[type], [id], value);
        this._updateConfigFromSpecs();
    }

    manualStart() {
        this._canStartDef ||= Promise.withResolvers();
        this._canStartDef.resolve(true);
    }

    /** @param {...Callback<ErrorEvent | PromiseRejectionEvent>} callbacks */
    onError(...callbacks) {
        const { suite, test } = this.getCurrent();
        const callbackRegistry = suite ? suite.callbacks : this._callbacks;
        for (const callback of callbacks) {
            callbackRegistry.add("error", callback, Boolean(test));
        }
    }

    /** @param {Partial<Record<SearchFilter, Iterable<string>>>} specs */
    simplifyUrlIds(specs) {
        if (!specs) {
            return {};
        }
        const ids = {};
        let items = 0;
        if (specs.id) {
            for (const id of ensureArray(specs.id)) {
                items++;
                ids[id] = INCLUDE_LEVEL.url;
            }
        }
        if (items > 1) {
            this._simplifyIncludeSpecs(ids);
        }
        return {
            ...specs,
            id: $keys(ids),
        };
    }

    /** @param {...Job} jobs */
    async start(...jobs) {
        jobs = jobs.filter(Boolean);
        if (!this._started) {
            this._started = true;
            this._prepareRunner();
            await this._setupStart();
        } else if (!jobs.length) {
            throw new HootError(
                "cannot start test runner: runner has already started",
                {
                    level: "global",
                },
            );
        }

        if (this.state.status === "done") {
            return false;
        }

        if (jobs.length) {
            this._currentJobs = filterReady(jobs);
        }

        if (this._canStartDef) {
            await this._canStartDef.promise;
        }

        this.state.status = "running";

        /** @type {Runner["_handleError"]} */
        const handleError = this._handleError.bind(this);

        let job = this._nextJob(jobs);
        while (job && this.state.status === "running") {
            const callbackChain = this._getCallbackChain(job);
            if (job instanceof Suite) {
                /** @type {Suite} */
                const suite = job;
                if (!suite.config.skip && suite.currentJobs.length) {
                    if (suite.currentJobIndex <= 0) {
                        this.suiteStack.push(suite);

                        suite.before();
                        await this._callbacks.call("before-suite", suite, handleError);
                        await suite.callbacks.call("before-suite", suite, handleError);
                    }
                    if (suite.currentJobIndex >= suite.currentJobs.length) {
                        this.suiteStack.pop();

                        await this._execAfterCallback(async () => {
                            await suite.callbacks.call(
                                "after-suite",
                                suite,
                                handleError,
                            );
                            await this._callbacks.call(
                                "after-suite",
                                suite,
                                handleError,
                            );
                        });
                        suite.after();

                        logger.logSuite(suite);

                        suite.runCount++;
                        if (suite.willRunAgain()) {
                            suite.reset();
                            continue;
                        } else if (this.headless) {
                            this._erase(suite);
                        } else {
                            suite.cleanup();
                        }
                    }
                } else if (this.headless) {
                    this._erase(suite);
                } else {
                    suite.minimize();
                }
                job = this._nextJob(jobs, job);
                continue;
            }

            /** @type {Test} */
            const test = job;
            if (test.config.skip) {
                this._pushTest(test);
                test.setRunFn(null);
                test.parent.reporting.add({ skipped: +1, tests: +1 });
                job = this._nextJob(jobs, job);
                continue;
            }

            const restoreConsole = handleConsoleIssues(test, !this.debug);

            this.state.currentTest = test;
            this.expectHooks.before(test);
            test.before();
            const beforeTestError = await this._raceHookTimeout(
                "before-test",
                test,
                async (onError) => {
                    for (const callbackRegistry of [...callbackChain].reverse()) {
                        await callbackRegistry.call("before-test", test, onError);
                    }
                },
            );
            if (beforeTestError) {
                handleError(beforeTestError);
            }

            let timeoutId = 0;
            let timedOut = false;

            const testPromise = beforeTestError
                ? Promise.resolve()
                : Promise.resolve(test.run());
            const timeout = $floor(test.config.timeout || this.config.timeout);
            const timeoutPromise = new Promise((resolve, reject) => {
                this._resolveCurrent = resolve;

                if (timeout && !this.debug) {
                    timeoutId = nativeSetTimeout(() => {
                        timedOut = true;
                        const msg = `test ${stringify(
                            test.name,
                        )} timed out after ${timeout} milliseconds`;
                        reject(new HootError(msg, { level: "global" }));
                    }, timeout);
                }
            }).then(() => {
                this.aborted = true;
                this.debug = false;
            });

            await Promise.race([testPromise, timeoutPromise])
                .catch((error) => {
                    if (timedOut) {
                        this.expectHooks.timeout(timeout);
                    }
                    if (handleError) {
                        return handleError(error);
                    } else {
                        throw error;
                    }
                })
                .finally(() => {
                    this._resolveCurrent = null;

                    if (timeoutId) {
                        nativeClearTimeout(timeoutId);
                    }
                });

            const { lastResults } = test;
            const afterTestError = await this._raceHookTimeout(
                "after-test",
                test,
                (onError) =>
                    this._execAfterCallback(async () => {
                        for (const callbackRegistry of callbackChain) {
                            await callbackRegistry.call("after-test", test, onError);
                        }
                    }),
            );
            if (afterTestError) {
                handleError(afterTestError);
            }
            test.after();

            restoreConsole();

            this.expectHooks.after(this);
            if (lastResults.pass) {
                logger.logTest(test);

                if (this.state.failedIds.has(test.id)) {
                    this.state.failedIds.delete(test.id);
                    storageSet(STORAGE.failed, [...this.state.failedIds]);
                }
            } else {
                this._failed++;

                const failReasons = [];
                const failedAssertions = lastResults.events.filter(
                    (event) =>
                        event.type & CASE_EVENT_TYPES.assertion.value && !event.pass,
                );
                if (failedAssertions.length) {
                    const s = failedAssertions.length === 1 ? "" : "s";
                    failReasons.push(
                        `\nFailed assertion${s}:`,
                        ...formatAssertions(failedAssertions),
                    );
                }
                if (lastResults.currentErrors.length) {
                    const s = lastResults.currentErrors.length === 1 ? "" : "s";
                    failReasons.push(
                        `\nError${s} during test:`,
                        ...lastResults.currentErrors.map((error) => {
                            let msg = `\n${error.message}`;
                            let cause = error.cause;
                            while (cause) {
                                msg += `\nCaused by: ${cause}`;
                                if (cause.stack) {
                                    msg += `\n${cause.stack}`;
                                }
                                cause = cause.cause;
                            }
                            return msg;
                        }),
                    );
                }
                this._reportFailedTest(test, failReasons);

                if (!this.aborted) {
                    if (this._failed === 1) {
                        this.state.failedIds.clear();
                    }
                    this.state.failedIds.add(test.id);
                    storageSet(STORAGE.failed, [...this.state.failedIds]);
                }
            }

            await this._callbacks.call("after-post-test", test, handleError);

            this._pushTest(test);
            this.totalTime = formatTime($now() - this._startTime);
            test.runCount++;

            if (this.debug) {
                return new Promise(() => {});
            }
            if (this.config.bail && this._failed >= this.config.bail) {
                return this.stop();
            }

            if (test.willRunAgain()) {
                test.reset();
            } else if (this.headless) {
                this._erase(test);
            } else {
                test.cleanup();
            }
            if (test.runCount < (test.config.multi || 0)) {
                continue;
            }

            job = this._nextJob(jobs, job);
        }

        if (this.state.status === "done") {
            return false;
        }

        this._pushPendingTest();

        if (!this.debug) {
            if (jobs.length) {
                this.state.status = "ready";
            } else {
                await this.stop();
            }
        }

        return true;
    }

    async stop() {
        this._currentJobs = [];
        this.state.status = "done";

        if (this._resolveCurrent) {
            this._resolveCurrent();

            return false;
        }

        while (this._missedCallbacks.length) {
            await this._missedCallbacks.shift()();
        }

        await this._callbacks.call("after-all", this, logger.error);

        if (this.headless) {
            const restoreLogLevel = logger.setLogLevel("suites");
            for (const suite of this.suites.values()) {
                if (!suite.parent) {
                    logger.logSuite(suite);
                }
            }
            restoreLogLevel();
        }

        const { passed, failed, assertions } = this.reporting;
        if (failed > 0) {
            const errorMessage = ["Some tests failed: see above for details"];
            if (this.headless) {
                const ids = this.simplifyUrlIds({ id: this.state.failedIds });
                const link = createUrlFromId(ids, { debug: true });
                link.searchParams.set("debug", "assets");
                link.searchParams.delete("headless");
                link.searchParams.delete("loglevel");
                link.searchParams.delete("timeout");
                errorMessage.push(`Failed tests link: ${link.toString()}`);
            }
            logger.logGlobal(
                `Failed ${failed} tests (${passed} passed, total time: ${this.totalTime})`,
            );
            $error(errorMessage.join("\n"));
        } else if (this.headless && passed === 0) {
            logger.logGlobal(`no tests matched the current filters`);
            $error(
                "Test suite matched no tests: failing closed (check the suite id filters)",
            );
        } else {
            logger.logGlobal(
                `Passed ${passed} tests (${assertions} assertions, total time: ${this.totalTime})`,
            );
            logger.logRun("Test suite succeeded");
        }

        logger.setIssueLevel("critical");

        return false;
    }

    /**
     * @template {(...args: any[]) => any} T
     * @template {false | (() => Job)} C
     * @param {T} fn
     * @param {C} getCurrent
     * @returns {typeof configurableFn}
     */
    _addConfigurators(fn, getCurrent) {
        /**
         * @typedef {((...args: DropFirst<Parameters<T>>) => Configurators) & Configurators} ConfigurableFunction
         * @typedef {{
         *  readonly debug: ConfigurableFunction;
         *  readonly only: ConfigurableFunction;
         *  readonly skip: ConfigurableFunction;
         *  readonly todo: ConfigurableFunction;
         *  readonly config: (...configs: JobConfig[]) => Configurators;
         *  readonly current: C extends false ? never : Configurators;
         *  readonly multi: (count: number) => Configurators;
         *  readonly tags: (...tagNames: string[]) => Configurators;
         *  readonly timeout: (ms: number) => Configurators;
         * }} Configurators
         */

        /** @type {Configurators["current"]} */
        const current =
            getCurrent && (() => this._createCurrentConfigurators(getCurrent));

        /** @type {Configurators["debug"]} */
        function debug() {
            tags("debug");
            return configurableFn;
        }

        /** @type {Configurators["only"]} */
        function only() {
            tags("only");
            return configurableFn;
        }

        /** @type {Configurators["skip"]} */
        function skip() {
            tags("skip");
            return configurableFn;
        }

        /** @type {Configurators["todo"]} */
        function todo() {
            tags("todo");
            return configurableFn;
        }

        /** @type {Configurators["config"]} */
        function config(...configs) {
            $assign(currentConfig, ...configs);
            return configurators;
        }

        /** @type {Configurators["multi"]} */
        function multi(count) {
            currentConfig.multi = count;
            return configurators;
        }

        /** @type {Configurators["tags"]} */
        function tags(...tagNames) {
            currentConfig.tags.push(...getTags(tagNames));
            return configurators;
        }

        /** @type {Configurators["timeout"]} */
        function timeout(ms) {
            currentConfig.timeout = ms;
            return configurators;
        }

        /** @type {ConfigurableFunction} */
        function configurableFn(...args) {
            const jobConfig = { ...currentConfig };
            currentConfig = { tags: [] };
            return boundFn(jobConfig, ...args);
        }

        const boundFn = fn.bind(this);

        const configuratorGetters = { debug, only, skip, todo };
        const configuratorMethods = { config, multi, tags, timeout };
        if (current) {
            configuratorGetters.current = current;
        }
        /** @type {Configurators} */
        const configurators = { ...configuratorGetters, ...configuratorMethods };

        for (const [key, getter] of $entries(configuratorGetters)) {
            $defineProperty(configurableFn, key, { get: getter });
        }
        for (const [key, getter] of $entries(configuratorMethods)) {
            $defineProperty(configurableFn, key, { value: getter });
        }

        /** @type {{ tags: Tag[], [key: string]: any }} */
        let currentConfig = { tags: [] };
        return configurableFn;
    }

    /** @param {Job} job */
    _applyTagModifiers(job) {
        let shouldSkip = false;
        let [ignoreSkip] = this._getExplicitIncludeStatus(job);
        for (const tag of job.tags) {
            this.tags.set(tag.id, tag);
            switch (tag.name) {
                case Tag.DEBUG:
                case Tag.ONLY:
                    if (tag.name === Tag.DEBUG) {
                        if (typeof this.debug !== "boolean" && this.debug !== job) {
                            throw new HootError(
                                `cannot set multiple tests or suites as "debug" at the same time`,
                                { level: "critical" },
                            );
                        }
                        this.debug = job;
                    }
                    if (!this.dry) {
                        logger.global.warn(
                            `${stringify(job.fullName)} is marked as ${stringify(
                                tag.name,
                            )}. This is not suitable for CI`,
                        );
                    }
                    this._include(
                        this.state.includeSpecs.id,
                        [job.id],
                        INCLUDE_LEVEL.tag,
                    );
                    ignoreSkip = true;
                    break;
                case Tag.SKIP:
                    shouldSkip = true;
                    break;
                case Tag.TODO:
                    job.config.todo = true;
                    break;
            }
        }

        if (shouldSkip) {
            if (ignoreSkip) {
                logger.global.warn(
                    `${stringify(
                        job.fullName,
                    )} is marked as skipped but explicitly included: "skip" modifier has been ignored`,
                );
            } else {
                job.config.skip = true;
            }
        }
    }

    /** @param {() => Job} getCurrent */
    _createCurrentConfigurators(getCurrent) {
        /** @param {JobConfig} config */
        function configureCurrent(config) {
            getCurrent().configure(config);

            return currentConfigurators;
        }

        /** @param {...string} tagNames */
        const addTagsToCurrent = (...tagNames) => {
            const current = getCurrent();
            current.configure({ tags: getTags(tagNames) });
            this._applyTagModifiers(current);

            return currentConfigurators;
        };

        /** @type {CurrentConfigurators} */
        const currentConfigurators = $freeze({
            config: configureCurrent,
            debug: () => addTagsToCurrent("debug"),
            multi: (count) => configureCurrent({ multi: count }),
            only: () => addTagsToCurrent("only"),
            skip: () => addTagsToCurrent("skip"),
            tags: addTagsToCurrent,
            timeout: (ms) => configureCurrent({ timeout: ms }),
            todo: () => addTagsToCurrent("todo"),
        });

        return currentConfigurators;
    }

    /**
     * @param {Job} job
     * @param {boolean} [canEraseParent]
     */
    _erase(job, canEraseParent = false) {
        if (job instanceof Suite) {
            if (!job.reporting.failed) {
                this.suites.delete(job.id);
            }
        } else {
            if (job.results.every((result) => result.pass)) {
                this.tests.delete(job.id);
            }
        }
        job.minimize();
        if (canEraseParent && job.parent) {
            const jobIndex = job.parent.jobs.indexOf(job);
            if (jobIndex >= 0) {
                job.parent.jobs.splice(jobIndex, 1);
            }
            if (!job.parent.jobs.length) {
                if (this.suiteStack.includes(job.parent)) {
                    this.emptiedWhileDeclaring.add(job.parent);
                } else {
                    this._erase(job.parent);
                }
            }
        }
        return job;
    }

    /** @param {() => Promise<void>} callback */
    async _execAfterCallback(callback) {
        if (this.debug) {
            this._missedCallbacks.push(callback);
        } else {
            await callback();
        }
    }

    /**
     * @param {"before-test" | "after-test"} phase
     * @param {Test} test
     * @param {(onError: Runner["_handleError"]) => Promise<void>} runHooks
     * @returns {Promise<Error | null>}
     */
    async _raceHookTimeout(phase, test, runHooks) {
        const hookTimeout = $floor(this.config.hookTimeout);
        let error = null;
        const onHookError = (reason) => {
            if (!error) {
                return this._handleError(reason);
            }
        };
        await Promise.race([
            runHooks(onHookError),
            new Promise((_, reject) =>
                nativeSetTimeout(
                    () =>
                        reject(
                            new HootError(
                                `${stringify(phase)} hooks of test ${stringify(
                                    test.name,
                                )} timed out after ${hookTimeout} milliseconds`,
                            ),
                        ),
                    hookTimeout,
                ),
            ),
        ]).catch((reason) => {
            error = reason;
        });
        return error;
    }

    /**
     * @param {Job} job
     * @returns {Callbacks[]}
     */
    _getCallbackChain(job) {
        const chain = [];
        while (job) {
            if (job instanceof Suite) {
                chain.push(job.callbacks);
            }
            job = job.parent;
        }
        chain.push(this._callbacks);
        return chain;
    }

    /** @param {Job} job */
    _getExplicitIncludeStatus(job) {
        const explicitInclude = this.state.includeSpecs.id[job.id] || 0;
        return [explicitInclude > 0, explicitInclude < 0];
    }

    /**
     * @param {Record<string, number>} values
     * @param {Iterable<string>} ids
     * @param {number} includeLevel
     * @param {boolean} [noIncrement]
     */
    _include(values, ids, includeLevel, noIncrement = false) {
        const isRemovable = $abs(includeLevel) === INCLUDE_LEVEL.url;
        const shouldInclude = !!includeLevel;
        let applied = 0;
        for (const id of ids) {
            let idLevel = includeLevel;
            let nId = normalize(id.toLowerCase());
            if (nId.startsWith(EXCLUDE_PREFIX)) {
                nId = nId.slice(EXCLUDE_PREFIX.length);
                if (idLevel > 0) {
                    idLevel *= -1;
                }
            }
            const previousValue = values[nId] || 0;
            const wasRemovable = $abs(previousValue) === INCLUDE_LEVEL.url;
            if (wasRemovable) {
                applied++;
            }
            if (shouldInclude) {
                if (previousValue === idLevel) {
                    continue;
                }
                values[nId] = idLevel;
                if (noIncrement) {
                    continue;
                }
                if (previousValue <= 0 && idLevel > 0) {
                    this._includeFilterCount++;
                } else if (previousValue > 0 && idLevel <= 0) {
                    this._includeFilterCount--;
                }
                if (!wasRemovable && isRemovable) {
                    this._removableFilterCount++;
                } else if (wasRemovable && !isRemovable) {
                    this._removableFilterCount--;
                }
            } else {
                delete values[nId];
                if (noIncrement) {
                    continue;
                }
                if (previousValue > 0) {
                    this._includeFilterCount--;
                }
                if (wasRemovable) {
                    this._removableFilterCount--;
                }
            }
        }
        return applied;
    }

    /**
     * @param {Job} job
     * @returns {boolean | null}
     */
    _isImplicitlyExcluded(job) {
        for (const [tagName, status] of $entries(this.state.includeSpecs.tag)) {
            if (status < 0 && job.tags.some((tag) => tag.name === tagName)) {
                return true;
            }
        }

        if (
            this.queryExclude.length &&
            this.queryExclude.some((qp) => qp.matchValue(job.key))
        ) {
            return true;
        }

        return false;
    }

    /**
     * @param {Job} job
     * @returns {boolean | null}
     */
    _isImplicitlyIncluded(job) {
        for (const [tagName, status] of $entries(this.state.includeSpecs.tag)) {
            if (status > 0 && job.tags.some((tag) => tag.name === tagName)) {
                return true;
            }
        }

        if (
            this.queryInclude.length &&
            this.queryInclude.every((qp) => qp.matchValue(job.key))
        ) {
            return true;
        }

        return false;
    }

    /**
     * @param {Job[]} jobs
     * @param {Job} [job]
     */
    _nextJob(jobs, job) {
        this.state.currentTest = null;
        if (job) {
            const sibling = job.currentJobs?.[job.currentJobIndex++];
            if (sibling) {
                return sibling;
            }
            const parent = job.parent;
            if (parent && (!jobs.length || jobs.some((j) => parent.path.includes(j)))) {
                return parent;
            }
        }
        const index = this._currentJobs.findIndex(Boolean);
        if (index >= 0) {
            return this._currentJobs.splice(index, 1)[0];
        }
        return null;
    }

    /**
     * @param {Job[]} jobs
     * @param {boolean} [implicitInclude]
     * @returns {Job[]}
     */
    _prepareJobs(jobs, implicitInclude = !this._includeFilterCount) {
        if (typeof this.debug !== "boolean") {
            let debugTest = this.debug;
            while (debugTest instanceof Suite) {
                if (debugTest.jobs.length > 1) {
                    logger.global.warn(
                        `debugging a suite with ${debugTest.jobs.length} jobs: only the first one will be run`,
                    );
                }
                debugTest = debugTest.jobs[0];
            }

            if (this._populateState) {
                this.state.tests.push(debugTest);
            }

            const jobs = debugTest.path;
            for (let i = 0; i < jobs.length - 1; i++) {
                const suite = jobs[i];
                suite.setCurrentJobs([jobs[i + 1]]);
                if (this._populateState) {
                    this.state.suites.push(suite);
                }
            }
            return [jobs[0]];
        }

        const filteredJobs = jobs.filter((job) => {
            const [explicitInclude, explicitExclude] =
                this._getExplicitIncludeStatus(job);
            if (explicitExclude) {
                return false;
            }

            if (!explicitInclude && this._isImplicitlyExcluded(job)) {
                return false;
            }

            let included =
                explicitInclude || implicitInclude || this._isImplicitlyIncluded(job);
            if (job instanceof Suite) {
                job.setCurrentJobs(this._prepareJobs(job.jobs, included));
                included = Boolean(job.currentJobs.length);

                if (included && this._populateState) {
                    this.state.suites.push(job);
                }
            } else if (included && this._populateState) {
                this.state.tests.push(job);
            }
            return included;
        });

        switch (this.config.order) {
            case "fifo": {
                return filteredJobs;
            }
            case "lifo": {
                return filteredJobs.reverse();
            }
            case "random": {
                return shuffle(filteredJobs);
            }
        }
    }

    _prepareRunner() {
        if (this._prepared) {
            return {};
        }
        this._prepared = true;

        if (this.config.preset) {
            const preset = this.presets[this.config.preset];
            if (!preset) {
                throw new HootError(`unknown preset: "${this.config.preset}"`, {
                    level: "critical",
                });
            }
            if (preset.tags?.length) {
                this._include(
                    this.state.includeSpecs.tag,
                    preset.tags,
                    INCLUDE_LEVEL.preset,
                );
            }
            if (typeof preset.touch === "boolean") {
                this.beforeEach(() => mockTouch(preset.touch));
            }
            this.checkPresetForViewPort();
        }

        const hasChanged = this._simplifyIncludeSpecs(this.state.includeSpecs.id);
        if (hasChanged) {
            this._updateConfigFromSpecs();
        }

        const failedIds = [...this.state.failedIds];
        const existingFailed = failedIds.filter((id) => this.tests.has(id));
        if (existingFailed.length !== failedIds.length) {
            this.state.failedIds = new Set(existingFailed);
            storageSet(STORAGE.failed, existingFailed);
        }

        const similarities = getTagSimilarities();
        if (similarities.length) {
            this._handleGlobalWarning(
                WARNINGS.tagNames +
                    similarities.map((s) => `\n- ${s.map(stringify).join(" / ")}`),
            );
            logger.global.warn(WARNINGS.tagNames, similarities);
        }

        this._populateState = true;
        this._currentJobs = this._prepareJobs(this.rootSuites);
        this._populateState = false;

        if (!this.state.tests.length) {
            logger.logGlobal(`no tests to run`);
        }

        const includedSuites = new Set(this.state.suites);
        for (const suite of this.suites.values()) {
            if (!includedSuites.has(suite)) {
                if (this.headless) {
                    this._erase(suite, true);
                } else {
                    suite.minimize();
                }
            }
        }
        const includedTests = new Set(this.state.tests);
        for (const test of this.tests.values()) {
            if (!includedTests.has(test)) {
                if (this.headless) {
                    this._erase(test, true);
                } else {
                    test.minimize();
                }
            }
        }

        if (this.headless) {
            this.rootSuites.length = 0;
            this.state.suites.length = 0;
            this.state.tests.length = 0;
        }

        return {
            suites: [...includedSuites],
            tests: [...includedTests],
        };
    }

    /** @param {Error | ErrorEvent | PromiseRejectionEvent} ev */
    _handleError(ev) {
        if (this.config.notrycatch) {
            return;
        }
        const error = ensureError(ev);

        if (!isInstanceOf(ev, Event)) {
            ev = new ErrorEvent("error", { error });
        }

        if (handledErrors.has(error)) {
            return ev.preventDefault();
        }
        handledErrors.add(error);

        mockPreventDefault(ev);

        if (error.message.includes(RESIZE_OBSERVER_MESSAGE)) {
            ev.stopImmediatePropagation();
            if (ev.bubbles) {
                ev.stopPropagation();
            }
            return ev.preventDefault();
        }

        if (this.state.currentTest && !(error instanceof HootError)) {
            const handled = this._handleErrorInTest(ev, error);
            if (handled) {
                return ev.preventDefault();
            }
        } else {
            this._handleGlobalError(ev, error);
        }

        ev.preventDefault();

        if (error.level) {
            const restoreLogger = logger.setIssueLevel(error.level);
            logger.error(error.level === "global" ? String(error) : error);
            restoreLogger();
        } else {
            logger.error(error);
        }
    }

    /**
     * @param {ErrorEvent | PromiseRejectionEvent} ev
     * @param {Error} error
     */
    _handleErrorInTest(ev, error) {
        for (const callbackRegistry of this._getCallbackChain(this.state.currentTest)) {
            callbackRegistry.callSync("error", ev, logger.error);
            if (isPrevented(ev)) {
                return true;
            }
        }

        return this.expectHooks.error(error);
    }

    /**
     * @param {ErrorEvent | PromiseRejectionEvent} ev
     * @param {Error} error
     */
    _handleGlobalError(ev, error) {
        const { globalErrors } = this.state;
        const key = String(error);
        if (globalErrors[key]) {
            globalErrors[key].count++;
        } else {
            globalErrors[key] = {
                count: 1,
                message: error.message,
                name: error.constructor.name || error.name,
            };
        }
        return false;
    }

    /** @param {string} message */
    _handleGlobalWarning(message) {
        const { globalWarnings } = this.state;
        const key = message;
        if (globalWarnings[key]) {
            globalWarnings[key].count++;
        } else {
            globalWarnings[key] = {
                count: 1,
                message,
                name: this.config.fun ? "warming" : "warning",
            };
        }
        return false;
    }

    async _setupStart() {
        this._startTime = $now();
        if (this.config.manual) {
            this._canStartDef ||= Promise.withResolvers();
        }

        const table = { ...toRaw(this.config) };
        for (const key of FILTER_KEYS) {
            if (isIterable(table[key])) {
                table[key] = `[${[...table[key]].join(", ")}]`;
            }
        }
        logger.group("Configuration (click to expand)", () => {
            logger.table(table);
        });
        logger.logRun("Starting test suites");
        logger.setIssueLevel("trace");

        if (this.debug) {
            const activeSingleTests = this.state.tests.filter(
                (test) => !test.config.skip && !test.config.multi,
            );
            if (activeSingleTests.length !== 1) {
                logger.global.warn(
                    `Disabling debug mode: ${activeSingleTests.length} tests will be run`,
                );
                this.config.debugTest = false;
                this.debug = false;
            } else {
                const nameSpace = exposeHelpers(
                    _hootDom,
                    _animation,
                    _date,
                    _math,
                    _navigator,
                    _network,
                    _notification,
                    _window,
                    {
                        __debug__: this,
                        destroy,
                        getFixture: this.fixture.get,
                    },
                );
                logger.setLogLevel("debug");
                logger.logDebug(
                    `Debug mode is active: Hoot helpers available from \`window.${nameSpace}\``,
                );
            }
        }

        this.beforeAll(defineRootNode.bind(null, this.fixture.get));
        this.afterAll(
            !this.debug && on(window, "pointermove", warnUserEvent),
            !this.debug && on(window, "pointerdown", warnUserEvent),
            !this.debug && on(window, "keydown", warnUserEvent),
        );
        this.beforeEach(this.fixture.setup, setupWindow, setupTime);
        this.afterEach(
            this.fixture.cleanup,
            cleanupAnimations,
            cleanupWindow,
            cleanupNetwork,
            cleanupNavigator,
            cleanupEvents,
            cleanupDOM,
            cleanupDate,
            cleanupTime,
        );

        enableEventLogs(logger.canLog("debug"));
        setFrameRate(this.config.fps);

        await this._callbacks.call("before-all", this, logger.error);
    }

    /** @param {Runner["state"]["includeSpecs"]["id"]} idSpecs */
    _simplifyIncludeSpecs(idSpecs) {
        let hasChanged = false;
        const unresolved = [];
        let remaining = $keys(idSpecs);
        while (remaining.length) {
            const id = remaining.shift();
            const value = idSpecs[id];
            if ($abs(value) !== INCLUDE_LEVEL.url) {
                continue;
            }
            const item = this.suites.get(id) || this.tests.get(id);
            if (!item) {
                const couldRemove = this._include(idSpecs, [id], 0);
                if (value > 0) {
                    unresolved.push(id);
                    if (couldRemove) {
                        logger.warn(
                            `Test runner did not find job with ID "${id}": it has been removed from the URL`,
                        );
                    } else {
                        logger.warn(
                            `Test runner did not find job with ID "${id}": it has been ignored from the current run`,
                        );
                    }
                }
                hasChanged = true;
            }
            if (!item?.parent || item.parent.jobs.length < 1) {
                continue;
            }
            const siblingIds = item.parent.jobs.map((job) => job.id);
            if (
                siblingIds.every(
                    (siblingId) => idSpecs[siblingId] === INCLUDE_LEVEL.url,
                )
            ) {
                remaining = remaining.filter((id) => !siblingIds.includes(id));
                this._include(idSpecs, [item.parent.id], INCLUDE_LEVEL.url, true);
                this._include(idSpecs, siblingIds, 0, true);
                hasChanged = true;
            }
        }
        if (unresolved.length && this.headless) {
            throw new HootError(
                `no suite or test matches ${unresolved.length > 1 ? "ids" : "id"} ${unresolved
                    .map(stringify)
                    .join(", ")}: refusing to fall back to running every test`,
                { level: "critical" },
            );
        }
        return hasChanged;
    }

    _updateConfigFromSpecs() {
        for (const type of FILTER_KEYS) {
            if (type === "filter") {
                continue;
            }
            this.config[type] = formatIncludes(this.state.includeSpecs[type]);
        }
    }
}
