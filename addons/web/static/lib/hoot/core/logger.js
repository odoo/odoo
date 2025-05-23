/** @odoo-module */

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
const styledArguments = (args, prefix, prefixColor) => {
    const fullPrefix = `%c[${prefix || "HOOT"}]%c`;
    const styles = [`color:${prefixColor || "#ff0080"};font-weight:bold`, ""];
    let firstArg = args.shift() ?? "";
    if (typeof firstArg === "function") {
        firstArg = firstArg();
    }
    if (typeof firstArg === "string") {
        args.unshift(`${fullPrefix} ${firstArg}`, ...styles);
    } else {
        args.unshift(fullPrefix, ...styles, firstArg);
    }
    return args;
};

/**
 * @param {any[]} args
 */
const unstyledArguments = (args) => {
    const prefix = `[HOOT]`;
    const firstArg = args.shift() ?? "";
    if (typeof firstArg === "string") {
        args.unshift(`${prefix} ${firstArg}`);
    } else {
        args.unshift(prefix, firstArg);
    }
    return [args.join(" ")];
};

const DEBUG_PREFIX = ["DEBUG", "#ffb000"];
const ERROR_PREFIX = ["ERROR", "#9f1239"];
const WARNING_PREFIX = ["WARNING", "#f59e0b"];
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
            if (logger.level < LOG_LEVELS.debug) {
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
            if (logger.level < LOG_LEVELS.debug) {
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
    level: urlParams.loglevel ?? LOG_LEVELS.runner,
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
        if (logger.level < LOG_LEVELS.debug) {
            return;
        }
        $debug(...styledArguments(args, ...DEBUG_PREFIX));
    },
    /**
     * @param {import("./test").Test} test
     */
    logTest(test) {
        if (logger.level < LOG_LEVELS.tests) {
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
     * @param {import("./suite").Suite} suite
     */
    logSuite(suite) {
        if (logger.level < LOG_LEVELS.suites) {
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
     * @param {...any} args
     */
    logRun(...args) {
        if (logger.level < LOG_LEVELS.runner) {
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
     * @param {string} reason
     */
    suppressIssues(reason) {
        const restore = () => {
            logger.suppressed = "";
        };
        logger.suppressed = reason || "(suppressed)";
        return restore;
    },
};
