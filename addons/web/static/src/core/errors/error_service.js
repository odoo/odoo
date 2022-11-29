/** @odoo-module **/

import { browser } from "../browser/browser";
import { _lt } from "../l10n/translation";
import { registry } from "../registry";
import { completeUncaughtError, getErrorTechnicalName } from "./error_utils";

/**
 * Uncaught Errors have 4 properties:
 * - name: technical name of the error (UncaughtError, ...)
 * - message: short user visible description of the issue ("Uncaught Cors Error")
 * - traceback: long description, possibly technical of the issue (such as a traceback)
 * - originalError: the error that was actually being caught. Note that it is not
 *      necessarily an error (for ex, if some code does throw "boom")
 */
export class UncaughtError extends Error {
    constructor(message) {
        super(message);
        this.name = getErrorTechnicalName(this);
        this.traceback = null;
    }
}

export class UncaughtClientError extends UncaughtError {
    constructor(message = _lt("Uncaught Javascript Error")) {
        super(message);
    }
}

export class UncaughtPromiseError extends UncaughtError {
    constructor(message = _lt("Uncaught Promise")) {
        super(message);
        this.unhandledRejectionEvent = null;
    }
}

export class UncaughtCorsError extends UncaughtError {
    constructor(message = _lt("Uncaught CORS Error")) {
        super(message);
    }
}

export const errorService = {
    start(env) {
        function handleError(uncaughtError, retry = true) {
            let originalError = uncaughtError;
            while (originalError && "cause" in originalError) {
                originalError = originalError.cause;
            }
            const services = env.services;
            if (!services.dialog || !services.notification || !services.rpc) {
                // here, the environment is not ready to provide feedback to the user.
                // We simply wait 1 sec and try again, just in case the application can
                // recover.
                if (retry) {
                    browser.setTimeout(() => {
                        handleError(uncaughtError, false);
                    }, 1000);
                }
                return;
            }
            for (const handler of registry.category("error_handlers").getAll()) {
                if (handler(env, uncaughtError, originalError)) {
                    break;
                }
            }
            if (
                originalError instanceof Error &&
                originalError.errorEvent &&
                !originalError.errorEvent.defaultPrevented
            ) {
                // Log the full traceback instead of letting the browser log the incomplete one
                originalError.errorEvent.preventDefault();
                console.error(uncaughtError.traceback);
            }
        }

        browser.addEventListener("error", async (ev) => {
            const { colno, error, filename, lineno, message } = ev;
            const errorsToIgnore = [
                // Ignore some unnecessary "ResizeObserver loop limit exceeded" error in Firefox.
                "ResizeObserver loop completed with undelivered notifications.",
                // ignore Chrome video internal error: https://crbug.com/809574
                "ResizeObserver loop limit exceeded",
            ];
            if (!error && errorsToIgnore.includes(message)) {
                return;
            }
            let uncaughtError;
            if (!filename && !lineno && !colno) {
                uncaughtError = new UncaughtCorsError();
                uncaughtError.traceback = env._t(
                    `Unknown CORS error\n\n` +
                        `An unknown CORS error occured.\n` +
                        `The error probably originates from a JavaScript file served from a different origin.\n` +
                        `(Opening your browser console might give you a hint on the error.)`
                );
            } else {
                uncaughtError = new UncaughtClientError();
                if (error instanceof Error) {
                    error.errorEvent = ev;
                    const annotated = env.debug && env.debug.includes("assets");
                    await completeUncaughtError(uncaughtError, error, annotated);
                }
            }
            uncaughtError.cause = error;
            handleError(uncaughtError);
        });

        browser.addEventListener("unhandledrejection", async (ev) => {
            const error = ev.reason;
            const uncaughtError = new UncaughtPromiseError();
            uncaughtError.unhandledRejectionEvent = ev;
            if (error instanceof Error) {
                error.errorEvent = ev;
                const annotated = env.debug && env.debug.includes("assets");
                await completeUncaughtError(uncaughtError, error, annotated);
            }
            uncaughtError.cause = error;
            handleError(uncaughtError);
        });
    },
};

registry.category("services").add("error", errorService, { sequence: 1 });
