/** @odoo-module */

import { generateSeed } from "../mock/math";

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @template {Record<string, any>} T
 * @param {T} schema
 * @returns {{ [key in keyof T]: ReturnType<T[key]["parse"]> }}
 */
const getSchemaDefaults = (schema) =>
    Object.fromEntries(Object.entries(schema).map(([key, value]) => [key, value.default]));

/**
 * @template {Record<string, any>} T
 * @param {T} schema
 * @returns {(keyof T)[]}
 */
const getSchemaKeys = (schema) => Object.keys(schema);

/**
 * @template T
 * @param {(values: string[]) => T} parse
 * @returns {(valueIfEmpty: T) => (values: string[]) => T}
 */
const makeParser = (parse) => (valueIfEmpty) => (values) =>
    values.length ? parse(values) : valueIfEmpty;

const parseBoolean = makeParser(([value]) => value === "true");

const parseNumber = makeParser(([value]) => Number(value) || 0);

/** @type {ReturnType<typeof makeParser<"first-fail" | "failed" | false>>} */
const parseShowDetail = makeParser(([value]) => (value === "false" ? false : value));

const parseString = makeParser(([value]) => value);

const parseStringArray = makeParser((values) => values);

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

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
     * runner in "debug" mode. See {@link TestRunner.debug} for more info.
     * @default false
     */
    debugTest: {
        default: false,
        parse: parseBoolean(true),
    },
    /**
     * Amount of frames rendered per second, used when mocking animation frames.
     * @default 60
     */
    frameRate: {
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
     * Whether the test runner must be manually started after page load (defaults
     * to starting automatically).
     * @default false
     */
    manual: {
        default: false,
        parse: parseBoolean(true),
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
     * Determines the seed from which random numbers will be generated. If truthy,
     * tests and suites will be shuffled within their parent suite.
     *
     * If set without a seed (= without URL value):
     *  -> the seed will be randomly generated and tests/suites will be shuffled accordingly
     * If set with a seed (= with a given URL value):
     *  -> tests/suites will be shuffled using the seed
     * If not set (= 0):
     *  -> tests/suites will be run sequentially as declared in the file system
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
    /**
     * Monitors keys added on global objects if truthy. The value is a comma-separated
     * list of white-listed keys. If left empty, no monitoring will be performed.
     * @default ""
     */
    watchkeys: {
        default: "",
        parse: parseString(""),
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
     * IDs of the suites to run exclusively. The ID of a suite is generated deterministically
     * based on its full name.
     * @default []
     */
    suite: {
        aliases: ["suites"],
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
    /**
     * IDs of the tests to run exclusively. The ID of a test is generated deterministically
     * based on its full name.
     * @default []
     */
    test: {
        aliases: ["tests"],
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
