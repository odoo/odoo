/** @odoo-module **/

import { browser } from "../browser/browser";
import { isBrowserChrome } from "../browser/feature_detection";
import { _lt } from "../l10n/translation";
import { registry } from "../registry";

/**
 * Uncaught Errors have 4 properties:
 * - name: technical name of the error (UncaughtError, ...)
 * - message: short user visible description of the issue ("Uncaught Cors Error")
 * - traceback: long description, possibly technical of the issue (such as a traceback)
 * - originalError: the error that was actually being caught. Note that it is not
 *      necessarily an error (for ex, if some code does throw "boom")
 */
export class UncaughtError extends Error {
    constructor(message, name) {
        super(message);
        this.name = name || "UncaughtError";
        this.originalError = null;
        this.traceback = null;
    }
}

export class UncaughtClientError extends UncaughtError {
    constructor(message = _lt("Uncaught Javascript Error")) {
        super(message, "UncaughtClientError");
    }
}

export class UncaughtPromiseError extends UncaughtError {
    constructor(message = _lt("Uncaught Promise")) {
        super(message, "UncaughtPromiseError");
        this.unhandledRejectionEvent = null;
    }
}

export class UncaughtCorsError extends UncaughtError {
    constructor(message = _lt("Uncaught CORS Error")) {
        super(message, "UncaughtCorsError");
    }
}

export const errorService = {
    start(env) {
        const handlers = registry
            .category("error_handlers")
            .getAll()
            .map((builder) => builder(env));

        function handleError(error, retry = true) {
            const services = env.services;
            if (!services.dialog || !services.notification || !services.rpc) {
                // here, the environment is not ready to provide feedback to the user.
                // We simply wait 1 sec and try again, just in case the application can
                // recover.
                if (retry) {
                    browser.setTimeout(() => {
                        handleError(error, false);
                    }, 1000);
                }
                return;
            }
            for (let handler of handlers) {
                if (handler(error, env)) {
                    break;
                }
            }
            env.bus.trigger("ERROR_DISPATCHED", error);
        }

        window.addEventListener("error", (ev) => {
            const { colno, error: eventError, filename, lineno, message } = ev;
            let err;
            if (!filename && !lineno && !colno) {
                err = new UncaughtCorsError();
                err.traceback = env._t(
                    `Unknown CORS error\n\n` +
                        `An unknown CORS error occured.\n` +
                        `The error probably originates from a JavaScript file served from a different origin.\n` +
                        `(Opening your browser console might give you a hint on the error.)`
                );
            } else {
                // ignore Chrome video internal error: https://crbug.com/809574
                if (!eventError && message === "ResizeObserver loop limit exceeded") {
                    return;
                }
                let stack = eventError ? eventError.stack : "";
                if (!isBrowserChrome()) {
                    // transforms the stack into a chromium stack
                    // Chromium stack example:
                    // Error: Mock: Can't write value
                    //     _onOpenFormView@http://localhost:8069/web/content/425-baf33f1/web.assets.js:1064:30
                    //     ...
                    stack = `${message}\n${stack}`.replace(/\n/g, "\n    ");
                }
                err = new UncaughtClientError();
                err.originalError = eventError;
                err.traceback = `${message}\n\n${filename}:${lineno}\n${env._t(
                    "Traceback"
                )}:\n${stack}`;
            }
            handleError(err);
        });

        window.addEventListener("unhandledrejection", (ev) => {
            const uncaughtError = ev.reason;
            const error = new UncaughtPromiseError();
            error.unhandledRejectionEvent = ev;
            error.originalError = uncaughtError;
            if (uncaughtError instanceof Error) {
                error.message = uncaughtError.message;
                error.traceback = uncaughtError.stack; // todo: do same computation as regular errors
            }
            handleError(error);
        });
    },
};

registry.category("services").add("error", errorService, { sequence: 1 });
