/** @odoo-module */

import { getColorHex } from "../../hoot-dom/hoot_dom_utils";
import { stringify } from "../hoot_utils";
import { urlParams } from "./url";

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const {
    console: {
        debug: $debug,
        dir: $dir,
        error: $error,
        groupCollapsed: $groupCollapsed,
        groupEnd: $groupEnd,
        log: $log,
        table: $table,
        trace: $trace,
        warn: $warn,
    },
} = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @param {any[]} args
 * @param {string} [prefix]
 * @param {string} [prefixColor]
 */
function styledArguments(args, prefix, prefixColor) {
    const fullPrefix = `%c[${prefix || DEFAULT_PREFIX[0]}]%c`;
    const styles = [`color:${prefixColor || DEFAULT_PREFIX[1]};font-weight:bold`, ""];
    const firstArg = args.shift() ?? "";
    if (typeof firstArg === "string") {
        args.unshift(`${fullPrefix} ${firstArg}`, ...styles);
    } else {
        args.unshift(fullPrefix, ...styles, firstArg);
    }
    return args;
}

/**
 * @param {any[]} args
 */
function unstyledArguments(args) {
    const prefix = `[${DEFAULT_PREFIX[0]}]`;
    const firstArg = args.shift() ?? "";
    if (typeof firstArg === "string") {
        args.unshift(`${prefix} ${firstArg}`);
    } else {
        args.unshift(prefix, firstArg);
    }
    return [args.join(" ")];
}

const DEBUG_PREFIX = ["DEBUG", getColorHex("purple")];
const DEFAULT_PREFIX = ["HOOT", getColorHex("primary")];
const ERROR_PREFIX = ["ERROR", getColorHex("rose")];
const WARNING_PREFIX = ["WARNING", getColorHex("amber")];
let nextNetworkLogId = 1;

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * @param {string} prefix
 * @param {string} title
 */
export function makeNetworkLogger(prefix, title) {
    const id = nextNetworkLogId++;
    return {
        /**
         * Request logger: blue-ish.
         * @param {() => any} getData
         */
        async logRequest(getData) {
            if (!logger.allows("debug")) {
                return;
            }
            const color = `color: #66e`;
            const styles = [`${color}; font-weight: bold;`, color];
            $groupCollapsed(`-> %c${prefix}#${id}%c<${title}>`, ...styles, await getData());
            $trace("request trace");
            $groupEnd();
        },
        /**
         * Response logger: orange.
         * @param {() => any} getData
         */
        async logResponse(getData) {
            if (!logger.allows("debug")) {
                return;
            }
            const color = `color: #f80`;
            const styles = [`${color}; font-weight: bold;`, color];
            $log(`<- %c${prefix}#${id}%c<${title}>`, ...styles, await getData());
        },
    };
}

export const LOG_LEVELS = {
    runner: 0,
    suites: 1,
    tests: 2,
    debug: 3,
};

export const logger = {
    /** @private */
    currentLevel: urlParams.loglevel ?? LOG_LEVELS.runner,
    suppressed: "",

    // Standard console methods

    /**
     * @param {...any} args
     */
    debug(...args) {
        $debug(...styledArguments(args));
    },
    /**
     * @param {...any} args
     */
    error(...args) {
        if (logger.suppressed) {
            $groupCollapsed(...styledArguments([logger.suppressed], ...ERROR_PREFIX));
            $trace(...args);
            $groupEnd();
        } else {
            $trace(...styledArguments(args, ...ERROR_PREFIX));
        }
    },
    /**
     * @param {any} arg
     * @param {() => any} callback
     */
    group(title, callback) {
        $groupCollapsed(...styledArguments([title]));
        callback();
        $groupEnd();
    },
    /**
     * @param  {...any} args
     */
    table(...args) {
        $table(...args);
    },
    /**
     * @param  {...any} args
     */
    trace(...args) {
        $trace(...args);
    },
    /**
     * @param {...any} args
     */
    warn(...args) {
        if (logger.suppressed) {
            $groupCollapsed(...styledArguments([logger.suppressed], ...WARNING_PREFIX));
            $trace(...args);
            $groupEnd();
        } else {
            $warn(...styledArguments(args));
        }
    },

    // Level-specific methods

    /**
     * @param {...any} args
     */
    logDebug(...args) {
        if (!logger.allows("debug")) {
            return;
        }
        $debug(...styledArguments(args, ...DEBUG_PREFIX));
    },
    /**
     * @param {import("./suite").Suite} suite
     */
    logSuite(suite) {
        if (!logger.allows("suites")) {
            return;
        }
        const args = [`${stringify(suite.fullName)} ended`];
        const withArgs = [];
        if (suite.reporting.passed) {
            withArgs.push("passed:", suite.reporting.passed, "/");
        }
        if (suite.reporting.failed) {
            withArgs.push("failed:", suite.reporting.failed, "/");
        }
        if (suite.reporting.skipped) {
            withArgs.push("skipped:", suite.reporting.skipped, "/");
        }
        if (withArgs.length) {
            args.push(
                `(${withArgs.shift()}`,
                ...withArgs,
                "time:",
                suite.jobs.reduce((acc, job) => acc + (job.duration || 0), 0),
                "ms)"
            );
        }
        $log(...styledArguments(args));
    },
    /**
     * @param {import("./test").Test} test
     */
    logTest(test) {
        if (!logger.allows("tests")) {
            return;
        }
        const { fullName, lastResults } = test;
        $log(
            ...styledArguments([
                `Test ${stringify(fullName)} passed (assertions:`,
                lastResults.counts.assertion || 0,
                `/ time:`,
                lastResults.duration,
                `ms)`,
            ])
        );
    },
    /**
     * @param {[label: string, color: string]} prefix
     * @param {...any} args
     */
    logTestEvent(prefix, ...args) {
        $log(...styledArguments(args, ...prefix));
    },
    /**
     * @param {...any} args
     */
    logRun(...args) {
        if (!logger.allows("runner")) {
            return;
        }
        $log(...styledArguments(args));
    },
    /**
     * @param {...any} args
     */
    logGlobal(...args) {
        $dir(...unstyledArguments(args));
    },
    /**
     * @param {...any} args
     */
    logGlobalError(...args) {
        $error(...styledArguments(args));
    },
    /**
     * @param {...any} args
     */
    logGlobalWarning(...args) {
        $warn(...styledArguments(args));
    },

    // Other methods

    /**
     * @param {keyof typeof LOG_LEVELS} level
     */
    allows(level) {
        return logger.currentLevel >= LOG_LEVELS[level];
    },
    /**
     * @param {keyof typeof LOG_LEVELS} level
     */
    setLevel(level) {
        logger.currentLevel = LOG_LEVELS[level];
    },
    /**
     * @param {string} reason
     */
    suppressIssues(reason) {
        logger.suppressed = reason || "(suppressed)";
        return function restore() {
            logger.suppressed = "";
        };
    },
};
