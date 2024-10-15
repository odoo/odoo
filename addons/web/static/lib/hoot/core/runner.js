/** @odoo-module */

import { Deferred, on, setFrameRate } from "@odoo/hoot-dom";
import { markRaw, reactive, toRaw } from "@odoo/owl";
import { cleanupDOM } from "@web/../lib/hoot-dom/helpers/dom";
import { enableEventLogs } from "@web/../lib/hoot-dom/helpers/events";
import { cleanupTime } from "@web/../lib/hoot-dom/helpers/time";
import { isIterable, parseRegExp } from "@web/../lib/hoot-dom/hoot_dom_utils";
import {
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
    formatTechnical,
    formatTime,
    getFuzzyScore,
    normalize,
    storageGet,
    storageSet,
    stringify,
} from "../hoot_utils";
import { cleanupDate } from "../mock/date";
import { internalRandom } from "../mock/math";
import { cleanupNavigator, mockUserAgent } from "../mock/navigator";
import { cleanupNetwork } from "../mock/network";
import { cleanupWindow, getViewPortHeight, getViewPortWidth, mockTouch } from "../mock/window";
import { DEFAULT_CONFIG, FILTER_KEYS } from "./config";
import { makeExpect } from "./expect";
import { makeFixtureManager } from "./fixture";
import { logLevels, logger } from "./logger";
import { Suite, suiteError } from "./suite";
import { Tag } from "./tag";
import { Test, testError } from "./test";
import { EXCLUDE_PREFIX, createUrlFromId, setParams, urlParams } from "./url";

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
 */

/**
 * @template T
 * @typedef {(payload: T) => MaybePromise<any>} Callback
 */

/**
 * @template {unknown[]} T
 * @typedef {T extends [any, ...infer U] ? U : never} DropFirst
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
    console: { groupEnd: $groupEnd, log: $log, table: $table },
    EventTarget,
    Map,
    Math: { floor: $floor },
    Object: {
        assign: $assign,
        defineProperties: $defineProperties,
        entries: $entries,
        freeze: $freeze,
        fromEntries: $fromEntries,
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
const filterReady = (jobs) =>
    jobs.filter((job) => {
        if (job instanceof Suite) {
            job.setCurrentJobs(filterReady(job.currentJobs));
            return job.currentJobs.length;
        }
        return job.run;
    });

/**
 * @param {import("./expect").Assertion[]} assertions
 */
const formatAssertions = (assertions) => {
    const lines = [];
    for (let i = 0; i < assertions.length; i++) {
        const { failedDetails, label, message } = assertions[i];
        lines.push(`\n${i + 1}. [${label}] ${message}`);
        if (failedDetails) {
            for (let [key, value] of failedDetails) {
                if (Markup.isMarkup(key)) {
                    key = key.content;
                }
                if (Markup.isMarkup(value)) {
                    if (value.technical) {
                        continue;
                    }
                    value = value.content;
                }
                lines.push(`> ${key} ${formatTechnical(value)}`);
            }
        }
    }
    return lines;
};

/**
 * @returns {Map<string, Preset>}
 */
const getDefaultPresets = () =>
    new Map([
        [
            "",
            {
                label: "No preset",
            },
        ],
        [
            "desktop",
            {
                icon: "fa-desktop",
                label: "Desktop",
                platform: "linux",
                size: [1366, 768],
                tags: ["-mobile"],
                touch: false,
            },
        ],
        [
            "mobile",
            {
                icon: "fa-mobile",
                label: "Mobile",
                platform: "android",
                size: [375, 667],
                tags: ["-desktop"],
                touch: true,
            },
        ],
    ]);

const noop = () => {};

/**
 * @param {Event} ev
 */
const safePrevent = (ev) => ev.cancelable && ev.preventDefault();

/**
 * @template T
 * @param {T[]} array
 */
const shuffle = (array) => {
    const copy = [...array];
    let randIndex;
    for (let i = 0; i < copy.length; i++) {
        randIndex = $floor(internalRandom() * copy.length);
        [copy[i], copy[randIndex]] = [copy[randIndex], copy[i]];
    }
    return copy;
};

/**
 * @param {Test} test
 * @param {boolean} shouldSuppress
 */
const handleConsoleIssues = (test, shouldSuppress) => {
    if (shouldSuppress && test.config.todo) {
        const restoreConsole = () => $assign(globalThis.console, originalMethods);

        /**
         * @param {string} label
         * @param {string} color
         */
        const suppressIssueLogger = (label, color) => {
            const groupName = [`%c[${label}]%c suppressed by "test.todo"`, `color: ${color}`, ""];
            return (...args) => {
                logger.groupCollapsed(...groupName);
                $log(...args);
                $groupEnd();
            };
        };

        const originalMethods = {
            error: globalThis.console.error,
            warn: globalThis.console.warn,
        };
        $assign(globalThis.console, {
            error: suppressIssueLogger("ERROR", "#9f1239"),
            warn: suppressIssueLogger("WARNING", "#f59e0b"),
        });

        return restoreConsole;
    } else {
        const offConsoleEvents = () => {
            while (cleanups.length) {
                cleanups.pop()();
            }
        };

        const cleanups = [];
        if (globalThis.console instanceof EventTarget) {
            cleanups.push(
                on(globalThis.console, "error", () => test.logs.error++),
                on(globalThis.console, "warn", () => test.logs.warn++)
            );
        }

        return offConsoleEvents;
    }
};

/**
 * @param {Event} ev
 */
const warnUserEvent = (ev) => {
    if (!ev.isTrusted) {
        return;
    }

    logger.warn(
        `User event detected: "${ev.type}"\n\n`,
        `This kind of interaction can interfere with the current test and should be avoided.`
    );

    removeEventListener(ev.type, warnUserEvent);
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
    presets = reactive(getDefaultPresets());
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
         * @type {{
         *  suites: Record<string, number>;
         *  tags: Record<string, number>;
         *  tests: Record<string, number>;
         * }}
         */
        includeSpecs: {
            suites: {},
            tags: {},
            tests: {},
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
    /** @type {string | RegExp} */
    textFilter = "";
    totalTime = "n/a";

    /**
     * @type {boolean}
     */
    get hasFilter() {
        return this._hasRemovableFilter;
    }

    // Private properties
    _callbacks = new Callbacks();
    /** @type {Job[]} */
    _currentJobs = [];
    _failed = 0;
    _hasRemovableFilter = false;
    _hasIncludeFilter = false;
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

    /** @type {(reason?: any) => any} */
    _rejectCurrent = noop;
    /** @type {(value?: any) => any} */
    _resolveCurrent = noop;

    /**
     * @param {typeof DEFAULT_CONFIG} [config]
     */
    constructor(config) {
        // Main test methods
        this.describe = this._addConfigurators(this.addSuite, () => this.suiteStack.at(-1));
        this.fixture = makeFixtureManager(this);
        this.test = this._addConfigurators(this.addTest, false);

        const initialConfig = { ...DEFAULT_CONFIG, ...config };
        const reactiveConfig = reactive({ ...initialConfig, ...urlParams }, () => {
            setParams(
                $fromEntries(
                    $entries(this.config).map(([key, value]) => [
                        key,
                        deepEqual(value, initialConfig[key]) ? null : value,
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
            this._hasIncludeFilter = true;
            this.textFilter = parseRegExp(normalize(this.config.filter), { safe: true });
        }

        // Suites
        if (this.config.suite?.length) {
            this._include("suites", this.config.suite);
        }

        // Tags
        if (this.config.tag?.length) {
            this._include("tags", this.config.tag);
        }

        // Tests
        if (this.config.test?.length) {
            this._include("tests", this.config.test);
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

        let result;
        try {
            result = fn();
        } finally {
            this.suiteStack.pop();
        }
        if (result !== undefined) {
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
        const preset = this.presets.get(presetId);
        if (!preset.size) {
            return true;
        }
        const innerWidth = getViewPortWidth();
        const innerHeight = getViewPortHeight();
        const [width, height] = preset.size;
        if (width !== innerWidth || height !== innerHeight) {
            if (lastPresetWarn !== presetId) {
                this._handleGlobalWarning(
                    "viewport size does not match the expected size for the current preset"
                );
                logger.warn(
                    `viewport size does not match the expected size for the "${preset.label}" preset`,
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
     * @param {string} name
     * @param {Preset} preset
     */
    registerPreset(name, preset) {
        this.presets.set(name, preset);
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
        const handleError = !this.config.notrycatch && this._handleError.bind(this);

        /**
         * @param {Job} [job]
         */
        const nextJob = (job) => {
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
        };

        let job = nextJob();
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

                        suite.runCount++;
                        if (suite.config.multi && suite.runCount < suite.config.multi) {
                            suite.resetIndex();
                        }
                        suite.parent?.reporting.add({ suites: +1 });
                        suite.callbacks.clear();

                        logger.logSuite(suite);
                    }
                }
                job = nextJob(job);
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
                job = nextJob(job);
                continue;
            }

            // Suppress console errors and warnings if test is in "todo" mode
            // (and not in debug).
            const restoreConsole = handleConsoleIssues(test, !this.debug);

            // Before test
            this.state.currentTest = test;
            this.expectHooks.before(test);
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
                this._rejectCurrent = reject;
                this._resolveCurrent = resolve;

                if (timeout && !this.debug) {
                    // Set timeout
                    timeoutId = setTimeout(
                        () => reject(new HootError(`test timed out after ${timeout} milliseconds`)),
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
                    this._rejectCurrent = noop; // prevents loop

                    if (handleError) {
                        return handleError(error);
                    } else {
                        throw error;
                    }
                })
                .finally(() => {
                    this._rejectCurrent = noop;
                    this._resolveCurrent = noop;

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

            restoreConsole();

            // Log test errors and increment counters
            this.expectHooks.after(this);
            test.runCount++;
            if (lastResults.pass) {
                logger.logTest(test);

                if (this.state.failedIds.has(test.id)) {
                    this.state.failedIds.delete(test.id);
                    storageSet(STORAGE.failed, [...this.state.failedIds]);
                }
            } else {
                const failReasons = [];
                const failedAssertions = lastResults.assertions.filter(
                    (assertion) => !assertion.pass
                );
                if (failedAssertions.length) {
                    const s = failedAssertions.length === 1 ? "" : "s";
                    failReasons.push(
                        `\nFailed assertion${s}:`,
                        ...formatAssertions(failedAssertions)
                    );
                }
                if (lastResults.errors.length) {
                    const s = lastResults.errors.length === 1 ? "" : "s";
                    failReasons.push(
                        `\nError${s} during test:`,
                        ...lastResults.errors.map((e) => `\n${e.message}`)
                    );
                }
                logger.error(
                    [`Test ${stringify(test.fullName)} failed:`, ...failReasons].join("\n")
                );

                this.state.failedIds.add(test.id);
                storageSet(STORAGE.failed, [...this.state.failedIds]);
            }

            await this._callbacks.call("after-post-test", test, handleError);

            if (this.config.bail) {
                if (!test.config.skip && !lastResults.pass) {
                    this._failed++;
                }
                if (this._failed >= this.config.bail) {
                    return this.stop();
                }
            }
            this._pushTest(test);
            if (test.willRunAgain()) {
                test.run = test.run.bind(test);
            } else {
                if (this.debug) {
                    return new Promise(() => {});
                }
                test.setRunFn(null);
                job = nextJob(job);
            }
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
        this.totalTime = formatTime($now() - this._startTime);

        if (this._resolveCurrent !== noop) {
            this._resolveCurrent();
            return false;
        }

        while (this._missedCallbacks.length) {
            await this._missedCallbacks.shift()();
        }

        await this._callbacks.call("after-all", logger.error);

        const { passed, failed, assertions } = this.reporting;
        if (failed > 0) {
            const link = createUrlFromId(this.state.failedIds, "test");
            // Use console.dir for this log to appear on runbot sub-builds page
            logger.logGlobal(
                `failed ${failed} tests (${passed} passed, total time: ${this.totalTime})`
            );
            logger.error("test failed (see above for details)");
            logger.error("failed tests link:", link.toString());
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
     * @returns {typeof taggedFn}
     */
    _addConfigurators(fn, getCurrent) {
        /**
         * @typedef {((...args: DropFirst<Parameters<T>>) => ConfigurableFunction) & {
         *  readonly config: typeof configure;
         *  readonly current: C extends false ? never : CurrentConfigurators;
         *  readonly debug: typeof taggedFn;
         *  readonly multi: (count: number) => typeof taggedFn;
         *  readonly only: typeof taggedFn;
         *  readonly skip: typeof taggedFn;
         *  readonly tags: typeof addTags;
         *  readonly todo: typeof taggedFn;
         *  readonly timeout: (ms: number) => typeof taggedFn;
         * }} ConfigurableFunction
         */

        /**
         * Adds tags to the current test/suite.
         *
         * Tags can be a string, a list of strings, or a spread of strings.
         *
         * @param  {...(string | Iterable<string>)} tags
         * @returns {ConfigurableFunction}
         * @example
         *  // Will be tagged with "desktop" and "ui"
         *  test.tags("desktop", "ui")("my test", () => { ... });
         *  test.tags(["desktop", "ui"])("my test", () => { ... });
         * @example
         *  test.tags`mobile,ui`("my mobile test", () => { ... });
         */
        const addTags = (...tags) => {
            if (tags[0]?.raw) {
                tags = String.raw(...tags).split(/\s*,\s*/g);
            }

            currentConfig.tags.push(...tags.flatMap(ensureArray));

            return taggedFn;
        };

        /**
         * Modifies the current test/suite configuration.
         *
         * - `timeout`: sets the timeout for the current test/suite;
         * - `multi`: sets the number of times the current test/suite will be run.
         *
         * @param  {...JobConfig} configs
         * @returns {ConfigurableFunction}
         * @example
         *  // Will timeout each of its tests after 10 seconds
         *  describe.config({ timeout: 10_000 })("Expensive tests", () => { ... });
         * @example
         *  // Will be run 100 times
         *  test.config({ multi: 100 })("non-deterministic test", async () => { ... });
         */
        const configure = (...configs) => {
            $assign(currentConfig, ...configs);

            return taggedFn;
        };

        /** @type {ConfigurableFunction} */
        const taggedFn = (...args) => {
            const jobConfig = { ...currentConfig };
            currentConfig = { tags: [] };
            return fn.call(this, jobConfig, ...args);
        };

        let currentConfig = { tags: [] };
        $defineProperties(taggedFn, {
            config: { get: configure },
            debug: { get: () => addTags("debug") },
            multi: { get: () => (count) => configure({ multi: count }) },
            only: { get: () => addTags("only") },
            skip: { get: () => addTags("skip") },
            tags: { get: () => addTags },
            timeout: { get: () => (ms) => configure({ timeout: ms }) },
            todo: { get: () => addTags("todo") },
        });

        if (getCurrent) {
            $defineProperties(taggedFn, {
                current: { get: () => this._createCurrentConfigurators(getCurrent) },
            });
        }

        return taggedFn;
    }

    /**
     * @param {Job} job
     */
    _applyTagModifiers(job) {
        let shouldSkip = false;
        let [ignoreSkip] = this._getExplicitIncludeStatus(job);
        for (const tag of job.tags) {
            this.tags.set(tag.name, tag);
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
                        logger.warn(
                            `${stringify(job.fullName)} is marked as ${stringify(
                                tag.name
                            )}. This is not suitable for CI`
                        );
                    }
                    this._include(
                        job instanceof Suite ? "suites" : "tests",
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
                logger.warn(
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
     * @param {keyof Runner["config"]} configKey
     * @param {keyof Runner["state"]["includeSpecs"]} specKey
     * @param {Map<string, any>} valuesMap
     */
    _checkUrlValidity(configKey, specKey, valuesMap) {
        const values = this.state.includeSpecs[specKey];
        const availableValues = new Set(valuesMap.keys());
        for (const [key, incLevel] of Object.entries(values)) {
            if (Math.abs(incLevel) === INCLUDE_LEVEL.url && !availableValues.has(key)) {
                delete values[key];
                this.config[configKey] = this.config[configKey].filter((val) => key !== val);
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
        const configureCurrent = (config) => {
            getCurrent().configure(config);

            return currentConfigurators;
        };

        /**
         * @param  {...string} tags
         */
        const addTagsToCurrent = (...tags) => {
            const current = getCurrent();
            current.configure({ tags });
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
            job instanceof Suite ? this.state.includeSpecs.suites : this.state.includeSpecs.tests;
        const explicitInclude = includeSpec[job.id] || 0;
        return [explicitInclude > 0, explicitInclude < 0];
    }

    /**
     * @param {"suites" | "tags" | "tests"} type
     * @param {Iterable<string>} ids
     * @param {number} [priority=1]
     */
    _include(type, ids, priority = INCLUDE_LEVEL.url) {
        priority = Math.abs(priority);
        if (priority === INCLUDE_LEVEL.url) {
            this._hasRemovableFilter = true;
        }
        const values = this.state.includeSpecs[type];
        for (const id of ids) {
            const nId = normalize(id);
            if (id.startsWith(EXCLUDE_PREFIX)) {
                values[nId.slice(EXCLUDE_PREFIX.length)] = priority * -1;
            } else if ((values[nId]?.[0] || 0) >= 0) {
                this._hasIncludeFilter = true;
                values[nId] = priority;
            }
        }
    }

    /**
     * @param {Job} job
     * @returns {boolean | null}
     */
    _isImplicitlyExcluded(job) {
        // By tag name
        for (const [tagName, status] of $entries(this.state.includeSpecs.tags)) {
            if (status < 0 && job.tags.some((tag) => tag.name === tagName)) {
                return true;
            }
        }

        // By text filter
        if (typeof this.textFilter === "string" && this.textFilter?.startsWith(EXCLUDE_PREFIX)) {
            const query = this.textFilter.slice(EXCLUDE_PREFIX.length);
            return getFuzzyScore(query, job.key) > 0;
        }

        return false;
    }

    /**
     * @param {Job} job
     * @returns {boolean | null}
     */
    _isImplicitlyIncluded(job) {
        // By tag name
        for (const [tagName, status] of $entries(this.state.includeSpecs.tags)) {
            if (status > 0 && job.tags.some((tag) => tag.name === tagName)) {
                return true;
            }
        }

        // By text filter
        if (this.textFilter) {
            if (this.textFilter instanceof RegExp) {
                return this.textFilter.test(job.key);
            } else {
                return getFuzzyScore(this.textFilter, job.key) > 0;
            }
        }

        return false;
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
            const preset = this.presets.get(this.config.preset);
            if (!preset) {
                throw new HootError(`unknown preset: "${this.config.preset}"`);
            }
            if (preset.tags?.length) {
                this._include("tags", preset.tags, INCLUDE_LEVEL.preset);
            }
            if (preset.platform) {
                mockUserAgent(preset.platform);
            }
            if (typeof preset.touch === "boolean") {
                mockTouch(preset.touch);
            }
            this.checkPresetForViewPort();
        }

        // Cleanup invalid IDs and tags from URL
        if (this.config.suite) {
            this._checkUrlValidity("suite", "suites", this.suites);
        }
        if (this.config.tag) {
            this._checkUrlValidity("tag", "tags", this.tags);
        }
        if (this.config.test) {
            this._checkUrlValidity("test", "tests", this.tests);
        }

        // Cleanup invalid tests from storage
        const failedIds = [...this.state.failedIds];
        const existingFailed = failedIds.filter((id) => this.tests.has(id));
        if (existingFailed.length !== failedIds.length) {
            this.state.failedIds = new Set(existingFailed);
            storageSet(STORAGE.failed, existingFailed);
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
        const error = ensureError(ev);
        if (this.config.notrycatch || handledErrors.has(error)) {
            // Already handled
            return;
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

        if (this.state.currentTest) {
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

        const { lastResults } = this.state.currentTest;
        if (!lastResults) {
            return false;
        }

        lastResults.errors.push(error);
        lastResults.caughtErrors++;
        if (lastResults.expectedErrors >= lastResults.caughtErrors) {
            return true;
        }

        this._rejectCurrent(error);
        return false;
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
                name: "warning",
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
        logger.groupCollapsed("Configuration (click to expand)");
        $table(table);
        $groupEnd();
        logger.logRun("Starting test suites");

        // Adjust debug mode if more or less than 1 test will be run
        if (this.debug) {
            const activeSingleTests = this.state.tests.filter(
                (test) => !test.config.skip && !test.config.multi
            );
            if (activeSingleTests.length !== 1) {
                logger.warn(`disabling debug mode: ${activeSingleTests.length} tests will be run`);
                this.config.debugTest = false;
                this.debug = false;
            }
        }

        // Register default hooks
        this.afterAll(
            // Warn user events
            !this.debug && on(window, "pointermove", warnUserEvent),
            !this.debug && on(window, "pointerdown", warnUserEvent),
            !this.debug && on(window, "keydown", warnUserEvent)
        );
        this.beforeEach(this.fixture.setup);
        this.afterEach(
            cleanupWindow,
            cleanupNetwork,
            cleanupNavigator,
            this.fixture.cleanup,
            cleanupDOM,
            cleanupTime,
            cleanupDate
        );

        if (this.debug) {
            logger.level = logLevels.DEBUG;
        }
        enableEventLogs(this.debug);
        setFrameRate(this.config.fps);

        await this._callbacks.call("before-all", logger.error);
    }
}
