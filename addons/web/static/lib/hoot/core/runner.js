/** @odoo-module */
/* eslint-disable no-restricted-syntax */

import { markRaw, reactive, toRaw, whenReady } from "@odoo/owl";
import { cleanupDOM, watchKeys } from "@web/../lib/hoot-dom/helpers/dom";
import { enableEventLogs, on } from "@web/../lib/hoot-dom/helpers/events";
import { isIterable, parseRegExp } from "@web/../lib/hoot-dom/hoot_dom_utils";
import {
    HootError,
    Markup,
    batch,
    createReporting,
    deepEqual,
    ensureArray,
    ensureError,
    formatTechnical,
    formatTime,
    getFuzzyScore,
    makeCallbacks,
    normalize,
} from "../hoot_utils";
import { MockMath, internalRandom } from "../mock/math";
import { cleanupNavigator, mockUserAgent } from "../mock/navigator";
import { cleanupTime, setFrameRate } from "../mock/time";
import { cleanupWindow, mockTouch, watchListeners } from "../mock/window";
import { DEFAULT_CONFIG, FILTER_KEYS } from "./config";
import { makeExpect } from "./expect";
import { makeFixtureManager } from "./fixture";
import { logLevels, logger } from "./logger";
import { Suite, suiteError } from "./suite";
import { Tag } from "./tag";
import { Test, testError } from "./test";
import { EXCLUDE_PREFIX, setParams, urlParams } from "./url";

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
 * @typedef {Suite | Test} Job
 *
 * @typedef {import("./job").JobConfig} JobConfig
 *
 * @typedef {{
 *  icon?: string;
 *  label: string;
 *  platform?: import("../mock/navigator").Platform;
 *  tags?: string[];
 *  touch?: boolean;
 * }} Preset
 *
 * @typedef {{
 *  auto?: boolean;
 * }} StartOptions
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
    console: { warn: $warn, error: $error },
    document,
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
 * @param {import("./expect").Assertion[]} assertions
 */
const formatAssertions = (assertions) => {
    const lines = [];
    for (let i = 0; i < assertions.length; i++) {
        const { info, label, message, pass } = assertions[i];
        if (pass) {
            continue;
        }
        lines.push(`\n${i + 1}. [${label}] ${message}`);
        if (info) {
            for (let [key, value] of info) {
                if (key instanceof Markup) {
                    key = key.content;
                }
                if (value instanceof Markup) {
                    if (value.technical) {
                        continue;
                    }
                    value = value.content;
                }
                lines.push(`> ${key} ${formatTechnical(value)}`);
            }
        }
    }
    return lines.join("\n");
};

/**
 * @returns {Map<Job, Preset>}
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
                tags: ["-desktop"],
                touch: true,
            },
        ],
    ]);

const noop = () => {};

const restoreConsole = () => {
    logger.ignoreErrors = false;

    $assign(globalThis.console, ORINAL_CONSOLE_METHODS);
};

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
 * @param {string} reason
 */
const suppressConsoleErrors = (reason) => {
    /**
     * @param {string} label
     * @param {string} color
     */
    const suppressedMethod = (label, color) => {
        const groupName = [`%c[${label}]%c suppressed by ${reason}`, `color: ${color}`, ""];
        return (...args) => {
            logger.group(...groupName);
            logger.log(...args);
            logger.groupEnd(...groupName);
        };
    };

    logger.ignoreErrors = true;

    $assign(globalThis.console, {
        error: suppressedMethod("ERROR", "#9f1239"),
        warn: suppressedMethod("WARNING", "#f59e0b"),
    });
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
        `Note that this kind of interaction can interfere with the current test and should be avoided.`
    );

    removeEventListener(ev.type, warnUserEvent);
};

const ORINAL_CONSOLE_METHODS = {
    error: $error,
    warn: $warn,
};

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export class TestRunner {
    // Properties
    aborted = false;
    /** @type {boolean | Test | Suite} */
    debug = false;
    /** @type {ReturnType<typeof makeExpect>[0]} */
    expect;
    /** @type {ReturnType<typeof makeExpect>[1]} */
    expectHooks;
    presets = reactive(getDefaultPresets());
    /** @type {Suite[]} */
    rootSuites = [];
    /** @type {Map<string, Suite>} */
    suites = new Map();
    /** @type {Set<Tag>} */
    tags = new Set();
    /** @type {Map<string, Test>} */
    tests = new Map();
    /** @type {string | RegExp} */
    textFilter = "";
    totalTime = "n/a";

    reporting = createReporting();
    state = reactive({
        /** @type {Test | null} */
        currentTest: null,
        /**
         * List of tests that have been run
         * @type {Test[]}
         */
        done: [],
        /**
         * Dictionnary containing whether a job is included or excluded from the
         * current run.
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
         * List of suites that will be run (only available after {@link TestRunner.start})
         * @type {Suite[]}
         */
        suites: [],
        /**
         * List of tests that will be run (only available after {@link TestRunner.start})
         * @type {Test[]}
         */
        tests: [],
    });

    /**
     * @type {boolean}
     */
    get hasFilter() {
        return this.#hasExcludeFilter || this.#hasIncludeFilter;
    }

    // Private properties
    #callbacks = makeCallbacks();
    /** @type {Job[]} */
    #currentJobs = [];
    #dry = false;
    #failed = 0;
    #hasExcludeFilter = false;
    #hasIncludeFilter = false;
    /** @type {(() => MaybePromise<void>)[]} */
    #missedCallbacks = [];
    #prepared = false;
    /** @type {Suite[]} */
    #suiteStack = [];
    #startTime = 0;

    /** @type {(reason?: any) => any} */
    #rejectCurrent = noop;
    /** @type {(value?: any) => any} */
    #resolveCurrent = noop;

    /**
     * @param {typeof DEFAULT_CONFIG} [config]
     */
    constructor(config) {
        // Main test methods
        this.describe = this.#addConfigurators(this.addSuite, () => this.#suiteStack.at(-1));
        this.fixture = makeFixtureManager(this);
        this.test = this.#addConfigurators(this.addTest, false);

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

        [this.expect, this.expectHooks] = makeExpect({
            get headless() {
                return reactiveConfig.headless;
            },
        });

        this.config = reactiveConfig;

        // Debug
        this.debug = Boolean(this.config.debugTest);

        // Text filter
        if (this.config.filter) {
            this.#hasIncludeFilter = true;
            this.textFilter = parseRegExp(normalize(this.config.filter));
        }

        // Suites
        if (this.config.suite?.length) {
            this.#include("suites", this.config.suite);
        }

        // Tags
        if (this.config.tag?.length) {
            this.#include("tags", this.config.tag);
        }

        // Tests
        if (this.config.test?.length) {
            this.#include("tests", this.config.test);
        }

        // Random seed
        if (this.config.random) {
            internalRandom.seed = this.config.random;
            MockMath.random.seed = this.config.random;
        }
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
            this.addSuite([], suiteName, () => this.addSuite(config, otherNames, fn));
            return;
        }
        const parentSuite = this.#suiteStack.at(-1);
        if (typeof fn !== "function") {
            throw suiteError(
                { name: suiteName, parent: parentSuite },
                `expected second argument to be a function and got ${String(fn)}`
            );
        }
        if (this.state.status !== "ready") {
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
                parentSuite.jobs.push(suite);
                suite.reporting = createReporting(parentSuite.reporting);
            } else {
                this.rootSuites.push(suite);
                suite.reporting = createReporting(this.reporting);
            }
        }
        this.#suiteStack.push(suite);

        this.#applyTagModifiers(suite);

        let result;
        try {
            result = fn();
        } finally {
            this.#suiteStack.pop();
        }
        if (result !== undefined) {
            throw suiteError(
                { name: suiteName, parent: parentSuite },
                `the suite function cannot return a value`
            );
        }
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
        const parentSuite = this.#suiteStack.at(-1);
        if (!parentSuite) {
            throw testError({ name, parent: null }, `cannot register a test outside of a suite.`);
        }
        if (typeof fn !== "function") {
            throw testError(
                { name, parent: parentSuite },
                `expected second argument to be a function and got ${String(fn)}`
            );
        }
        if (this.state.status !== "ready") {
            throw testError(
                { name, parent: parentSuite },
                `cannot add a test after the test runner started.`
            );
        }
        if (this.#dry) {
            fn = null;
        }
        let test = markRaw(new Test(parentSuite, name, config, fn));
        const originalTest = this.tests.get(test.id);
        if (originalTest) {
            if (originalTest.runFn === null) {
                test = originalTest;
                test.setRunFn(fn);
            } else {
                throw testError(
                    { name, parent: parentSuite },
                    `a test with that name already exists in the suite "${parentSuite.name}"`
                );
            }
        } else {
            parentSuite.jobs.push(test);
            parentSuite.increaseWeight();
            this.tests.set(test.id, test);
        }

        this.#applyTagModifiers(test);
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
        if (this.#dry) {
            return;
        }
        this.__after(...callbacks);
    }

    /**
     * Registers a callback that will be executed at the very end of the test runner,
     * after all suites have been run.
     *
     * @param {...Callback<never>} callbacks
     */
    afterAll(...callbacks) {
        if (this.#dry) {
            return;
        }
        this.__afterAll(...callbacks);
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
        if (this.#dry) {
            return;
        }
        this.__afterEach(...callbacks);
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
        if (this.#dry) {
            return;
        }
        this.__before(...callbacks);
    }

    /**
     * Registers a callback that will be executed at the very start of the test
     * runner, before any suites have been run.
     *
     * @param {...Callback<never>} callbacks
     */
    beforeAll(...callbacks) {
        if (this.#dry) {
            return;
        }
        this.__beforeAll(...callbacks);
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
        if (this.#dry) {
            return;
        }
        this.__beforeEach(...callbacks);
    }

    /**
     * @template T
     * @template {(previous: T | null) => T} F
     * @param {F} instanceGetter
     * @param {() => any} [afterCallback]
     * @returns {F}
     */
    createJobScopedGetter(instanceGetter, afterCallback) {
        /** @type {F} */
        const getInstance = () => {
            const currentJob = this.state.currentTest || this.#suiteStack.at(-1) || this;
            if (!instances.has(currentJob)) {
                const parentInstance = [...instances.values()].at(-1);
                instances.set(currentJob, instanceGetter(parentInstance));

                if (canCallAfter) {
                    this.after(() => {
                        instances.delete(currentJob);

                        canCallAfter = false;
                        afterCallback?.();
                        canCallAfter = true;
                    });
                }
            }

            return instances.get(currentJob);
        };

        /** @type {Map<Job, T>} */
        const instances = new Map();
        let canCallAfter = true;

        return getInstance;
    }

    /**
     * @param {() => Promise<void>} callback
     * @returns {Promise<{ suites: Suite[]; tests: Test[] }>}
     */
    async dryRun(callback) {
        if (this.state.status !== "ready") {
            throw new HootError("cannot run a dry run after the test runner started");
        }

        this.#dry = true;

        await callback();

        this.#prepareRunner();

        this.#dry = false;

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
            suite: this.#suiteStack.at(-1) || null,
            test: this.state.currentTest,
        };
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
        if (this.#dry) {
            return;
        }
        this.__onError(...callbacks);
    }

    /**
     * @param {Job[]} [jobs]
     * @param {boolean} [implicitInclude] fallback include value for sub-jobs
     * @returns {Job[]}
     */
    prepareJobs(jobs = this.rootSuites, implicitInclude = !this.#hasIncludeFilter) {
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

            this.state.tests.push(debugTest);

            const jobs = debugTest.path;
            for (let i = 0; i < jobs.length - 1; i++) {
                const suite = jobs[i];
                suite.currentJobs = [jobs[i + 1]];
                this.state.suites.push(suite);
            }
            return [jobs[0]];
        }

        const filteredJobs = jobs.filter((job) => {
            // Priority 1: explicit include or exclude (URL or special tag)
            const [explicitInclude, explicitExclude] = this.#getExplicitIncludeStatus(job);
            if (explicitExclude) {
                return false;
            }

            // Priority 2: implicit exclude
            if (!explicitInclude && this.#isImplicitlyExcluded(job)) {
                return false;
            }

            // Priority 3: implicit include
            let included = explicitInclude || implicitInclude || this.#isImplicitlyIncluded(job);
            if (job instanceof Suite) {
                // For suites: included if at least 1 included job
                job.currentJobs = this.prepareJobs(job.jobs, included);
                included = Boolean(job.currentJobs.length);

                if (included) {
                    this.state.suites.push(job);
                }
            } else if (included) {
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
     * @param {StartOptions} [options]
     */
    async start(options) {
        await whenReady();

        if ((options?.auto && this.config.manual) || this.state.status !== "ready") {
            // Already running or in manual mode
            return;
        }
        this.state.status = "running";

        this.#prepareRunner();
        this.#startTime = $now();

        // Config log
        const table = { ...toRaw(this.config) };
        for (const key of FILTER_KEYS) {
            if (isIterable(table[key])) {
                table[key] = `[${[...table[key]].join(", ")}]`;
            }
        }
        logger.groupCollapsed("Configuration (click to expand)");
        logger.table(table);
        logger.groupEnd();
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

        const { fps, watchkeys } = this.config;

        // Register default hooks
        const [addTestDone, flushTestDone] = batch((test) => this.state.done.push(test), 10);
        this.__afterAll(
            flushTestDone,
            // Catch errors
            on(window, "error", (ev) => this.#onError(ev)),
            on(window, "unhandledrejection", (ev) => this.#onError(ev)),
            // Warn user events
            !this.debug && on(window, "pointermove", warnUserEvent),
            !this.debug && on(window, "pointerdown", warnUserEvent),
            !this.debug && on(window, "keydown", warnUserEvent),
            watchListeners(window, document, document.documentElement, document.head, document.body)
        );
        this.__beforeEach(this.fixture.setup);
        this.__afterEach(
            cleanupWindow,
            cleanupNavigator,
            this.fixture.cleanup,
            cleanupDOM,
            cleanupTime
        );
        if (watchkeys) {
            const keys = watchkeys?.split(/\s*,\s*/g) || [];
            this.__afterEach(watchKeys(window, keys), watchKeys(document, keys));
        }

        if (this.debug) {
            logger.level = logLevels.DEBUG;
        }
        enableEventLogs(this.debug);
        setFrameRate(fps);

        await this.#callbacks.call("before-all");

        const nextJob = () => {
            this.state.currentTest = null;
            job = job.currentJobs?.[job.visited++] || job.parent || this.#currentJobs.shift();
        };

        let job = this.#currentJobs.shift();
        while (job && this.state.status === "running") {
            const callbackChain = this.#getCallbackChain(job);
            if (job instanceof Suite) {
                // Case: suite
                // -----------

                /** @type {Suite} */
                const suite = job;
                if (suite.canRun()) {
                    if (suite.visited === 0) {
                        // before suite code
                        this.#suiteStack.push(suite);

                        for (const callbackRegistry of [...callbackChain].reverse()) {
                            await callbackRegistry.call("before-suite", suite);
                        }
                    }
                    if (suite.visited === suite.currentJobs.length) {
                        // after suite code
                        this.#suiteStack.pop();

                        await this.#execAfterCallback(async () => {
                            for (const callbackRegistry of callbackChain) {
                                await callbackRegistry.call("after-suite", suite);
                            }
                        });

                        suite.parent?.reporting.add({ suites: +1 });

                        logger.logSuite(suite);
                    }
                }
                nextJob();
                continue;
            }

            // Case: test
            // ----------

            /** @type {Test} */
            const test = job;
            if (test.config.skip) {
                // Skipped test
                addTestDone(test);
                test.parent.reporting.add({ skipped: +1 });
                nextJob();
                continue;
            }

            // Suppress console errors and warnings if test is in "todo" mode
            // (and not in debug).
            const suppressErrors = test.config.todo && !this.debug;
            if (suppressErrors) {
                suppressConsoleErrors("test.todo");
            }

            // Before test
            this.state.currentTest = test;
            for (const callbackRegistry of [...callbackChain].reverse()) {
                await callbackRegistry.call("before-test", test);
            }

            this.expectHooks.before(test);

            let timeoutId = 0;

            // ! The following assignment should stay in the `start` function to
            // ! keep the smallest stack trace possible:
            // !    TestRunner.start() > Test.run() > Error
            const testPromise = Promise.resolve(test.run());
            const timeout = $floor(test.config.timeout || this.config.timeout);
            const timeoutPromise = new Promise((resolve, reject) => {
                // Set abort signal
                this.#rejectCurrent = reject;
                this.#resolveCurrent = resolve;

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
                    this.#rejectCurrent = noop; // prevents loop

                    return this.#onError(error);
                })
                .finally(() => {
                    this.#rejectCurrent = noop;
                    this.#resolveCurrent = noop;

                    if (timeoutId) {
                        clearTimeout(timeoutId);
                    }
                });

            // After test
            const { lastResults } = test;
            await this.#execAfterCallback(async () => {
                for (const callbackRegistry of callbackChain) {
                    await callbackRegistry.call("after-test", test);
                }
            });

            if (suppressErrors) {
                restoreConsole();
            }

            // Log test errors and increment counters
            this.expectHooks.after(test, this);
            test.visited++;
            if (lastResults.pass) {
                logger.logTest(test);
            } else {
                let failReason;
                if (lastResults.errors.length) {
                    failReason = lastResults.errors.map((e) => e.message).join("\n");
                } else {
                    failReason = formatAssertions(lastResults.assertions);
                }

                logger.error(`Test "${test.fullName}" failed:\n${failReason}`);
            }

            await this.#callbacks.call("after-post-test", test);

            if (this.config.bail) {
                if (!test.config.skip && !lastResults.pass) {
                    this.#failed++;
                }
                if (this.#failed >= this.config.bail) {
                    return this.stop();
                }
            }
            if (!test.config.multi || test.visited === test.config.multi) {
                addTestDone(test);
                nextJob();
            }
        }

        if (!this.state.tests.length) {
            logger.error(`no tests to run`);
            await this.stop();
        } else if (!this.debug) {
            await this.stop();
        }
    }

    async stop() {
        this.#currentJobs = [];
        this.state.status = "done";
        this.totalTime = formatTime($now() - this.#startTime);

        if (this.#resolveCurrent !== noop) {
            return this.#resolveCurrent();
        }

        while (this.#missedCallbacks.length) {
            await this.#missedCallbacks.shift()();
        }

        await this.#callbacks.call("after-all");

        const { passed, failed, assertions } = this.reporting;
        if (failed > 0) {
            // Use console.dir for this log to appear on runbot sub-builds page
            logger.logGlobal(
                `failed ${failed} tests (${passed} passed, total time: ${this.totalTime})`
            );
            logger.error("test failed (see above for details)");
        } else {
            // Use console.dir for this log to appear on runbot sub-builds page
            logger.logGlobal(
                `passed ${passed} tests (${assertions} assertions, total time: ${this.totalTime})`
            );
            // This statement acts as a success code for the server to know when
            // all suites have passed.
            logger.logRun("test suite succeeded");
        }
    }

    /**
     * @param {...Callback<Job>} callbacks
     */
    __after(...callbacks) {
        const { suite, test } = this.getCurrent();
        if (test) {
            for (const callback of callbacks) {
                suite.callbacks.add("after-test", callback, true);
            }
        } else {
            const callbackRegistry = suite ? suite.callbacks : this.#callbacks;
            for (const callback of callbacks) {
                callbackRegistry.add("after-suite", callback);
            }
        }
    }

    /**
     * @param {...Callback<never>} callbacks
     */
    __afterAll(...callbacks) {
        for (const callback of callbacks) {
            this.#callbacks.add("after-all", callback);
        }
    }

    /**
     * @param {...Callback<Test>} callbacks
     */
    __afterEach(...callbacks) {
        const { suite, test } = this.getCurrent();
        if (test) {
            throw testError(test, `cannot call hook "afterEach" inside of a test`);
        }
        const callbackRegistry = suite ? suite.callbacks : this.#callbacks;
        for (const callback of callbacks) {
            callbackRegistry.add("after-test", callback);
        }
    }

    /**
     * @param {...Callback<Test>} callbacks
     */
    __afterPostTest(...callbacks) {
        for (const callback of callbacks) {
            this.#callbacks.add("after-post-test", callback);
        }
    }

    /**
     * @param {...Callback<Job>} callbacks
     */
    __before(...callbacks) {
        const { suite, test } = this.getCurrent();
        if (test) {
            for (const callback of callbacks) {
                suite.callbacks.add("after-test", callback(test), true);
            }
        } else {
            const callbackRegistry = suite ? suite.callbacks : this.#callbacks;
            for (const callback of callbacks) {
                callbackRegistry.add("before-suite", callback);
            }
        }
    }

    /**
     * @param {...Callback<never>} callbacks
     */
    __beforeAll(...callbacks) {
        for (const callback of callbacks) {
            this.#callbacks.add("before-all", callback);
        }
    }

    /**
     * @param {...Callback<Test>} callbacks
     */
    __beforeEach(...callbacks) {
        const { suite, test } = this.getCurrent();
        if (test) {
            throw testError(test, `cannot call hook "beforeEach" inside of a test`);
        }
        const callbackRegistry = suite ? suite.callbacks : this.#callbacks;
        for (const callback of callbacks) {
            callbackRegistry.add("before-test", callback);
        }
    }

    /**
     * @param {...Callback<ErrorEvent | PromiseRejectionEvent>} callbacks
     */
    __onError(...callbacks) {
        const { suite, test } = this.getCurrent();
        const callbackRegistry = suite ? suite.callbacks : this.#callbacks;
        for (const callback of callbacks) {
            callbackRegistry.add("error", callback, Boolean(test));
        }
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
    #addConfigurators(fn, getCurrent) {
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
                current: { get: () => this.#createCurrentConfigurators(getCurrent) },
            });
        }

        return taggedFn;
    }

    /**
     * @param {Preset} preset
     */
    #applyPreset(preset) {
        if (preset.tags?.length) {
            this.#include("tags", preset.tags, true);
        }
        if (preset.platform) {
            mockUserAgent(preset.platform);
        }

        if (typeof preset.touch === "boolean") {
            mockTouch(preset.touch);
        }
    }

    /**
     * @param {Job} job
     */
    #applyTagModifiers(job) {
        let skip = false;
        let ignoreSkip = false;
        for (const tag of job.tags) {
            this.tags.add(tag);
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
                    this.#include(job instanceof Suite ? "suites" : "tests", [job.id], true);
                    ignoreSkip = true;
                    break;
                case Tag.SKIP:
                    skip = true;
                    break;
                case Tag.TODO:
                    job.config.todo = true;
                    break;
            }
        }

        if (skip) {
            if (ignoreSkip) {
                logger.warn(
                    `test "${job.fullName}" is explicitly included but marked as skipped: "skip" modifier has been ignored`
                );
            } else {
                job.config.skip = true;
            }
        }
    }

    /**
     * @param {() => Job} getCurrent
     */
    #createCurrentConfigurators(getCurrent) {
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
            this.#applyTagModifiers(current);

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
    async #execAfterCallback(callback) {
        if (this.debug) {
            this.#missedCallbacks.push(callback);
            if (this.state.currentTest) {
                await this.#callbacks.call("after-debug-test", this.state.currentTest);
            }
        } else {
            await callback();
        }
    }

    /**
     * @param {Job} job
     * @returns {ReturnType<typeof makeCallbacks>[]}
     */
    #getCallbackChain(job) {
        const chain = [];
        while (job) {
            if (job instanceof Suite) {
                chain.push(job.callbacks);
            }
            job = job.parent;
        }
        chain.push(this.#callbacks);
        return chain;
    }

    /**
     * @param {Job} job
     */
    #getExplicitIncludeStatus(job) {
        const includeSpec =
            job instanceof Suite ? this.state.includeSpecs.suites : this.state.includeSpecs.tests;
        const explicitInclude = includeSpec[job.id] || 0;
        return [explicitInclude > 0, explicitInclude < 0];
    }

    /**
     * @param {"suites" | "tags" | "tests"} type
     * @param {Iterable<string>} ids
     * @param {boolean} [readonly]
     */
    #include(type, ids, readonly) {
        const values = this.state.includeSpecs[type];
        for (const id of ids) {
            const nId = normalize(id);
            if (id.startsWith(EXCLUDE_PREFIX)) {
                values[nId.slice(EXCLUDE_PREFIX.length)] = readonly ? -2 : -1;
                this.#hasExcludeFilter = true;
            } else if ((values[nId]?.[0] || 0) >= 0) {
                this.#hasIncludeFilter = true;
                values[nId] = readonly ? +2 : +1;
            }
        }
    }

    /**
     * @param {Job} job
     * @returns {boolean | null}
     */
    #isImplicitlyExcluded(job) {
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
    #isImplicitlyIncluded(job) {
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

    #prepareRunner() {
        if (this.#prepared) {
            return;
        }
        this.#prepared = true;

        if (this.config.preset) {
            const preset = this.presets.get(this.config.preset);
            if (!preset) {
                throw new HootError(`unknown preset: "${this.config.preset}"`);
            }
            this.#applyPreset(preset);
        }

        this.#currentJobs = this.prepareJobs();
    }

    /**
     * @param {Error | ErrorEvent | PromiseRejectionEvent} ev
     */
    async #onError(ev) {
        const error = ensureError(ev);
        if (!(ev instanceof Event)) {
            ev = new ErrorEvent("error", { error });
        }

        if (this.state.currentTest) {
            for (const callbackRegistry of this.#getCallbackChain(this.state.currentTest)) {
                callbackRegistry.callSync("error", ev);
                if (ev.defaultPrevented) {
                    return;
                }
            }

            const { lastResults } = this.state.currentTest;
            if (!lastResults) {
                return;
            }

            ev.preventDefault();

            lastResults.errors.push(error);
            lastResults.caughtErrors++;
            if (lastResults.expectedErrors >= lastResults.caughtErrors) {
                return;
            }

            this.#rejectCurrent(error);
        }

        if (this.config.notrycatch) {
            throw error;
        }

        if (error.cause) {
            logger.error(error.cause);
        }
        logger.error(error);
    }
}
