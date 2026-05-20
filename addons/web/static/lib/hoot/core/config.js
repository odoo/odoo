/** @odoo-module */

import { signal } from "@odoo/owl";
import { deepEqual, DEFAULT_EVENT_TYPES, generateSeed } from "../hoot_utils";

/**
 * @typedef {BaseConfigManager & {
 *  [Key in keyof HootConfig]: import("@odoo/owl").ReactiveValue<HootConfig[Key]>
 * }} ConfigManager
 *
 * @typedef {typeof DEFAULT_CONFIG_AND_FILTERS} HootConfig
 *
 * @typedef {keyof typeof FILTER_SCHEMA} SearchFilter
 */

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const {
    Number: { parseFloat: $parseFloat },
    Object: { entries: $entries, fromEntries: $fromEntries, keys: $keys },
    Symbol,
} = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @template {Record<string, any>} T
 * @param {T} schema
 * @returns {{ [key in keyof T]: ReturnType<T[key]["parse"]> }}
 */
function getSchemaDefaults(schema) {
    return $fromEntries($entries(schema).map(([key, value]) => [key, value.default]));
}

/**
 * @template {Record<string, any>} T
 * @param {T} schema
 * @returns {(keyof T)[]}
 */
function getSchemaKeys(schema) {
    return $keys(schema);
}

/**
 * @template T
 * @param {(values: string[]) => T} parse
 * @returns {(valueIfEmpty: T) => (values: string[]) => T}
 */
function makeParser(parse) {
    return (valueIfEmpty) => (values) => (values.length ? parse(values) : valueIfEmpty);
}

const parseBoolean = makeParser(([value]) => value === "true");

const parseNumber = makeParser(([value]) => $parseFloat(value) || 0);

/** @type {ReturnType<typeof makeParser<"first-fail" | "failed" | false>>} */
const parseShowDetail = makeParser(([value]) => (value === "false" ? false : value));

const parseString = makeParser(([value]) => value);

const parseStringArray = makeParser((values) => values);

class BaseConfigManager {}

const S_INITIAL_CONFIG = Symbol("initial config");

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * @param {ConfigManager} config
 * @param {boolean} [ignoreSameValue] if true, values identical to default will be 'null'
 */
export function getConfigValues(config, ignoreSameValue) {
    /** @type {HootConfig} */
    const dict = {};
    for (const [key, signal] of $entries(config)) {
        const value = signal();
        if (ignoreSameValue && deepEqual(value, DEFAULT_CONFIG_AND_FILTERS[key])) {
            dict[key] = null;
        } else {
            dict[key] = value;
        }
    }
    return dict;
}

/**
 * Check whether the config has changed since creation.
 *
 * @param {ConfigManager} config
 */
export function hasConfigChanged(config) {
    for (const [key, value] of $entries(config[S_INITIAL_CONFIG])) {
        if (!deepEqual(config[key](), value)) {
            return true;
        }
    }
    return false;
}

/**
 * @param {Partial<HootConfig>} urlParams
 * @returns {ConfigManager}
 */
export function makeConfigManager(urlParams) {
    const manager = new BaseConfigManager();
    const initialConfig = { ...DEFAULT_CONFIG_AND_FILTERS, ...urlParams };
    manager[S_INITIAL_CONFIG] = initialConfig;
    for (const [key, value] of $entries(initialConfig)) {
        manager[key] = signal(value);
    }
    return manager;
}

export const CONFIG_SCHEMA = {
    /**
     * Amount of failed tests after which the test runner will be stopped.
     * A falsy value (including 0) means that the runner should never be aborted.
     * @default false
     */
    bail: {
        default: 0,
        parse: parseNumber(1),
    },
    /**
     * Debug parameter used in Odoo.
     * It has no direct effect on the test runner, but is taken into account since
     * all URL parameters not explicitly defined in the schema are ignored.
     * @default ""
     */
    debug: {
        default: "",
        parse: parseString("assets"),
    },
    /**
     * Same as the {@link FILTER_SCHEMA.test} filter, while also putting the test
     * runner in "debug" mode. See {@link Runner.debug} for more info.
     * @default false
     */
    debugTest: {
        default: false,
        parse: parseBoolean(true),
    },
    /**
     * Determines the event types shown in test results.
     * @default assertion|error
     */
    events: {
        default: DEFAULT_EVENT_TYPES,
        parse: parseNumber(0),
    },
    /**
     * Amount of frames rendered per second, used when mocking animation frames.
     * @default 60
     */
    fps: {
        default: 60,
        parse: parseNumber(60),
    },
    /**
     * Lights up the mood.
     * @default false
     */
    fun: {
        default: false,
        parse: parseBoolean(true),
    },
    /**
     * Whether to render the test runner user interface.
     * Note: this cannot be changed at runtime: the UI will not be un-rendered or
     * rendered if this parameter changes.
     * @default false
     */
    headless: {
        default: false,
        parse: parseBoolean(true),
    },
    /**
     * Log level used by the test runner. The higher the level, the more logs will
     * be displayed.
     */
    loglevel: {
        default: 0,
        parse: parseNumber(0),
    },
    /**
     * Whether the test runner must be manually started after page load (defaults
     * to starting automatically).
     * @default false
     */
    manual: {
        default: false,
        parse: parseBoolean(true),
    },
    /**
     * Artifical delay introduced for each network call. It can be a fixed integer,
     * or an integer range (in the form "min-max") to generate a random delay between
     * "min" and "max".
     * @default 0
     */
    networkDelay: {
        default: "0",
        parse: parseString("0"),
    },
    /**
     * Removes the safety of 'try .. catch' statements around each test's run function
     * to let errors bubble to the browser.
     * @default false
     */
    notrycatch: {
        default: false,
        parse: parseBoolean(true),
    },
    /**
     * Determines the order of the tests execution.
     * - `"fifo"`: tests will be run sequentially as declared in the file system.
     * - `"lifo"`: tests will be run sequentially in the reverse order.
     * - `"random"`: shuffles tests and suites within their parent suite.
     * @default "fifo"
     */
    order: {
        default: "fifo",
        parse: parseString(""),
    },
    /**
     * Environment in which the test runner is running. This parameter is used to
     * determine the default value of other parameters, namely:
     *  - the user agent;
     *  - touch support;
     *  - size of the viewport.
     * @default "" no specific parameters are set
     */
    preset: {
        default: "",
        parse: parseString(""),
    },
    /**
     * Determines the seed from which random numbers will be generated.
     * @default 0
     */
    random: {
        default: 0,
        parse: parseString(generateSeed()),
    },
    /**
     * Determines how the failed tests must be unfolded in the UI:
     * - "first-fail": only the first failed test will be unfolded
     * - "failed": all failed tests will be unfolded
     * - false: all tests will remain folded
     * @default "first-fail"
     */
    showdetail: {
        default: "first-fail",
        parse: parseShowDetail("failed"),
    },
    /**
     * Duration (in milliseconds) at the end of which a test will automatically fail.
     * @default 5_000
     */
    timeout: {
        default: 5_000,
        parse: parseNumber(5_000),
    },
};

export const FILTER_SCHEMA = {
    /**
     * Search string that will filter matching tests/suites, based on:
     * - their full name (including their parent suite(s))
     * - their tags
     * @default ""
     */
    filter: {
        aliases: ["name"],
        default: "",
        parse: parseString(""),
    },
    /**
     * IDs of the suites OR tests to run exclusively. The ID of a job is generated
     * deterministically based on its full name.
     * @default []
     */
    id: {
        aliases: ["ids"],
        default: [],
        parse: parseStringArray([]),
    },
    /**
     * Tag names of tests and suites to run exclusively (case insensitive).
     * @default []
     */
    tag: {
        aliases: ["tags"],
        default: [],
        parse: parseStringArray([]),
    },
};

/** @see {@link CONFIG_SCHEMA} */
export const DEFAULT_CONFIG = getSchemaDefaults(CONFIG_SCHEMA);
export const CONFIG_KEYS = getSchemaKeys(CONFIG_SCHEMA);

/** @see {@link FILTER_SCHEMA} */
export const DEFAULT_FILTERS = getSchemaDefaults(FILTER_SCHEMA);
export const FILTER_KEYS = getSchemaKeys(FILTER_SCHEMA);

export const DEFAULT_CONFIG_AND_FILTERS = { ...DEFAULT_CONFIG, ...DEFAULT_FILTERS };
