/** @odoo-module */

import { Deferred, on, setFrameRate } from "@odoo/hoot-dom";
import { markRaw, reactive, toRaw } from "@odoo/owl";
import { cleanupDOM } from "@web/../lib/hoot-dom/helpers/dom";
import { cleanupEvents, enableEventLogs } from "@web/../lib/hoot-dom/helpers/events";
import { cleanupTime, setupTime } from "@web/../lib/hoot-dom/helpers/time";
import { exposeHelpers, isIterable } from "@web/../lib/hoot-dom/hoot_dom_utils";
import {
    CASE_EVENT_TYPES,
    Callbacks,
    HootError,
    INCLUDE_LEVEL,
    Markup,
    STORAGE,
    batch,
    createReporting,
    deepEqual,
    ensureArray,
    ensureError,
    formatHumanReadable,
    formatTechnical,
    formatTime,
    isLabel,
    normalize,
    parseQuery,
    storageGet,
    storageSet,
    stringify,
} from "../hoot_utils";
import { cleanupAnimations } from "../mock/animation";
import { cleanupDate } from "../mock/date";
import { internalRandom } from "../mock/math";
import { cleanupNavigator, mockUserAgent } from "../mock/navigator";
import { cleanupNetwork, throttleNetwork } from "../mock/network";
import {
    cleanupWindow,
    getViewPortHeight,
    getViewPortWidth,
    mockTouch,
    setupWindow,
} from "../mock/window";
import { DEFAULT_CONFIG, FILTER_KEYS } from "./config";
import { makeExpect } from "./expect";
import { destroy, makeFixtureManager } from "./fixture";
import { logger } from "./logger";
import { Suite, suiteError } from "./suite";
import { Tag, getTagSimilarities, getTags } from "./tag";
import { Test, testError } from "./test";
import { EXCLUDE_PREFIX, createUrlFromId, setParams } from "./url";

// Import all helpers for debug mode
import * as hootDom from "@odoo/hoot-dom";
import * as hootMock from "@odoo/hoot-mock";

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
 *
 * @typedef {{
 *  count: number;
 *  message: string;
 *  name: string;
 * }} GlobalIssueReport
 *
 * @typedef {Suite | Test} Job
 *
 * @typedef {import("./job").JobConfig} JobConfig
 *
 * @typedef {{
 *  icon?: string;
 *  label: string;
 *  platform?: import("../mock/navigator").Platform;
 *  size?: [number, number];
 *  tags?: string[];
 *  touch?: boolean;
 * }} Preset
 *
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

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const {
    clearTimeout,
    console: { error: $error },
    EventTarget,
    Map,
    Math: { abs: $abs, floor: $floor },
    Number: { parseFloat: $parseFloat },
    Object: {
        assign: $assign,
        defineProperties: $defineProperties,
        entries: $entries,
        freeze: $freeze,
        fromEntries: $fromEntries,
        keys: $keys,
    },
    performance,
    Promise,
    removeEventListener,
    Set,
    setTimeout,
    window,
} = globalThis;
/** @type {Performance["now"]} */
const $now = performance.now.bind(performance);

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @param {Job[]} jobs
 */
function filterReady(jobs) {
    return jobs.filter((job) => {
        if (job instanceof Suite) {
            job.setCurrentJobs(filterReady(job.currentJobs));
            return job.currentJobs.length;
        }
        return job.run;
    });
}

/**
 * @param {Record<string, number>} values
 */
function formatIncludes(values) {
    return $entries(values)
        .filter(([, value]) => $abs(value) === INCLUDE_LEVEL.url)
        .map(([id, value]) => (value >= 0 ? id : `${EXCLUDE_PREFIX}${id}`));
}

/**
 * @param {import("./expect").Assertion[]} assertions
 */
function formatAssertions(assertions) {
    const lines = [];
    for (const { failedDetails, label, message, number } of assertions) {
        const formattedMessage = message.map((part) => (isLabel(part) ? part[0] : String(part)));
        lines.push(`\n${number}. [${label}] ${formattedMessage.join(" ")}`);
        if (failedDetails) {
            for (const detail of failedDetails) {
                if (Markup.isMarkup(detail, "group")) {
                    lines.push(
                        `${number}.${detail.groupIndex}. (${formatHumanReadable(detail.content)})`
                    );
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
 * @param {Event} ev
 */
function safePrevent(ev) {
    if (ev.cancelable) {
        ev.preventDefault();
    }
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
        return logger.suppressIssues(`suppressed by "test.todo"`);
    } else {
        const cleanups = [];
        if (globalThis.console instanceof EventTarget) {
            cleanups.push(
                on(globalThis.console, "error", () => test.logs.error++),
                on(globalThis.console, "warn", () => test.logs.warn++)
            );
        }

        return function offConsoleEvents() {
            while (cleanups.length) {
                cleanups.pop()();
            }
        };
    }
}

/**
 * @param {Event} ev
 */
function warnUserEvent(ev) {
    if (!ev.isTrusted) {
        return;
    }

    logger.warn(
        `User event detected: "${ev.type}"\n\n`,
        `This kind of interaction can interfere with the current test and should be avoided.`
    );

    removeEventListener(ev.type, warnUserEvent);
}

const WARNINGS = {
    viewport: "Viewport size does not match the expected size for the current preset",
    tagNames:
        "The following tag names are very similar to each other and may be confusing for other developers:",
};
const RESIZE_OBSERVER_MESSAGE = "ResizeObserver loop completed with undelivered notifications";
const handledErrors = new WeakSet();
/** @type {string | null} */
let lastPresetWarn = null;

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export class Runner {
    static URL_SPEC = 1;
    static TAG_SPEC = 2;
    static PRESET_SPEC = 3;

    // Properties
    aborted = false;
    /** @type {boolean | Test | Suite} */
    debug = false;
    dry = false;
    /** @type {ReturnType<typeof makeExpect>[0]} */
    expect;
    /** @type {ReturnType<typeof makeExpect>[1]} */
    expectHooks;
    /** @type {Record<string, Preset>} */
    presets = reactive({
        [""]: { label: "No preset" },
    });
    reporting = createReporting();
    /** @type {Suite[]} */
    rootSuites = [];
    state = reactive({
        /** @type {Test | null} */
        currentTest: null,
        /**
         * List of tests that have been run
         * @type {Set<Test>}
         */
        done: new Set(),
        /**
         * List of IDs of tests that have failed (previously AND during this run).
         */
        failedIds: new Set(storageGet(STORAGE.failed)),
        /**
         * @type {Record<string, GlobalIssueReport>}
         */
        globalErrors: {},
        /**
         * @type {Record<string, GlobalIssueReport>}
         */
        globalWarnings: {},
        /**
         * Dictionnary containing whether a job is included or excluded from the
         * current run. Values are numbers defining priority:
         *  - 0: inherits inclusion status from parent object
         *  - +1/-1: included/excluded by URL
         *  - +2/-2: included/excluded by explicit test tag (readonly)
         *  - +3/-3: included/excluded by preset (readonly)
         * @type {Record<Exclude<SearchFilter, "filter">, Record<string, number>>}
         */
        includeSpecs: {
            suite: {},
            tag: {},
            test: {},
        },
        /** @type {"ready" | "running" | "done"} */
        status: "ready",
        /**
         * List of suites that will be run (only available after {@link Runner.start})
         * @type {Suite[]}
         */
        suites: [],
        /**
         * List of tests that will be run (only available after {@link Runner.start})
         * @type {Test[]}
         */
        tests: [],
    });
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

    /**
     * @type {boolean}
     */
    get hasFilter() {
        return this._hasRemovableFilter > 0;
    }

    // Private properties
    _callbacks = new Callbacks();
    /** @type {Job[]} */
    _currentJobs = [];
    _failed = 0;
    _hasRemovableFilter = 0;
    _hasIncludeFilter = 0;
    /** @type {(() => MaybePromise<void>)[]} */
    _missedCallbacks = [];
    _populateState = false;
    _prepared = false;
    /** @type {() => void} */
    _pushPendingTest;
    /** @type {(test: Test) => void} */
    _pushTest;
    _started = false;
    _startTime = 0;

    /** @type {null | (value?: any) => any} */
    _resolveCurrent = null;

    /**
     * @param {typeof DEFAULT_CONFIG} [config]
     */
    constructor(config) {
        // Main test methods
        this.describe = this._addConfigurators(this.addSuite, () => this.suiteStack.at(-1));
        this.fixture = makeFixtureManager(this);
        this.test = this._addConfigurators(this.addTest, false);

        this.initialConfig = { ...DEFAULT_CONFIG, ...config };
        const reactiveConfig = reactive({ ...this.initialConfig }, () => {
            setParams(
                $fromEntries(
                    $entries(this.config).map(([key, value]) => [
                        key,
                        deepEqual(value, DEFAULT_CONFIG[key]) ? null : value,
                    ])
                )
            );
        });

        [this._pushTest, this._pushPendingTest] = batch((test) => this.state.done.add(test), 10);
        [this.expect, this.expectHooks] = makeExpect({
            get headless() {
                return reactiveConfig.headless;
            },
        });

        this.config = reactiveConfig;
        for (const key in this.config) {
            this.config[key];
        }

        // Debug
        this.debug = Boolean(this.config.debugTest);

        // Text filter
        if (this.config.filter) {
            for (const queryPart of parseQuery(this.config.filter)) {
                if (queryPart.exclude) {
                    this.queryExclude.push(queryPart);
                } else {
                    this.queryInclude.push(queryPart);
                }
            }
            this._hasIncludeFilter += this.queryInclude.length;
        }

        // Suites
        if (this.config.suite?.length) {
            this._include(this.state.includeSpecs.suite, this.config.suite, INCLUDE_LEVEL.url);
        }

        // Tags
        if (this.config.tag?.length) {
            this._include(this.state.includeSpecs.tag, this.config.tag, INCLUDE_LEVEL.url);
        }

        // Tests
        if (this.config.test?.length) {
            this._include(this.state.includeSpecs.test, this.config.test, INCLUDE_LEVEL.url);
        }

        if (this.config.networkDelay) {
            const values = this.config.networkDelay.split("-").map((val) => $parseFloat(val) || 0);
            throttleNetwork(...values);
        }

        // Random seed
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
            throw new HootError(`a suite name must not be empty, got ${name}`);
        }
        const names = ensureArray(name).flatMap((n) => normalize(n).split("/").filter(Boolean));
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
                `expected second argument to be a function and got ${String(fn)}`
            );
        }
        if (this.state.status === "running") {
            throw suiteError(
                { name: suiteName, parent: parentSuite },
                `cannot add a suite after the test runner started`
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

        let error, result;
        if (!this._prepared || suite.currentJobs.length) {
            try {
                result = fn();
            } catch (err) {
                error = String(err);
            }
        }
        this.suiteStack.pop();
        if (error) {
            throw suiteError({ name: suiteName, parent: parentSuite }, error);
        } else if (result !== undefined) {
            throw suiteError(
                { name: suiteName, parent: parentSuite },
                `the suite function cannot return a value`
            );
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
            throw new HootError(`a test name must not be empty, got ${name}`);
        }
        const parentSuite = this.suiteStack.at(-1);
        if (!parentSuite) {
            throw testError({ name, parent: null }, `cannot register a test outside of a suite.`);
        }
        if (typeof fn !== "function") {
            throw testError(
                { name, parent: parentSuite },
                `expected second argument to be a function and got ${String(fn)}`
            );
        }
        if (this.state.status === "running") {
            throw testError(
                { name, parent: parentSuite },
                `cannot add a test after the test runner started.`
            );
        }
        const runFn = this.dry ? null : fn;
        let test = markRaw(new Test(parentSuite, name, config));
        const originalTest = this.tests.get(test.id);
        if (originalTest) {
            if (this.dry || originalTest.run) {
                throw testError(
                    { name, parent: parentSuite },
                    `a test with that name already exists in the suite ${stringify(
                        parentSuite.name
                    )}`
                );
            }
            test = originalTest;
        } else {
            parentSuite.addJob(test);
            this.tests.set(test.id, test);
        }

        test.setRunFn(runFn);

        this._applyTagModifiers(test);

        return test;
    }

    /**
     * Registers a callback that will be executed at the end of the current test
     * entity:
     *
     * - inside of a test: executed at the end of the *current* test, after all
     *  assertions have been completed;
     *
     * - inside of a suite: executed at the end of the *current* suite, after all
     *  tests have been run. Note that neither "after" nor "before" callbacks will
     *  be called if the suite is empty (= no tests to run);
     *
     * - outside of a suite: executed at the end of *every* suite
     *
     * @param {...Callback<Job>} callbacks
     */
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

    /**
     * @param {...Callback<never>} callbacks
     */
    afterAll(...callbacks) {
        for (const callback of callbacks) {
            this._callbacks.add("after-all", callback);
        }
    }

    /**
     * Registers a callback that will be executed at the end of each test in the
     * current test entity:
     *
     * - inside of a suite: executed for all tests in the *current* suite;
     *
     * - outside of a suite: executed for every single test accross *all* suites.
     *
     * @param {...Callback<Test>} callbacks
     */
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

    /**
     * @param {...Callback<Test>} callbacks
     */
    afterPostTest(...callbacks) {
        for (const callback of callbacks) {
            this._callbacks.add("after-post-test", callback);
        }
    }

    /**
     * Registers a callback that will be executed at the start of the current test
     * entity:
     *
     * - inside of a test: executed at the start of the *current* test, before any
     *  assertion have been completed;
     *
     * - inside of a suite: executed at the start of the *current* suite, before any
     *  test is run. Note that neither "before" nor "before" callbacks will be called
     *  if the suite is empty (= no tests to run);
     *
     * - outside of a suite: executed at the start of *every* suite
     *
     * @param {...Callback<Job>} callbacks
     */
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

    /**
     * @param {...Callback<never>} callbacks
     */
    beforeAll(...callbacks) {
        for (const callback of callbacks) {
            this._callbacks.add("before-all", callback);
        }
    }

    /**
     * Registers a callback that will be executed at the start of each test in the
     * current test entity:
     *
     * - inside of a suite: executed for all tests in the *current* suite;
     *
     * - outside of a suite: executed for every single test accross *all* suites.
     *
     * @param {...Callback<Test>} callbacks
     */
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
                logger.warn(
                    WARNINGS.viewport,
                    `\n> expected:`,
                    width,
                    "x",
                    height,
                    `\n> current:`,
                    innerWidth,
                    "x",
                    innerHeight,
                    `\n\nHint: you can use the "device toolbar" in your devtools to manually set the size of your viewport`
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

    /**
     * @param {() => Promise<void>} callback
     */
    async dryRun(callback) {
        if (this.state.status !== "ready") {
            throw new HootError("cannot run a dry run after the test runner started");
        }
        if (this._prepared) {
            throw new HootError("cannot run a dry run: runner has already been prepared");
        }

        this.dry = true;

        await callback();

        this._prepareRunner();

        this.dry = false;

        return {
            suites: this.state.suites,
            tests: this.state.tests,
        };
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
        this._canStartPromise.resolve(true);
    }

    /**
     * Registers callbacks that will be executed when an error occurs during the
     * execution of the test runner.
     *
     * If called within a test, the given callbacks will only be called once.
     *
     * @param {...Callback<ErrorEvent | PromiseRejectionEvent>} callbacks
     */
    onError(...callbacks) {
        const { suite, test } = this.getCurrent();
        const callbackRegistry = suite ? suite.callbacks : this._callbacks;
        for (const callback of callbacks) {
            callbackRegistry.add("error", callback, Boolean(test));
        }
    }

    /**
     * @param {Partial<Record<SearchFilter, Iterable<string>>>} ids
     */
    simplifyUrlIds(ids) {
        if (!ids) {
            return {};
        }
        const specs = {
            suite: {},
            tag: {},
            test: {},
        };
        let items = 0;
        for (const key in specs) {
            if (ids[key]) {
                for (const id of ensureArray(ids[key])) {
                    items++;
                    specs[key][id] = INCLUDE_LEVEL.url;
                }
            }
        }
        if (items > 1) {
            this._simplifyIncludeSpecs(specs, {
                test: this.tests,
                suite: this.suites,
            });
        }
        for (const key in specs) {
            specs[key] = $keys(specs[key]);
        }
        return specs;
    }

    /**
     * Boot function starting all registered tests and suites.
     *
     * The returned promise is resolved after all tests (and teardowns) have been
     * executed. Its value is an object containing the list of tests and suites
     * that have been run.
     *
     * An optional "dry" option can be passed to the function to only prepare the
     * list of tests and suites that will be run, without actually running them.
     * It will then reset all tests' run functions to allow them to be registered
     * again with the actual run functions.
     *
     * @param {...Job} jobs
     */
    async start(...jobs) {
        if (!this._started) {
            this._started = true;
            this._prepareRunner();
            await this._setupStart();
        } else if (!jobs.length) {
            throw new HootError("cannot start test runner: runner has already started");
        }

        if (this.state.status === "done") {
            return false;
        }

        if (jobs.length) {
            this._currentJobs = filterReady(jobs);
        }

        if (this._canStartPromise) {
            await this._canStartPromise;
        }

        this.state.status = "running";

        /** @type {Runner["_handleError"]} */
        const handleError = this._handleError.bind(this);

        let job = this._nextJob(jobs);
        while (job && this.state.status === "running") {
            const callbackChain = this._getCallbackChain(job);
            if (job instanceof Suite) {
                // Case: suite
                // -----------

                /** @type {Suite} */
                const suite = job;
                if (!suite.config.skip) {
                    if (suite.currentJobIndex <= 0) {
                        // before suite code
                        this.suiteStack.push(suite);

                        suite.before();
                        await this._callbacks.call("before-suite", suite, handleError);
                        await suite.callbacks.call("before-suite", suite, handleError);
                    }
                    if (suite.currentJobIndex >= suite.currentJobs.length) {
                        // after suite code
                        this.suiteStack.pop();

                        await this._execAfterCallback(async () => {
                            await suite.callbacks.call("after-suite", suite, handleError);
                            await this._callbacks.call("after-suite", suite, handleError);
                        });
                        suite.after();

                        logger.logSuite(suite);

                        suite.runCount++;
                        if (suite.willRunAgain()) {
                            suite.reset();
                        } else {
                            suite.cleanup();
                        }
                        if (suite.runCount < (suite.config.multi || 0)) {
                            continue;
                        }
                    }
                }
                job = this._nextJob(jobs, job);
                continue;
            }

            // Case: test
            // ----------

            /** @type {Test} */
            const test = job;
            if (test.config.skip) {
                // Skipped test
                this._pushTest(test);
                test.setRunFn(null);
                test.parent.reporting.add({ skipped: +1, tests: +1 });
                job = this._nextJob(jobs, job);
                continue;
            }

            // Suppress console errors and warnings if test is in "todo" mode
            // (and not in debug).
            const restoreConsole = handleConsoleIssues(test, !this.debug);

            // Before test
            this.state.currentTest = test;
            this.expectHooks.before(test);
            test.before();
            for (const callbackRegistry of [...callbackChain].reverse()) {
                await callbackRegistry.call("before-test", test, handleError);
            }

            let timeoutId = 0;

            // ! The following assignment should stay in the `start` function to
            // ! keep the smallest stack trace possible:
            // !    Runner.start() > Test.run() > Error
            const testPromise = Promise.resolve(test.run());
            const timeout = $floor(test.config.timeout || this.config.timeout);
            const timeoutPromise = new Promise((resolve, reject) => {
                // Set abort signal
                this._resolveCurrent = resolve;

                if (timeout && !this.debug) {
                    // Set timeout
                    timeoutId = setTimeout(
                        () =>
                            reject(
                                new HootError(
                                    `test ${stringify(
                                        test.name
                                    )} timed out after ${timeout} milliseconds`
                                )
                            ),
                        timeout
                    );
                }
            }).then(() => {
                this.aborted = true;
                this.debug = false; // Remove debug mode to let the runner stop
            });

            // Run test
            await Promise.race([testPromise, timeoutPromise])
                .catch((error) => {
                    if (handleError) {
                        return handleError(error);
                    } else {
                        throw error;
                    }
                })
                .finally(() => {
                    this._resolveCurrent = null;

                    if (timeoutId) {
                        clearTimeout(timeoutId);
                    }
                });

            // After test
            const { lastResults } = test;
            await this._execAfterCallback(async () => {
                for (const callbackRegistry of callbackChain) {
                    await callbackRegistry.call("after-test", test, handleError);
                }
            });
            test.after();

            restoreConsole();

            // Log test errors and increment counters
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
                    (event) => event.type & CASE_EVENT_TYPES.assertion.value && !event.pass
                );
                if (failedAssertions.length) {
                    const s = failedAssertions.length === 1 ? "" : "s";
                    failReasons.push(
                        `\nFailed assertion${s}:`,
                        ...formatAssertions(failedAssertions)
                    );
                }
                if (lastResults.currentErrors.length) {
                    const s = lastResults.currentErrors.length === 1 ? "" : "s";
                    failReasons.push(
                        `\nError${s} during test:`,
                        ...lastResults.currentErrors.map((error) => `\n${error.message}`)
                    );
                }
                logger.logGlobalError(
                    [`Test ${stringify(test.fullName)} failed:`, ...failReasons].join("\n")
                );

                if (!this.aborted) {
                    if (this._failed === 1) {
                        // On first failed test: reset the "failed IDs" list
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

            // `stop` will be called again after test has been resolved.
            return false;
        }

        while (this._missedCallbacks.length) {
            await this._missedCallbacks.shift()();
        }

        await this._callbacks.call("after-all", this, logger.error);

        const { passed, failed, assertions } = this.reporting;
        if (failed > 0) {
            const errorMessage = ["Some tests failed: see above for details"];
            if (this.config.headless) {
                const ids = this.simplifyUrlIds({ test: this.state.failedIds });
                const link = createUrlFromId(ids, { debug: true });
                // Tweak parameters to make debugging easier
                link.searchParams.set("debug", "assets");
                link.searchParams.delete("headless");
                link.searchParams.delete("loglevel");
                link.searchParams.delete("timeout");
                errorMessage.push(`Failed tests link: ${link.toString()}`);
            }
            // Use console.dir for this log to appear on runbot sub-builds page
            logger.logGlobal(
                `failed ${failed} tests (${passed} passed, total time: ${this.totalTime})`
            );
            // Do not use logger to not apply the [HOOT] prefix and allow the CI
            // to stop the test run browser.
            $error(errorMessage.join("\n"));
        } else {
            // Use console.dir for this log to appear on runbot sub-builds page
            logger.logGlobal(
                `passed ${passed} tests (${assertions} assertions, total time: ${this.totalTime})`
            );
            // This statement acts as a success code for the server to know when
            // all suites have passed.
            logger.logRun("test suite succeeded");
        }

        return false;
    }

    /**
     * Enriches the given function with test modifiers, which are:
     * - `debug`: only run in debug mode
     * - `only`: only run this test/suite
     * - `skip`: skip this test/suite
     * - `todo`: mark this test/suite as todo
     * - `tags`: add tags to this test/suite
     *
     * @template {(...args: any[]) => any} T
     * @template {false | () => Job} C
     * @param {T} fn
     * @param {C} getCurrent
     * @returns {typeof configurableFn}
     */
    _addConfigurators(fn, getCurrent) {
        /**
         * @typedef {((...args: DropFirst<Parameters<T>>) => Configurators) & Configurators} ConfigurableFunction
         *
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

        // GETTER MODIFIERS

        /** @type {Configurators["current"]} */
        const current = getCurrent && (() => this._createCurrentConfigurators(getCurrent));

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

        // FUNCTION MODIFIERS

        /**
         * Modifies the current test/suite configuration.
         *
         * - `timeout`: sets the timeout for the current test/suite;
         * - `multi`: sets the number of times the current test/suite will be run.
         *
         * @type {Configurators["config"]}
         * @example
         *  // Will timeout each of its tests after 10 seconds
         *  describe.config({ timeout: 10_000 });
         *  describe("Expensive tests", () => { ... });
         * @example
         *  // Will be run 100 times
         *  test.config({ multi: 100 });
         *  test("non-deterministic test", async () => { ... });
         */
        function config(...configs) {
            $assign(currentConfig, ...configs);
            return configurators;
        }

        /** @type {Configurators["multi"]} */
        function multi(count) {
            currentConfig.multi = count;
            return configurators;
        }

        /**
         * Adds tags to the current test/suite.
         *
         * Tags can be a string, a list of strings, or a spread of strings.
         *
         * @type {Configurators["tags"]}
         * @example
         *  // Will be tagged with "desktop" and "ui"
         *  test.tags("desktop", "ui");
         *  test("my test", () => { ... });
         * @example
         *  test.tags("mobile");
         *  test("my mobile test", () => { ... });
         */
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

        const properties = {};
        for (const [key, getter] of $entries(configuratorGetters)) {
            properties[key] = { get: getter };
        }
        for (const [key, getter] of $entries(configuratorMethods)) {
            properties[key] = { value: getter };
        }

        /** @type {{ tags: Tag[], [key: string]: any }} */
        let currentConfig = { tags: [] };
        return $defineProperties(configurableFn, properties);
    }

    /**
     * @param {Job} job
     */
    _applyTagModifiers(job) {
        let shouldSkip = false;
        let [ignoreSkip] = this._getExplicitIncludeStatus(job);
        for (const tag of job.tags) {
            this.tags.set(tag.id, tag);
            switch (tag.name) {
                case Tag.DEBUG:
                    if (typeof this.debug !== "boolean" && this.debug !== job) {
                        throw new HootError(
                            `cannot set multiple tests or suites as "debug" at the same time`
                        );
                    }
                    this.debug = job;
                // Falls through
                case Tag.ONLY:
                    if (!this.dry) {
                        logger.logGlobalWarning(
                            `${stringify(job.fullName)} is marked as ${stringify(
                                tag.name
                            )}. This is not suitable for CI`
                        );
                    }
                    this._include(
                        this.state.includeSpecs[job instanceof Suite ? "suite" : "test"],
                        [job.id],
                        INCLUDE_LEVEL.tag
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
                logger.logGlobalWarning(
                    `${stringify(
                        job.fullName
                    )} is marked as skipped but explicitly included: "skip" modifier has been ignored`
                );
            } else {
                job.config.skip = true;
            }
        }
    }

    /**
     * @param {() => Job} getCurrent
     */
    _createCurrentConfigurators(getCurrent) {
        /**
         * @param {JobConfig} config
         */
        function configureCurrent(config) {
            getCurrent().configure(config);

            return currentConfigurators;
        }

        /**
         * @param  {...string} tagNames
         */
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
     * Executes a given callback when not in debug mode.
     * @param {() => Promise<void>} callback
     */
    async _execAfterCallback(callback) {
        if (this.debug) {
            this._missedCallbacks.push(callback);
        } else {
            await callback();
        }
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

    /**
     * @param {Job} job
     */
    _getExplicitIncludeStatus(job) {
        const includeSpec =
            job instanceof Suite ? this.state.includeSpecs.suite : this.state.includeSpecs.test;
        const explicitInclude = includeSpec[job.id] || 0;
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
            let nId = normalize(id.toLowerCase());
            if (nId.startsWith(EXCLUDE_PREFIX)) {
                nId = nId.slice(EXCLUDE_PREFIX.length);
                if (includeLevel > 0) {
                    includeLevel *= -1;
                }
            }
            const previousValue = values[nId] || 0;
            const wasRemovable = $abs(previousValue) === INCLUDE_LEVEL.url;
            if (wasRemovable) {
                applied++;
            }
            if (shouldInclude) {
                if (previousValue === includeLevel) {
                    continue;
                }
                values[nId] = includeLevel;
                if (noIncrement) {
                    continue;
                }
                if (previousValue <= 0 && includeLevel > 0) {
                    this._hasIncludeFilter++;
                } else if (previousValue > 0 && includeLevel <= 0) {
                    this._hasIncludeFilter--;
                }
                if (!wasRemovable && isRemovable) {
                    this._hasRemovableFilter++;
                } else if (wasRemovable && !isRemovable) {
                    this._hasRemovableFilter--;
                }
            } else {
                delete values[nId];
                if (noIncrement) {
                    continue;
                }
                if (previousValue > 0) {
                    this._hasIncludeFilter--;
                }
                if (wasRemovable) {
                    this._hasRemovableFilter--;
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
        // By tag name
        for (const [tagName, status] of $entries(this.state.includeSpecs.tag)) {
            if (status < 0 && job.tags.some((tag) => tag.name === tagName)) {
                return true;
            }
        }

        // By text filter
        if (this.queryExclude.length && this.queryExclude.some((qp) => qp.matchValue(job.key))) {
            return true;
        }

        return false;
    }

    /**
     * @param {Job} job
     * @returns {boolean | null}
     */
    _isImplicitlyIncluded(job) {
        // By tag name
        for (const [tagName, status] of $entries(this.state.includeSpecs.tag)) {
            if (status > 0 && job.tags.some((tag) => tag.name === tagName)) {
                return true;
            }
        }

        // By text filter
        if (this.queryInclude.length && this.queryInclude.every((qp) => qp.matchValue(job.key))) {
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
     * @param {boolean} [implicitInclude] fallback include value for sub-jobs
     * @returns {Job[]}
     */
    _prepareJobs(jobs, implicitInclude = !this._hasIncludeFilter) {
        if (typeof this.debug !== "boolean") {
            // Special case: test (or suite with 1 test) with "debug" tag
            let debugTest = this.debug;
            while (debugTest instanceof Suite) {
                if (debugTest.jobs.length > 1) {
                    throw new HootError(
                        `cannot debug a suite with more than 1 job, got ${debugTest.jobs.length}`
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
            // Priority 1: explicit include or exclude (URL or special tag)
            const [explicitInclude, explicitExclude] = this._getExplicitIncludeStatus(job);
            if (explicitExclude) {
                return false;
            }

            // Priority 2: implicit exclude
            if (!explicitInclude && this._isImplicitlyExcluded(job)) {
                return false;
            }

            // Priority 3: implicit include
            let included = explicitInclude || implicitInclude || this._isImplicitlyIncluded(job);
            if (job instanceof Suite) {
                // For suites: included if at least 1 included job
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
            return;
        }
        this._prepared = true;

        if (this.config.preset) {
            const preset = this.presets[this.config.preset];
            if (!preset) {
                throw new HootError(`unknown preset: "${this.config.preset}"`);
            }
            if (preset.tags?.length) {
                this._include(this.state.includeSpecs.tag, preset.tags, INCLUDE_LEVEL.preset);
            }
            if (preset.platform) {
                mockUserAgent(preset.platform);
            }
            if (typeof preset.touch === "boolean") {
                this.beforeEach(() => mockTouch(preset.touch));
            }
            this.checkPresetForViewPort();
        }

        // Cleanup invalid IDs and tags from URL
        const hasChanged = this._simplifyIncludeSpecs(this.state.includeSpecs, {
            test: this.tests,
            suite: this.suites,
            tag: this.tags,
        });
        if (hasChanged) {
            this._updateConfigFromSpecs();
        }

        // Cleanup invalid tests from storage
        const failedIds = [...this.state.failedIds];
        const existingFailed = failedIds.filter((id) => this.tests.has(id));
        if (existingFailed.length !== failedIds.length) {
            this.state.failedIds = new Set(existingFailed);
            storageSet(STORAGE.failed, existingFailed);
        }

        // Check tags similarities
        const similarities = getTagSimilarities();
        if (similarities.length) {
            this._handleGlobalWarning(
                WARNINGS.tagNames + similarities.map((s) => `\n- ${s.map(stringify).join(" / ")}`)
            );
            logger.logGlobalWarning(WARNINGS.tagNames, similarities);
        }

        this._populateState = true;
        this._currentJobs = this._prepareJobs(this.rootSuites);
        this._populateState = false;

        if (!this.state.tests.length) {
            throw new HootError(`no tests to run`);
        }
    }

    /**
     * @param {Error | ErrorEvent | PromiseRejectionEvent} ev
     */
    _handleError(ev) {
        if (this.config.notrycatch) {
            return;
        }
        const error = ensureError(ev);
        if (handledErrors.has(error)) {
            // Already handled
            return safePrevent(ev);
        }
        handledErrors.add(error);

        if (!(ev instanceof Event)) {
            ev = new ErrorEvent("error", { error });
        }

        if (error.message.includes(RESIZE_OBSERVER_MESSAGE)) {
            // Stop event
            ev.stopImmediatePropagation();
            if (ev.bubbles) {
                ev.stopPropagation();
            }
            return safePrevent(ev);
        }

        if (this.state.currentTest && !(error instanceof HootError)) {
            // Handle the error in the current test
            const handled = this._handleErrorInTest(ev, error);
            if (handled) {
                return safePrevent(ev);
            }
        } else {
            this._handleGlobalError(ev, error);
        }

        // Prevent error event
        safePrevent(ev);

        // Log error
        logger.error(error);
    }

    /**
     * @param {ErrorEvent | PromiseRejectionEvent} ev
     * @param {Error} error
     */
    _handleErrorInTest(ev, error) {
        for (const callbackRegistry of this._getCallbackChain(this.state.currentTest)) {
            callbackRegistry.callSync("error", ev, logger.error);
            if (ev.defaultPrevented) {
                // Prevented in tests
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

    /**
     * @param {string} message
     */
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
            this._canStartPromise = new Deferred();
        }

        // Config log
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

        // Adjust debug mode if more or less than 1 test will be run
        if (this.debug) {
            const activeSingleTests = this.state.tests.filter(
                (test) => !test.config.skip && !test.config.multi
            );
            if (activeSingleTests.length !== 1) {
                logger.logGlobalWarning(
                    `Disabling debug mode: ${activeSingleTests.length} tests will be run`
                );
                this.config.debugTest = false;
                this.debug = false;
            } else {
                const nameSpace = exposeHelpers(hootDom, hootMock, {
                    destroy,
                    getFixture: this.fixture.get,
                });
                logger.setLevel("debug");
                logger.logDebug(
                    `Debug mode is active: Hoot helpers available from \`window.${nameSpace}\``
                );
            }
        }

        // Register default hooks
        this.beforeAll(this.fixture.globalSetup);
        this.afterAll(
            this.fixture.globalCleanup,
            // Warn user events
            !this.debug && on(window, "pointermove", warnUserEvent),
            !this.debug && on(window, "pointerdown", warnUserEvent),
            !this.debug && on(window, "keydown", warnUserEvent)
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
            cleanupTime
        );

        enableEventLogs(logger.allows("debug"));
        setFrameRate(this.config.fps);

        await this._callbacks.call("before-all", this, logger.error);
    }

    /**
     * @param {Runner["state"]["includeSpecs"]} includeSpecs
     * @param {Partial<Record<keyof includeSpecs, Map<string, Job>>>} valuesMaps
     */
    _simplifyIncludeSpecs(includeSpecs, valuesMaps) {
        let hasChanged = false;
        const ignored = [];
        const removed = [];
        for (const [configKey, valuesMap] of $entries(valuesMaps)) {
            const specs = includeSpecs[configKey];
            let remaining = $keys(specs);
            while (remaining.length) {
                const id = remaining.shift();
                if (specs[id] !== INCLUDE_LEVEL.url) {
                    continue;
                }
                const item = valuesMap.get(id);
                if (!item) {
                    const applied = this._include(specs, [id], 0, true);
                    if (applied) {
                        removed.push(`\n- ${configKey} "${id}"`);
                    } else {
                        ignored.push(`\n- ${configKey} "${id}"`);
                    }
                    hasChanged = true;
                }
                if (!item?.parent || item.parent.jobs.length < 1) {
                    // No parent or no need to simplify
                    continue;
                }
                const siblingIds = item.parent.jobs.map((job) => job.id);
                if (
                    siblingIds.every(
                        (siblingId) => siblingId === id || remaining.includes(siblingId)
                    )
                ) {
                    remaining = remaining.filter((id) => !siblingIds.includes(id));
                    this._include(includeSpecs.suite, [item.parent.id], INCLUDE_LEVEL.url, true);
                    this._include(specs, siblingIds, 0, true);
                    hasChanged = true;
                }
            }
        }
        if (removed.length) {
            logger.warn(
                `The following IDs were not found and and have been removed from URL filters:`,
                ...removed
            );
        }
        if (ignored.length) {
            logger.warn(`The following IDs were not found and and have been ignored:`, ...ignored);
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
