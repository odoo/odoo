// @ts-check

/** @module @web/core/errors/uncaught_errors - Base classes for uncaught errors intercepted by the error service */

import { getErrorTechnicalName } from "./error_utils";

/**
 * Uncaught Errors have 4 properties:
 * - name: technical name of the error (UncaughtError, ...)
 * - message: short user visible description of the issue ("Uncaught Cors Error")
 * - traceback: long description, possibly technical of the issue (such as a traceback)
 * - originalError: the error that was actually being caught. Note that it is not
 *      necessarily an error (for ex, if some code does throw "boom")
 */
/**
 * Base class for all uncaught errors intercepted by the error service.
 * Has `traceback` and `originalError` properties populated by error handlers.
 */
export class UncaughtError extends Error {
    /** @param {string} message */
    constructor(message) {
        super(message);
        this.name = getErrorTechnicalName(this);
        /** @type {string | null} */
        this.traceback = null;
    }
}

/** Uncaught synchronous JavaScript error (from window "error" event). */
export class UncaughtClientError extends UncaughtError {
    /** @param {string} [message] */
    constructor(message = "Uncaught Javascript Error") {
        super(message);
    }
}

/** Uncaught rejected Promise (from window "unhandledrejection" event). */
export class UncaughtPromiseError extends UncaughtError {
    /** @param {string} [message] */
    constructor(message = "Uncaught Promise") {
        super(message);
        /** @type {PromiseRejectionEvent | null} */
        this.unhandledRejectionEvent = null;
    }
}

/** Error originating from a third-party script (cross-origin, redacted details). */
export class ThirdPartyScriptError extends UncaughtError {
    /** @param {string} [message] */
    constructor(message = "Third-Party Script Error") {
        super(message);
    }
}
