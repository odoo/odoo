/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * @typedef {import("../env").OdooEnv} OdooEnv
 * @typedef {import("../core/errors/error_service").UncaughtPromiseError} UncaughtPromiseError
 */

// -----------------------------------------------------------------------------
// Legacy Promise error handling
// -----------------------------------------------------------------------------

/**
 * @param {OdooEnv} env
 * @param {Error} error
 * @param {Error} originalError
 * @returns {boolean}
 */
function legacyRejectPromiseHandler(env, error, originalError) {
    if (error.name.startsWith("UncaughtPromiseError")) {
        const isLegitError = originalError && originalError instanceof Error;
        const isLegacyRPC = originalError && originalError.legacy;
        if (!isLegitError && !isLegacyRPC) {
            // we consider that a code throwing something that is not an error is
            // a case where it is meant as an asynchronous control flow (as legacy
            // code is sadly doing). For now, we just want to consider this as a non
            // error, so we prevent default it.
            error.unhandledRejectionEvent.preventDefault();
            return true;
        }
    }
    return false;
}

registry
    .category("error_handlers")
    .add("legacyRejectPromiseHandler", legacyRejectPromiseHandler, { sequence: 1 });
