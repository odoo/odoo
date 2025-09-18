// @ts-check

/** @module @web/services/error_service - Global error/rejection interceptor with UncaughtError classification and handler pipeline */

import { browser } from "@web/core/browser/browser";
import { isBrowserChrome, isBrowserFirefox } from "@web/core/browser/feature_detection";
import { completeUncaughtError } from "@web/core/errors/error_utils";
import {
    ThirdPartyScriptError,
    UncaughtClientError,
    UncaughtError,
    UncaughtPromiseError,
} from "@web/core/errors/uncaught_errors";
import { registry } from "@web/core/registry";

// Re-export for backward compatibility — canonical location is @web/core/errors/uncaught_errors
export {
    ThirdPartyScriptError,
    UncaughtClientError,
    UncaughtError,
    UncaughtPromiseError,
};

/** Error raised when an HTML element (img, script, iframe) fails to load. */
class HTMLElementLoadingError extends Error {
    static message = "Error loading an HTML Element";
    /**
     * @param {string} [message]
     * @param {Event} [event] - the DOM error event
     */
    constructor(message = HTMLElementLoadingError.message, event) {
        super(message);
        /** @type {Event | undefined} */
        this.event = event;
    }
}

/**
 * Global error handling service. Listens for uncaught errors and unhandled
 * promise rejections, classifies them, and dispatches to registered error handlers.
 */
export const errorService = {
    /**
     * @param {import("@web/env").OdooEnv} env
     */
    start(env) {
        /**
         * Dispatch an uncaught error to all registered error handlers.
         * @param {UncaughtError} uncaughtError
         * @param {boolean} [retry=true]
         */
        function handleError(/** @type {any} */ uncaughtError, retry = true) {
            function shouldLogError() {
                // Only log errors that are relevant business-wise, following the heuristics:
                // Error.event and Error.traceback have been assigned
                // in one of the two error event listeners below.
                // If preventDefault was already executed on the event, don't log it.
                return (
                    uncaughtError.event &&
                    !uncaughtError.event.defaultPrevented &&
                    uncaughtError.traceback
                );
            }
            let originalError = uncaughtError;
            while (originalError instanceof Error && "cause" in originalError) {
                originalError = originalError.cause;
            }
            for (const [name, handler] of registry
                .category("error_handlers")
                .getEntries()) {
                try {
                    if (handler(env, uncaughtError, originalError)) {
                        break;
                    }
                } catch (e) {
                    if (shouldLogError()) {
                        uncaughtError.event.preventDefault();
                        console.error(
                            `@web/core/error_service: handler "${name}" failed with "${
                                e.cause || e
                            }" while trying to handle:\n` + uncaughtError.traceback,
                        );
                    }
                    return;
                }
            }
            if (shouldLogError()) {
                // Log the full traceback instead of letting the browser log the incomplete one
                uncaughtError.event.preventDefault();
                console.error(uncaughtError.traceback);
            }
        }

        browser.addEventListener("error", async (ev) => {
            const { colno, error, filename, lineno, message } = ev;
            // We never want to display the following ResizeObserver error to the end-user. It
            // simply indicates that the browser delayed notifications to the next frame to prevent
            // infinite loop, which is how he's supposed to behave. However, it would be interesting
            // to track places from where this error could be thrown, and try to fix them.
            // https://trackjs.com/javascript-errors/resizeobserver-loop-completed-with-undelivered-notifications/
            const resizeObserverError =
                "ResizeObserver loop completed with undelivered notifications.";
            if (!(error instanceof Error) && message === resizeObserverError) {
                ev.preventDefault();
                return;
            }
            const isRedactedError = !filename && !lineno && !colno;
            const isThirdPartyScriptError =
                isRedactedError ||
                // Firefox doesn't hide details of errors occuring in third-party scripts, check origin explicitly
                (isBrowserFirefox() &&
                    new URL(filename).origin !== window.location.origin);
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
                /** @type {any} */ (uncaughtError).event = ev;
                if (error instanceof Error) {
                    /** @type {any} */ (error).errorEvent = ev;
                    const annotated = env.debug && env.debug.includes("assets");
                    await completeUncaughtError(uncaughtError, error, annotated);
                }
            }
            uncaughtError.cause = error;
            handleError(uncaughtError);
        });

        browser.addEventListener("unhandledrejection", async (ev) => {
            let error = ev.reason;

            if (error && error.type === "error" && "eventPhase" in error) {
                // https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement/error_event
                // See also MDN's img, script and iframe docs. The error Event *doesn't* bubble.
                // We sometimes reject a promise with the Event dispatched by the "error" handler
                // of an HTMLElement. If the code throwing that at us doesn't wrap the event in an
                // actual Error, there is no reason to do more than the spec: we do not handle
                // this error bubbling to us via the Promise being rejected.
                if (!error.bubbles) {
                    ev.preventDefault();
                    return;
                }
                // If for some reason the error Event bubbles then do something
                // a bit meaningful.
                let message;
                if (error.target) {
                    message = `${HTMLElementLoadingError.message}: ${error.target.nodeName}`;
                }
                error = new HTMLElementLoadingError(message, error);
            }

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
            /** @type {any} */ (uncaughtError).event = ev;
            uncaughtError.traceback = traceback;
            if (error instanceof Error) {
                /** @type {any} */ (error).errorEvent = ev;
                const annotated = env.debug && env.debug.includes("assets");
                await completeUncaughtError(uncaughtError, error, annotated);
            }
            uncaughtError.cause = error;
            handleError(uncaughtError);
        });
    },
};

registry.category("services").add("error", errorService, { sequence: 1 });
