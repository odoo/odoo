/** @odoo-module */

import { formatTime } from "../hoot_utils";
import { urlParams } from "./url";

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const { console } = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @param {any[]} args
 */
const styledArguments = (args) => {
    const prefix = `%c[HOOT]%c`;
    const styles = [`color:#ff0080`, `color:inherit`];
    let firstArg = args.shift() ?? "";
    if (typeof firstArg === "function") {
        firstArg = firstArg();
    }
    if (typeof firstArg === "string") {
        args.unshift(`${prefix} ${firstArg}`, ...styles);
    } else {
        args.unshift(prefix, ...styles, firstArg);
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
            if (logger.level < logLevels.DEBUG) {
                return;
            }
            const color = `color: #66e`;
            const styles = [`${color}; font-weight: bold;`, color];
            console.groupCollapsed(`-> %c${prefix}#${id}%c<${title}>`, ...styles, await getData());
            console.trace("request trace");
            console.groupEnd();
        },
        /**
         * Response logger: orange.
         * @param {() => any} getData
         */
        async logResponse(getData) {
            if (logger.level < logLevels.DEBUG) {
                return;
            }
            const color = `color: #f80`;
            const styles = [`${color}; font-weight: bold;`, color];
            console.log(`<- %c${prefix}#${id}%c<${title}>`, ...styles, await getData());
        },
    };
}

export const logLevels = {
    RUNNER: 0,
    SUITES: 1,
    TESTS: 2,
    DEBUG: 3,
};

export const logger = {
    level: urlParams.loglevel ?? logLevels.RUNNER,

    // Standard console methods

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
        console.groupCollapsed(...styledArguments(args));
    },
    groupEnd() {
        console.groupEnd();
    },
    /**
     * @param {...any} args
     */
    table(...args) {
        console.table(...args);
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
        if (logger.level < logLevels.DEBUG) {
            return;
        }
        console.debug(...styledArguments(args));
    },
    async logRequest(getData) {
        if (logger.level < logLevels.DEBUG) {
            return;
        }
        const color = `color: #66e`;
        const styles = [`${color}; font-weight: bold;`, color];
        console.groupCollapsed(`-> %c${prefix}#${id}%c<${title}>`, ...styles, await getData());
        console.trace(); // Using console to reduce stack trace noise
        logger.groupEnd();
    },
    async logResponse(getData) {
        if (logger.level < logLevels.DEBUG) {
            return;
        }
        const color = `color: #f80`;
        const styles = [`${color}; font-weight: bold;`, color];
        console.groupCollapsed(`<- %c${prefix}#${id}%c<${title}>`, ...styles, await getData());
        console.trace(); // Using console to reduce stack trace noise
        logger.groupEnd();
    },
    /**
     * @param {import("./test").Test} test
     */
    logTest(test) {
        if (logger.level < logLevels.TESTS) {
            return;
        }
        const { fullName, lastResults } = test;
        console.log(
            ...styledArguments([
                `Test "${fullName}" passed`,
                lastResults.assertions.length,
                `assertions (time: ${formatTime(lastResults.duration)})`,
            ])
        );
    },
    /**
     * @param {import("./suite").Suite} suite
     */
    logSuite(suite) {
        if (logger.level < logLevels.SUITES) {
            return;
        }
        const args = [`"${suite.fullName}" ended`];
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
        console.log(...styledArguments(args));
    },
    /**
     * @param {...any} args
     */
    logRun(...args) {
        if (logger.level < logLevels.RUNNER) {
            return;
        }
        console.log(...styledArguments(args));
    },
    /**
     * @param {...any} args
     */
    logGlobal(...args) {
        console.dir(...unstyledArguments(args));
    },
};
