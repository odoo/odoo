/** @odoo-module **/

import { browser } from "../browser/browser";
import { _t } from "@web/core/l10n/translation";
import { registry } from "../registry";
import { completeUncaughtError, getErrorTechnicalName } from "./error_utils";
import { isIOS, isBrowserSafari } from "@web/core/browser/feature_detection";

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
    constructor(message = _t("Uncaught Javascript Error")) {
        super(message);
    }
}

export class UncaughtPromiseError extends UncaughtError {
    constructor(message = _t("Uncaught Promise")) {
        super(message);
        this.unhandledRejectionEvent = null;
    }
}

export class UncaughtCorsError extends UncaughtError {
    constructor(message = _t("Uncaught CORS Error")) {
        super(message);
    }
}

export const errorService = {
    start(env) {
        function handleError(uncaughtError, retry = true) {
            let originalError = uncaughtError;
            while (originalError instanceof Error && "cause" in originalError) {
                originalError = originalError.cause;
            }
            for (const [name, handler] of registry.category("error_handlers").getEntries()) {
                try {
                    if (handler(env, uncaughtError, originalError)) {
                        break;
                    }
                } catch (e) {
                    console.error(
                        `A crash occured in error handler ${name} while handling ${uncaughtError}:`,
                        e
                    );
                    return;
                }
            }
            if (
                uncaughtError.event &&
                !uncaughtError.event.defaultPrevented &&
                uncaughtError.traceback
            ) {
                // Log the full traceback instead of letting the browser log the incomplete one
                uncaughtError.event.preventDefault();
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
                if ((isIOS() || isBrowserSafari()) && odoo.debug !== "assets") {
                    // In Safari 16.4+ (as of Jun 14th 2023), an error occurs
                    // when going back and forward through the browser when the
                    // cache is enabled. A feedback has been reported but in the
                    // meantime, hide any script error in these versions.
                    return;
                }
                uncaughtError = new UncaughtCorsError();
                uncaughtError.traceback = _t(
                    `Unknown CORS error\n\n` +
                        `An unknown CORS error occured.\n` +
                        `The error probably originates from a JavaScript file served from a different origin.\n` +
                        `(Opening your browser console might give you a hint on the error.)`
                );
            } else {
                uncaughtError = new UncaughtClientError();
                uncaughtError.event = ev;
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
            uncaughtError.event = ev;
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
