/** @odoo-module */
/* eslint-disable no-restricted-syntax */

import { markRaw, reactive, toRaw, whenReady } from "@odoo/owl";
import { cleanupObservers, isEmpty, watchKeys } from "@web/../lib/hoot-dom/helpers/dom";
import { enableEventLogs, on } from "@web/../lib/hoot-dom/helpers/events";
import { isIterable, parseRegExp } from "@web/../lib/hoot-dom/hoot_dom_utils";
import {
    HootError,
    Markup,
    createReporting,
    ensureArray,
    ensureError,
    formatTechnical,
    formatTime,
    getFuzzyScore,
    hootLog,
    makeCallbacks,
    normalize,
} from "../hoot_utils";
import { MockMath, internalRandom } from "../mock/math";
import { cleanupNavigator } from "../mock/navigator";
import { enableNetworkLogs } from "../mock/network";
import { cleanupTime, setFrameRate } from "../mock/time";
import { cleanupWindow, watchListeners } from "../mock/window";
import { DEFAULT_CONFIG, FILTER_KEYS } from "./config";
import { makeExpectFunction } from "./expect";
import { makeFixtureManager } from "./fixture";
import { Suite, suiteError } from "./suite";
import { Tag } from "./tag";
import { Test, testError } from "./test";
import { EXCLUDE_PREFIX, setParams, urlParams } from "./url";

/**
 * @typedef {Suite | Test} Job
 *
 * @typedef {import("./job").JobConfig} JobConfig
 *
 * @typedef {{
 *  auto?: boolean;
 *  callback?: () => MaybePromise<any>;
 *  dry?: boolean;
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
    console,
    document,
    Map,
    Math,
    performance,
    Promise,
    Set,
    setTimeout,
    window,
} = globalThis;

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

const noop = () => {};

const restoreConsole = () => {
    Object.assign(console, ORINAL_CONSOLE_METHODS);
};

/**
 * @template T
 * @param {T[]} array
 */
const shuffle = (array) => {
    const copy = [...array];
    let randIndex;
    for (let i = 0; i < copy.length; i++) {
        randIndex = Math.floor(internalRandom() * copy.length);
        [copy[i], copy[randIndex]] = [copy[randIndex], copy[i]];
    }
    return copy;
};

/**
 * @param {string} reason
 */
const suppressConsole = (reason) => {
    /**
     * @param {string} label
     * @param {string} color
     */
    const suppressedMethod = (label, color) => {
        const groupName = [`%c[${label}]%c suppressed by ${reason}`, `color: ${color}`, ""];
        return (...args) => {
            console.group(...groupName);
            console.log(...args);
            console.groupEnd(...groupName);
        };
    };

    Object.assign(console, {
        error: suppressedMethod("ERROR", "#9f1239"),
        warn: suppressedMethod("WARNING", "#f59e0b"),
    });
};

const ORINAL_CONSOLE_METHODS = {
    error: console.error,
    warn: console.warn,
};

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export class TestRunner {
    // Properties
    debug = false;
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
         * Dictionnary containing whether a job is included or excluded from the
         * current run.
         * @type {{
         *  suites: Record<string, boolean>;
         *  tags: Record<string, boolean>;
         *  tests: Record<string, boolean>;
         * }}
         */
        includeSpecs: { suites: {}, tags: {}, tests: {} },
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
    #failed = 0;
    #hasExcludeFilter = false;
    #hasIncludeFilter = false;
    /** @type {(() => MaybePromise<void>)[]} */
    #missedCallbacks = [];
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
        this.describe = this.#applyTestModifiers(this.addSuite);
        this.expect = makeExpectFunction(this);
        this.fixture = makeFixtureManager(this);
        this.test = this.#applyTestModifiers(this.addTest);

        const initialConfig = { ...DEFAULT_CONFIG, ...config };
        this.config = reactive({ ...initialConfig, ...urlParams }, () => {
            for (const key in this.config) {
                if (this.config[key] !== initialConfig[key]) {
                    setParams({ [key]: this.config[key] });
                } else {
                    setParams({ [key]: null });
                }
            }
        });

        // Debug
        this.debug = Boolean(urlParams.debugTest);

        // Text filter
        if (urlParams.filter) {
            this.#hasIncludeFilter = true;
            this.textFilter = parseRegExp(normalize(urlParams.filter));
        }

        // Suites
        if (urlParams.suite?.length) {
            this.#include("suites", ...urlParams.suite);
        }

        // Tags
        if (urlParams.tag?.length) {
            this.#include("tags", ...urlParams.tag);
        }

        // Tests
        if (urlParams.test?.length) {
            this.#include("tests", ...urlParams.test);
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
        const { suite: parentSuite } = this.getCurrent();
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
        for (const tag of suite.tags) {
            if (tag.special) {
                switch (tag.name) {
                    case Tag.DEBUG:
                        this.debug = true;
                    // fall through
                    case Tag.ONLY:
                        this.#include("suites", suite.id);
                        break;
                    case Tag.SKIP:
                        suite.config.skip = true;
                        break;
                    case Tag.TODO:
                        suite.config.todo = true;
                        break;
                }
            } else if (isEmpty(tag.config)) {
                this.tags.add(tag);
            }
        }
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
        const { suite: parentSuite } = this.getCurrent();
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
        let test = markRaw(new Test(parentSuite, name, config, fn));
        const originalTest = this.tests.get(test.id);
        if (originalTest) {
            if (originalTest.run === null) {
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
            this.tests.set(test.id, test);
        }
        for (const tag of test.tags) {
            if (tag.special) {
                switch (tag.name) {
                    case Tag.DEBUG:
                        this.debug = true;
                    // fall through
                    case Tag.ONLY:
                        this.#include("tests", test.id);
                        break;
                    case Tag.SKIP:
                        test.config.skip = true;
                        break;
                    case Tag.TODO:
                        test.config.todo = true;
                        break;
                }
            } else if (isEmpty(tag.config)) {
                this.tags.add(tag);
            }
        }
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
            const callbackRegistry = suite ? suite.callbacks : this.#callbacks;
            for (const callback of callbacks) {
                callbackRegistry.add("after-suite", callback);
            }
        }
    }

    /**
     * Registers a callback that will be executed at the very end of the test runner,
     * after all suites have been run.
     *
     * @param {...Callback<never>} callbacks
     */
    afterAll(...callbacks) {
        for (const callback of callbacks) {
            this.#callbacks.add("after-all", callback);
        }
    }

    /**
     * ! This is not meant to be exported and should be used in HOOT internally.
     * Registers a callback that will be executed at the end of any test, before
     * any other "after" callbacks have been called and regardless of the debug
     * state.
     *
     * @param {...Callback<Test>} callbacks
     */
    afterTestDone(...callbacks) {
        for (const callback of callbacks) {
            this.#callbacks.add("test-done", callback);
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
        const callbackRegistry = suite ? suite.callbacks : this.#callbacks;
        for (const callback of callbacks) {
            callbackRegistry.add("after-test", callback);
        }
    }

    /**
     * Starts the test runner if it is not set to manual mode.
     */
    async autostart() {
        if (!this.config.manual) {
            await this.start();
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
            const callbackRegistry = suite ? suite.callbacks : this.#callbacks;
            for (const callback of callbacks) {
                callbackRegistry.add("before-suite", callback);
            }
        }
    }

    /**
     * Registers a callback that will be executed at the very start of the test
     * runner, before any suites have been run.
     *
     * @param {...Callback<never>} callbacks
     */
    beforeAll(...callbacks) {
        for (const callback of callbacks) {
            this.#callbacks.add("before-all", callback);
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
        const callbackRegistry = suite ? suite.callbacks : this.#callbacks;
        for (const callback of callbacks) {
            callbackRegistry.add("before-test", callback);
        }
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
     * @param {Callback<ErrorEvent | PromiseRejectionEvent>} callback
     */
    onError(callback) {
        const { suite, test } = this.getCurrent();
        const callbacks = suite ? suite.callbacks : this.#callbacks;
        callbacks.add("error", callback, Boolean(test));
    }

    /**
     * @param {Callback<Test>} callback
     */
    onTestSkipped(callback) {
        this.#callbacks.add("test-skipped", callback);
    }

    /**
     * @param {Job[]} [jobs]
     * @param {boolean} [implicitInclude] fallback include value for sub-jobs
     * @returns {Job[]}
     */
    prepareJobs(jobs = this.rootSuites, implicitInclude = !this.#hasIncludeFilter) {
        const filteredJobs = jobs.filter((job) => {
            let included = this.#isIncluded(job) ?? implicitInclude;
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

        return this.config.random ? shuffle(filteredJobs) : filteredJobs;
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
     * @returns {Promise<{ suites: Suite[]; tests: Test[] }>}
     */
    async start(options) {
        await whenReady();

        if ((options?.auto && this.config.manual) || this.state.status !== "ready") {
            // Already running or in manual mode
            return {
                suites: [],
                tests: [],
            };
        }
        this.state.status = "running";

        this.#startTime = performance.now();
        if (!this.#currentJobs.length) {
            this.#currentJobs = this.prepareJobs();
        }

        if (options?.dry) {
            // Dry run
            this.state.status = "ready";
            for (const test of this.tests.values()) {
                // Soft resets all tests
                test.run = null;
            }
            for (const suite of this.suites.values()) {
                suite.callbacks.clear();
            }
            return {
                suites: this.state.suites,
                tests: this.state.tests,
            };
        }

        const table = { ...toRaw(this.config) };
        for (const key of FILTER_KEYS) {
            if (isIterable(table[key])) {
                table[key] = `[${[...table[key]].join(", ")}]`;
            }
        }
        const groupName = hootLog("Configuration (click to expand)");
        console.groupCollapsed(...groupName);
        console.table(table);
        console.groupEnd(...groupName);
        console.log(...hootLog("Starting test suites"));

        // Adjust debug mode if more than 1 test will be run
        if (this.debug && (this.state.tests.length > 1 || this.state.tests[0]?.config.multi)) {
            setParams({ debugTest: null });
            this.debug = false;
        }

        // Register default hooks
        this.afterAll(
            on(window, "error", (ev) => this.#onError(ev)),
            on(window, "unhandledrejection", (ev) => this.#onError(ev)),
            watchListeners(window, document, document.head, document.body)
        );
        this.beforeEach(this.fixture.setup);
        this.afterEach(
            cleanupTime,
            cleanupObservers,
            this.fixture.cleanup,
            cleanupNavigator,
            cleanupWindow
        );
        if (this.config.watchkeys) {
            const keys = this.config.watchkeys?.split(/\s*,\s*/g) || [];
            this.afterEach(watchKeys(window, keys), watchKeys(document, keys));
        }

        enableEventLogs(this.debug);
        enableNetworkLogs(this.debug);
        setFrameRate(this.config.frameRate);

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

                        // Log suite results and reset counters
                        const logArgs = [`"${suite.fullName}" ended`];
                        const withArgs = [];
                        if (suite.reporting.passed) {
                            withArgs.push(suite.reporting.passed, "passed");
                        }
                        if (suite.reporting.failed) {
                            withArgs.push(suite.reporting.failed, "failed");
                        }
                        if (suite.reporting.skipped) {
                            withArgs.push(suite.reporting.skipped, "skipped");
                        }
                        if (withArgs.length) {
                            logArgs.push("(", ...withArgs, ")");
                        }

                        console.log(...hootLog(...logArgs));
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
                for (const callbackRegistry of callbackChain) {
                    await callbackRegistry.call("test-skipped", test);
                }
                test.parent.reporting.add({ skipped: +1 });
                nextJob();
                continue;
            }

            // Suppress console errors and warnings if test is in "todo" mode
            // (and not in debug).
            const suppressErrors = test.config.todo && !this.debug;
            if (suppressErrors) {
                suppressConsole("test.todo");
            }

            // Before test
            this.state.currentTest = test;
            for (const callbackRegistry of [...callbackChain].reverse()) {
                await callbackRegistry.call("before-test", test);
            }

            this.expect.__before(this, test);

            let timeoutId = 0;

            // ! The following assignment should stay in the `start` function to
            // ! keep the smallest stack trace possible:
            // !    TestRunner.start() > Test.run() > Error
            const testPromise = Promise.resolve(test.run());
            const timeout = Math.floor(test.config.timeout || this.config.timeout);
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
                test.lastResults.aborted = true;
                this.debug = false; // Remove debug mode to let the runner stop
            });

            // Run test
            await Promise.race([testPromise, timeoutPromise])
                .catch((error) => {
                    this.#rejectCurrent = noop; // prevents loop

                    this.#onError(error);
                })
                .finally(() => {
                    this.#rejectCurrent = noop;
                    this.#resolveCurrent = noop;

                    if (timeoutId) {
                        clearTimeout(timeoutId);
                    }
                });

            this.expect.__after(this, test);
            test.visited++;

            // After test
            for (const callbackRegistry of callbackChain) {
                await callbackRegistry.call("test-done", test);
            }

            const { lastResults } = test;
            await this.#execAfterCallback(async () => {
                for (const callbackRegistry of callbackChain) {
                    await callbackRegistry.call("after-test", test);
                }

                if (this.config.bail) {
                    if (!test.config.skip && !lastResults.pass) {
                        this.#failed++;
                    }
                    if (this.#failed >= this.config.bail) {
                        return this.stop();
                    }
                }
            });

            if (suppressErrors) {
                restoreConsole();
            }

            // Log test errors and increment counters
            if (!lastResults.pass) {
                let failReason;
                if (lastResults.errors.length) {
                    failReason = lastResults.errors.map((e) => e.message).join("\n");
                } else {
                    failReason = formatAssertions(lastResults.assertions);
                }

                console.error(...hootLog(`Test "${test.fullName}" failed:\n${failReason}`));
            }

            if (!test.config.multi || test.visited === test.config.multi) {
                nextJob();
            }
        }

        if (!this.state.tests.length) {
            console.error(...hootLog(`no test to run`));
            await this.stop();
        } else if (!this.debug) {
            await this.stop();
        }

        return {
            suites: this.state.suites,
            tests: this.state.tests,
        };
    }

    async stop() {
        this.#currentJobs = [];
        this.#resolveCurrent();
        this.state.status = "done";
        this.totalTime = formatTime(performance.now() - this.#startTime);

        while (this.#missedCallbacks.length) {
            await this.#missedCallbacks.shift()();
        }

        await this.#callbacks.call("after-all");

        console.log(...hootLog(`All test suites have ended (total time: ${this.totalTime})`));
        if (this.#failed) {
            console.error(...hootLog("test failed (see above for details)"));
        } else {
            // This statement acts as a success code for the server to know when
            // all suites have passed.
            console.log(...hootLog("test successful"));
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
     * @param {T} fn
     * @returns {typeof taggedFn}
     */
    #applyTestModifiers(fn) {
        /**
         * @typedef {((...args: DropFirst<Parameters<T>>) => TaggedFunction) & {
         *  readonly config: typeof config;
         *  readonly debug: typeof taggedFn;
         *  readonly only: typeof taggedFn;
         *  readonly skip: typeof taggedFn;
         *  readonly todo: typeof taggedFn;
         * }} TaggedFunction
         */

        /**
         * Modifies the current test/suite configuration.
         *
         * - `timeout`: sets the timeout for the current test/suite;
         * - `multi`: sets the number of times the current test/suite will be run.
         *
         * @param  {...JobConfig} configs
         * @example
         *  // Will timeout each of its tests after 10 seconds
         *  describe.config({ timeout: 10_000 })("Expensive tests", () => { ... });
         * @example
         *  // Will be run 100 times
         *  test.config({ multi: 100 })("non-deterministic test", async () => { ... });
         */
        const config = (...configs) => {
            Object.assign(currentConfig, ...configs);

            return taggedFn;
        };

        /** @type {TaggedFunction} */
        const taggedFn = (...args) => {
            if (args[0]?.raw) {
                const tagString = String.raw(...args);
                currentConfig.tags.push(...tagString.split(/\s+/g));
                return taggedFn;
            }
            const jobConfig = { ...currentConfig };
            currentConfig = { tags: [] };
            return fn.call(this, jobConfig, ...args);
        };

        let currentConfig = { tags: [] };
        Object.defineProperties(taggedFn, {
            config: { value: config },
            debug: { get: () => taggedFn`debug` },
            only: { get: () => taggedFn`only` },
            skip: { get: () => taggedFn`skip` },
            todo: { get: () => taggedFn`todo` },
        });

        return taggedFn;
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
     *
     * @param {"suites" | "tags" | "tests"} type
     * @param {...string} ids
     */
    #include(type, ...ids) {
        const values = this.state.includeSpecs[type];
        for (const id of ids) {
            const nId = normalize(id);
            if (id.startsWith(EXCLUDE_PREFIX)) {
                values[nId.slice(EXCLUDE_PREFIX.length)] = false;
                this.#hasExcludeFilter = true;
            } else if (values[nId]?.[0] !== false) {
                this.#hasIncludeFilter = true;
                values[nId] = true;
            }
        }
    }

    /**
     * @param {Job} job
     * @returns {boolean | null}
     */
    #isIncluded(job) {
        const isSuite = job instanceof Suite;

        // Priority 1: excluded or included according to the value registered in the include map
        const includeValues = isSuite
            ? this.state.includeSpecs.suites
            : this.state.includeSpecs.tests;
        if (job.id in includeValues) {
            return includeValues[job.id];
        }

        // Priority 2: excluded if one of the job tags is in the tag "exlude" set
        const tagEntries = Object.entries(this.state.includeSpecs.tags);
        for (const [tagName, status] of tagEntries) {
            if (status === false && job.tagNames.has(tagName)) {
                return false;
            }
        }

        // Priority 3: included if one of the job tags is in the tag "include" set
        for (const [tagName, status] of tagEntries) {
            if (status === true && job.tagNames.has(tagName)) {
                return true;
            }
        }

        // Priority 4: included if the job name matches the text filter
        if (this.textFilter) {
            if (this.textFilter instanceof RegExp) {
                return this.textFilter.test(job.key);
            }
            const isExcluding = this.textFilter.startsWith(EXCLUDE_PREFIX);
            const query = isExcluding
                ? this.textFilter.slice(EXCLUDE_PREFIX.length)
                : this.textFilter;
            const match = getFuzzyScore(query, job.key) > 0;
            return isExcluding ? !match : match;
        }

        // No explicit filter matching the current job
        return null;
    }

    /**
     * @param {Error | ErrorEvent | PromiseRejectionEvent} ev
     */
    #onError(ev) {
        const error = ensureError(ev);
        if (!(ev instanceof Event)) {
            ev = new ErrorEvent("error", { error });
        }

        if (this.state.currentTest) {
            for (const callbackRegistry of this.#getCallbackChain(this.state.currentTest)) {
                callbackRegistry.call("error", ev);
                if (ev.defaultPrevented) {
                    return;
                }
            }

            ev.preventDefault();
            ev.stopPropagation();
            ev.stopImmediatePropagation();

            const { lastResults } = this.state.currentTest;
            lastResults.errors.push(error);
            if (lastResults.expectedErrors >= lastResults.errors.length) {
                return;
            }

            this.#rejectCurrent(error);
        }

        if (this.config.notrycatch) {
            throw error;
        }

        if (error.cause) {
            console.error(...hootLog(error.cause));
        }
        console.error(...hootLog(error));
    }
}
