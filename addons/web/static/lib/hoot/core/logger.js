/** @odoo-module */

import { getColorHex } from "../../hoot-dom/hoot_dom_utils";
import { isNil, stringify } from "../hoot_utils";
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
    Object: { entries: $entries, getOwnPropertyDescriptors: $getOwnPropertyDescriptors },
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

class Logger {
    /** @private */
    issueLevel;
    /** @private */
    logLevel;

    constructor(logLevel, issueLevel) {
        this.logLevel = logLevel;
        this.issueLevel = issueLevel;

        // Pre-bind all methods for ease of use
        for (const [key, desc] of $entries($getOwnPropertyDescriptors(Logger.prototype))) {
            if (key !== "constructor" && typeof desc.value === "function") {
                this[key] = this[key].bind(this);
            }
        }
    }

    get global() {
        return new Logger(this.logLevel, ISSUE_LEVELS.global);
    }

    // Standard console methods

    /**
     * @param {...any} args
     */
    debug(...args) {
        $debug(...styledArguments(args));
    }
    /**
     * @param {...any} args
     */
    error(...args) {
        switch (this.issueLevel) {
            case ISSUE_LEVELS.suppressed: {
                $groupCollapsed(...styledArguments(["suppressed"], ...ERROR_PREFIX));
                $trace(...args);
                $groupEnd();
                break;
            }
            case ISSUE_LEVELS.trace: {
                $trace(...styledArguments(args, ...ERROR_PREFIX));
                break;
            }
            case ISSUE_LEVELS.global: {
                $error(...styledArguments(args));
                break;
            }
            default: {
                $error(...args);
                break;
            }
        }
    }
    /**
     * @param {any} arg
     * @param {() => any} callback
     */
    group(title, callback) {
        $groupCollapsed(...styledArguments([title]));
        callback();
        $groupEnd();
    }
    /**
     * @param {...any} args
     */
    table(...args) {
        $table(...args);
    }
    /**
     * @param {...any} args
     */
    trace(...args) {
        $trace(...args);
    }
    /**
     * @param {...any} args
     */
    warn(...args) {
        switch (this.issueLevel) {
            case ISSUE_LEVELS.suppressed: {
                $groupCollapsed(...styledArguments(["suppressed"], ...WARNING_PREFIX));
                $trace(...args);
                $groupEnd();
                break;
            }
            case ISSUE_LEVELS.global: {
                $warn(...styledArguments(args));
                break;
            }
            default: {
                $warn(...args);
                break;
            }
        }
    }

    // Level-specific methods

    /**
     * @param {...any} args
     */
    logDebug(...args) {
        if (!this.canLog("debug")) {
            return;
        }
        $debug(...styledArguments(args, ...DEBUG_PREFIX));
    }
    /**
     * @param {import("./suite").Suite} suite
     */
    logSuite(suite) {
        if (!this.canLog("suites")) {
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
    }
    /**
     * @param {import("./test").Test} test
     */
    logTest(test) {
        if (!this.canLog("tests")) {
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
    }
    /**
     * @param {[label: string, color: string]} prefix
     * @param {...any} args
     */
    logTestEvent(prefix, ...args) {
        $log(...styledArguments(args, ...prefix));
    }
    /**
     * @param {...any} args
     */
    logRun(...args) {
        if (!this.canLog("runner")) {
            return;
        }
        $log(...styledArguments(args));
    }
    /**
     * @param {...any} args
     */
    logGlobal(...args) {
        $dir(...unstyledArguments(args));
    }

    // Other methods

    /**
     * @param {keyof typeof LOG_LEVELS} level
     */
    canLog(level) {
        return this.logLevel >= LOG_LEVELS[level];
    }
    /**
     * @param {keyof typeof ISSUE_LEVELS} level
     */
    setIssueLevel(level) {
        const restoreIssueLevel = () => {
            this.issueLevel = previous;
        };
        const previous = this.issueLevel;
        this.issueLevel = ISSUE_LEVELS[level];
        return restoreIssueLevel;
    }
    /**
     * @param {keyof typeof LOG_LEVELS} level
     */
    setLogLevel(level) {
        const restoreLogLevel = () => {
            this.logLevel = previous;
        };
        const previous = this.logLevel;
        this.logLevel = LOG_LEVELS[level];
        return restoreLogLevel;
    }
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
         * @param {() => any[]} getData
         */
        logRequest(getData) {
            if (!logger.canLog("debug")) {
                return;
            }
            const color = `color: #66e`;
            const args = [`${color}; font-weight: bold;`, color];
            const [dataHeader, ...otherData] = getData();
            if (!isNil(dataHeader)) {
                args.push(dataHeader);
            }
            $groupCollapsed(`-> %c${prefix}#${id}%c<${title}>`, ...args);
            for (const data of otherData) {
                $log(data);
            }
            $trace("Request trace:");
            $groupEnd();
        },
        /**
         * Response logger: orange.
         * @param {() => any[]} getData
         */
        logResponse(getData) {
            if (!logger.canLog("debug")) {
                return;
            }
            const color = `color: #f80`;
            const args = [`${color}; font-weight: bold;`, color];
            const [dataHeader, ...otherData] = getData();
            if (!isNil(dataHeader)) {
                args.push(dataHeader);
            }
            $groupCollapsed(`<- %c${prefix}#${id}%c<${title}>`, ...args);
            for (const data of otherData) {
                $log(data);
            }
            $trace("Response trace:");
            $groupEnd();
        },
    };
}

export const ISSUE_LEVELS = {
    /**
     * Suppressed:
     *
     * Condition:
     *  - typically: in "todo" tests where issues should be ignored
     *
     * Effect:
     *  - all errors and warnings are replaced by 'trace' calls
     */
    suppressed: 0,
    /**
     * Trace:
     *
     * Condition:
     *  - default level within a test run
     *
     * Effect:
     *  - warnings are left as-is;
     *  - errors are replaced by 'trace' calls, so that the actual console error
     *    comes from the test runner with a summary of all failed reasons.
     */
    trace: 1,
    /**
     * Global:
     *
     * Condition:
     *  - errors which should be reported globally but not interrupt the run
     *
     * Effect:
     *  - warnings are left as-is;
     *  - errors are wrapped with a "HOOT" prefix, as to not stop the current test
     *    run. Can typically be used to log test failed reasons.
     */
    global: 2,
    /**
     * Critical:
     *
     * Condition:
     *  - any error compromising the whole test run and should cancel or interrupt it
     *  - default level outside of a test run (import errors, module root errors, etc.)
     *
     * Effect:
     *  - warnings are left as-is;
     *  - errors are left as-is, as to tell the server test to stop the current
     *    (Python) test.
     */
    critical: 3,
};
export const LOG_LEVELS = {
    runner: 0,
    suites: 1,
    tests: 2,
    debug: 3,
};

export const logger = new Logger(
    urlParams.loglevel ?? LOG_LEVELS.runner,
    ISSUE_LEVELS.critical // by default, all errors are "critical", i.e. should abort the whole run
);
