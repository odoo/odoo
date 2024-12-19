import { browser } from "../browser/browser";
import { registry } from "../registry";
import { completeUncaughtError, getErrorTechnicalName } from "./error_utils";
import { isBrowserFirefox, isBrowserChrome } from "@web/core/browser/feature_detection";
import { user } from "@web/core/user";

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

/**
 * Service to handle uncaught errors happening for internal users.
 *
 * Beware that this service is *not* meant to be used to show non-internal users
 * functional problems in their flow (e.g. a product that could not be added to
 * their cart because it was not available anymore). For that, catch the error
 * explicitly by yourself and display what you need. The service is still
 * enabled for those users anyway, but only to log more info in the console.
 */
export const errorService = {
    start(env) {
        async function handleError(uncaughtError) {
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

            // Note that we do this potentially-rpc-making request only when the
            // first error is caught. Indeed, we may not want to load that info
            // always, especially on the website side. Also, we could not really
            // consider shutting down the whole service from the start as we
            // still want extra info being logged in the console, always.
            //
            // Notice that adding this asynchronicity here is technically a
            // "mistake" as the error handlers will now not have the opportunity
            // to actually `preventDefault` the error. However, it was decided
            // that actually preventingDefault the error has no utility except
            // checking the `defaultPrevented` flag at the end of this function,
            // so the fact that this is done asynchronously does not matter.
            // Also, the caller of this function is already doing it in an async
            // way in most cases anyway.
            let shouldHandleErrors = false;
            try {
                const isInternalUser = await user.hasGroup('base.group_user');
                // Note: we could have coded it in such a way the user group
                // call is not made in case we are in debug/test mode, but it
                // was chosen to make it so this call is made in that case too
                // so the technical flow is as much the same as possible,
                // especially keeping the same asynchronicity for the following
                // parts handling the error (to not be able to actually prevent
                // error default sometimes and sometimes not).
                shouldHandleErrors = Boolean(
                    isInternalUser
                    || odoo.debug
                    // Note: we enable the handling of errors in testing mode
                    // because otherwise, tests fail because of console errors
                    // that would otherwise be silenced. As a visitor, it would
                    // just get logged in the console with no other consequence.
                    //
                    // TODO there should be a better way to find this info.
                    || document.querySelector('script[src^="/web/assets/"][src*="web.__assets_tests_call__"]')
                );
            } catch (e) {
                console.error(
                    `A crash occurred upon checking the user group while handling the ${uncaughtError} error:`,
                    e
                );
                // FIXME waiting for discussion with AAB
            }
            // In case the user is not an internal user, we choose to not show
            // him traceback dialogs when an error occurs, by simply ignoring
            // all defined error handlers. If a system is needed to show visitor
            // errors, simply catch those errors and do what you need.
            // A good example of why this is a good idea: if a visitor uses a
            // browser extension that makes the website JS code crash... we
            // cannot expect website owners to warn visitors about it and we may
            // not have the possibility to fix all errors induced by extensions.
            if (shouldHandleErrors) {
                for (const [name, handler] of registry.category("error_handlers").getEntries()) {
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
                                }" while trying to handle:\n` + uncaughtError.traceback
                            );
                        }
                        return;
                    }
                }
            } else if (originalError) {
                // In the case of non-internal user, we did not let any handler
                // the opportunity to do something with the original error. So
                // best log it too and its common data if any, even if it is too
                // much or redundant.
                console.error(originalError, originalError.data, originalError.message);
            }

            // Either way, as explained above, since we do not let any event
            // handler `preventDefault` errors when the user is not an internal
            // one, the following code may log more in the console in that case.
            // This was judged acceptable and potentially even better: why not
            // always showing what we can in the console when we did not let any
            // code the opportunity to show any info another way.
            if (shouldLogError()) {
                // Log the full traceback instead of letting the browser log the
                // incomplete one
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
