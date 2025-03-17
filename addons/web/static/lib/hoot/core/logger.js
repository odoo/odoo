/** @odoo-module */

import { formatTime, stringify } from "../hoot_utils";
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
        console.error(...styledArguments(args));
    },
    /**
     * @param {...any} args
     */
    groupCollapsed(...args) {
        $groupCollapsed(...styledArguments(args));
    },
    /**
     * @param {...any} args
     */
    warn(...args) {
        console.warn(...styledArguments(args));
    },

    // Level-specific methods

    /**
     * @param {...any} args
     */
    logDebug(...args) {
        if (logger.level < LOG_LEVELS.debug) {
            return;
        }
        $debug(...styledArguments(args, "DEBUG", "#ffb000"));
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
                `Test ${stringify(fullName)} passed`,
                lastResults.counts.assertion || 0,
                `assertions (time: ${formatTime(lastResults.duration)})`,
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
            withArgs.push(suite.reporting.passed, "passed");
        }
        if (suite.reporting.failed) {
            withArgs.push(suite.reporting.failed, "failed");
        }
        if (suite.reporting.skipped) {
            withArgs.push(suite.reporting.skipped, "skipped");
        }
        if (withArgs.length) {
            args.push("(", ...withArgs, ")");
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
};
