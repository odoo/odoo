import { browser } from "../browser/browser";
import { registry } from "../registry";
import { completeUncaughtError, getErrorTechnicalName } from "./error_utils";
import { isBrowserFirefox, isBrowserChrome } from "@web/core/browser/feature_detection";

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
    constructor(message = "Uncaught Javascript Error") {
        super(message);
    }
}

export class UncaughtPromiseError extends UncaughtError {
    constructor(message = "Uncaught Promise") {
        super(message);
        this.unhandledRejectionEvent = null;
    }
}

export class ThirdPartyScriptError extends UncaughtError {
    constructor(message = "Third-Party Script Error") {
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
            const isRedactedError = !filename && !lineno && !colno;
            const isThirdPartyScriptError =
                isRedactedError ||
                // Firefox doesn't hide details of errors occuring in third-party scripts, check origin explicitly
                (isBrowserFirefox() && new URL(filename).origin !== window.location.origin);
            // Don't display error dialogs for third party script errors unless we are in debug mode
            if (isThirdPartyScriptError && !odoo.debug) {
                return;
            }
            let uncaughtError;
            if (isRedactedError) {
                uncaughtError = new ThirdPartyScriptError();
                uncaughtError.traceback =
                    `An error whose details cannot be accessed by the Odoo framework has occurred.\n` +
                    `The error probably originates from a JavaScript file served from a different origin.\n` +
                    `The full error is available in the browser console.`;
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
            let traceback;
            if (isBrowserChrome() && ev instanceof CustomEvent && error === undefined) {
                // This fix is ad-hoc to a bug in the Honey Paypal extension
                // They throw a CustomEvent instead of the specified PromiseRejectionEvent
                // https://developer.mozilla.org/en-US/docs/Web/API/Window/unhandledrejection_event
                // Moreover Chrome doesn't seem to sandbox enough the extension, as it seems irrelevant
                // to have extension's errors in the main business page.
                // We want to ignore those errors as they are not produced by us, and are parasiting
                // the navigation. We do this according to the heuristic expressed in the if.
                if (!odoo.debug) {
                    return;
                }
                traceback =
                    `Uncaught unknown Error\n` +
                    `An unknown error occured. This may be due to a Chrome extension meddling with Odoo.\n` +
                    `(Opening your browser console might give you a hint on the error.)`;
            }
            const uncaughtError = new UncaughtPromiseError();
            uncaughtError.unhandledRejectionEvent = ev;
            uncaughtError.event = ev;
            uncaughtError.traceback = traceback;
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
