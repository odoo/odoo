/** @odoo-module **/

import { isBrowserFirefox } from "@web/core/browser/feature_detection";
import { browser } from "../browser/browser";
import { _lt } from "../l10n/translation";
import { registry } from "../registry";
import { annotateTraceback, formatTraceback, getErrorTechnicalName } from "./error_utils";

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

// FIXME: this error is misnamed and actually represends errors in third-party scripts
// rename this in master
export class UncaughtCorsError extends UncaughtError {
    constructor(message = _lt("Uncaught CORS Error")) {
        super(message);
    }
}

/**
 * @param {UncaughtError} uncaughtError
 * @param {Error} originalError
 * @returns {string}
 */
function combineErrorNames(uncaughtError, originalError) {
    const originalErrorName = getErrorTechnicalName(originalError);
    const uncaughtErrorName = getErrorTechnicalName(uncaughtError);
    if (originalErrorName === Error.name) {
        return uncaughtErrorName;
    } else {
        return `${uncaughtErrorName} > ${originalErrorName}`;
    }
}

/**
 * @param {import("../../env").OdooEnv} env
 * @param {UncaughtError} uncaughtError
 * @param {Error} originalError
 * @returns {Promise<void>}
 */
async function completeUncaughtError(env, uncaughtError, originalError) {
    uncaughtError.name = combineErrorNames(uncaughtError, originalError);
    if (env.debug.includes("assets")) {
        uncaughtError.traceback = await annotateTraceback(originalError);
    } else {
        uncaughtError.traceback = formatTraceback(originalError);
    }
    if (originalError.message) {
        uncaughtError.message = `${uncaughtError.message} > ${originalError.message}`;
    }
}

export const errorService = {
    start(env) {
        function handleError(error, originalError, retry = true) {
            const services = env.services;
            if (!services.dialog || !services.notification || !services.rpc) {
                // here, the environment is not ready to provide feedback to the user.
                // We simply wait 1 sec and try again, just in case the application can
                // recover.
                if (retry) {
                    browser.setTimeout(() => {
                        handleError(error, originalError, false);
                    }, 1000);
                }
                return;
            }
            for (let handler of registry.category("error_handlers").getAll()) {
                if (handler(env, error, originalError)) {
                    break;
                }
            }
        }

        browser.addEventListener("error", async (ev) => {
            const { colno, error: originalError, filename, lineno, message } = ev;
            const errorsToIgnore = [
                // Ignore some unnecessary "ResizeObserver loop limit exceeded" error in Firefox.
                "ResizeObserver loop completed with undelivered notifications.",
                // ignore Chrome video internal error: https://crbug.com/809574
                "ResizeObserver loop limit exceeded"
            ]
            if (!originalError && errorsToIgnore.includes(message)) {
                return;
            }
            const isRedactedError = !filename && !lineno && !colno;
            const isThirdPartyScriptError =
                isRedactedError ||
                // Firefox doesn't hide details of errors occuring in third-party scripts, check origin explicitly
                (isBrowserFirefox() && new URL(filename).origin !== window.location.origin);
            // Don't display error dialogs to public users for third party script errors unless we are in debug mode
            if (
                isThirdPartyScriptError &&
                !(env.services.user && env.services.user.userId) &&
                !odoo.debug
            ) {
                return;
            }
            let uncaughtError;
            if (isRedactedError) {
                uncaughtError = new UncaughtCorsError();
                uncaughtError.traceback = env._t(
                    `Unknown CORS error\n\n` +
                        `An unknown CORS error occured.\n` +
                        `The error probably originates from a JavaScript file served from a different origin.\n` +
                        `(Opening your browser console might give you a hint on the error.)`
                );
            } else {
                uncaughtError = new UncaughtClientError();
                await completeUncaughtError(env, uncaughtError, originalError);
            }
            handleError(uncaughtError, originalError);
        });

        browser.addEventListener("unhandledrejection", async (ev) => {
            const originalError = ev.reason;
            const uncaughtError = new UncaughtPromiseError();
            uncaughtError.unhandledRejectionEvent = ev;
            if (originalError instanceof Error) {
                await completeUncaughtError(env, uncaughtError, originalError);
            }
            handleError(uncaughtError, originalError);
        });
    },
};

registry.category("services").add("error", errorService, { sequence: 1 });
