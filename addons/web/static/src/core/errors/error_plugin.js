import { Plugin, useListener, useScope } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { isBrowserChrome, isBrowserFirefox } from "@web/core/browser/feature_detection";
import { registry } from "@web/core/registry";
import { services } from "@web/core/services";
import { useChildEnv } from "@web/owl2/utils";
import { completeUncaughtError, getErrorTechnicalName } from "./error_utils";

export class HTMLElementLoadingError extends Error {
    static message = "Error loading an HTML Element";
    constructor(message = HTMLElementLoadingError.message, event) {
        super(message);
        this.event = event;
    }
}

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

export class ErrorPlugin extends Plugin {
    // start as early as possible, to catch errors thrown while the other
    // plugins (and legacy services) start
    static sequence = 1;

    /** @private */
    scope = useScope();

    /**
     * @todo owl3 migration: error handlers still receive the legacy env as
     * first argument (they typically read `env.services`)
     * @private
     */
    env = useChildEnv();

    setup() {
        // the listeners are tied to the lifetime of the plugin: an error that
        // destroyed the app should either have been handled before the app went
        // down, or it is simply too late to act on it
        useListener(browser, "error", (ev) => this._onError(ev));
        useListener(browser, "unhandledrejection", (ev) => this._onUnhandledRejection(ev));
    }

    /**
     * Dispatches an uncaught error to the handlers of the "error_handlers"
     * registry, and logs its full traceback if relevant.
     *
     * @param {UncaughtError} uncaughtError
     */
    handleError(uncaughtError) {
        const shouldLogError = () =>
            // Only log errors that are relevant business-wise, following the heuristics:
            // Error.event and Error.traceback have been assigned
            // in one of the two error event listeners below.
            // If preventDefault was already executed on the event, don't log it.
            uncaughtError.event && !uncaughtError.event.defaultPrevented && uncaughtError.traceback;
        let originalError = uncaughtError;
        while (originalError instanceof Error && "cause" in originalError) {
            originalError = originalError.cause;
        }
        const runHandlers = () => {
            for (const [name, handler] of registry.category("error_handlers").getEntries()) {
                try {
                    if (handler(this.env, uncaughtError, originalError)) {
                        break;
                    }
                } catch (e) {
                    if (shouldLogError()) {
                        uncaughtError.event.preventDefault();
                        console.error(
                            `@web/core/error_plugin: handler "${name}" failed with "${
                                e.cause || e
                            }" while trying to handle:\n` + uncaughtError.traceback
                        );
                    }
                    return;
                }
            }
        };
        try {
            this.scope.run(runHandlers);
        } catch {
            // The plugin may have been destroyed in the meantime: completing an
            // uncaught error is asynchronous, so the app can go down between the
            // event and this call. It is not safe to run the handlers then, but
            // the traceback below is still worth logging.
        }
        if (shouldLogError()) {
            // Log the full traceback instead of letting the browser log the incomplete one
            uncaughtError.event.preventDefault();
            console.error(uncaughtError.traceback);
        }
    }

    /**
     * @private
     * @param {ErrorEvent} ev
     */
    async _onError(ev) {
        const { colno, error, filename, lineno, message } = ev;
        // We never want to display the following ResizeObserver error to the end-user. It
        // simply indicates that the browser delayed notifications to the next frame to prevent
        // infinite loop, which is how he's supposed to behave. However, it would be interesting
        // to track places from where this error could be thrown, and try to fix them.
        // https://trackjs.com/javascript-errors/resizeobserver-loop-completed-with-undelivered-notifications/
        const resizeObserverError = "ResizeObserver loop completed with undelivered notifications.";
        if (!(error instanceof Error) && message === resizeObserverError) {
            ev.preventDefault();
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
                const annotated = this.env.debug && this.env.debug.includes("assets");
                await completeUncaughtError(uncaughtError, error, annotated);
            }
        }
        uncaughtError.cause = error;
        this.handleError(uncaughtError);
    }

    /**
     * @private
     * @param {PromiseRejectionEvent} ev
     */
    async _onUnhandledRejection(ev) {
        let error = ev.reason;

        if (error && error.name === "AbortError") {
            // abort errors are normal and expected, we don't want to do anything
            ev.preventDefault();
            return;
        }
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
                `An unknown error occurred. This may be due to a Chrome extension meddling with Odoo.\n` +
                `(Opening your browser console might give you a hint on the error.)`;
        }
        const uncaughtError = new UncaughtPromiseError();
        uncaughtError.unhandledRejectionEvent = ev;
        uncaughtError.event = ev;
        uncaughtError.traceback = traceback;
        if (error instanceof Error) {
            error.errorEvent = ev;
            const annotated = this.env.debug && this.env.debug.includes("assets");
            await completeUncaughtError(uncaughtError, error, annotated);
        }
        uncaughtError.cause = error;
        this.handleError(uncaughtError);
    }
}

services.add(ErrorPlugin);
