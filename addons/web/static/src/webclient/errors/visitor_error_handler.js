// @ts-check

/** @module @web/webclient/errors/visitor_error_handler - Error handler that swallows all tracebacks for non-internal (portal/public) users */

import { registry } from "@web/core/registry";
import { user } from "@web/services/user";
import { session } from "@web/session";

/**
 * We don't want to show tracebacks to non internal users. This handler swallows
 * all errors if we're not an internal user (except in debug or test mode).
 */
/**
 * Swallow all errors for non-internal users (except in debug/test mode).
 * @param {import("@odoo/owl").OdooEnv} env
 * @param {Error} error - The wrapped error
 * @param {Error} originalError - The original unwrapped error
 * @returns {true | undefined} `true` to swallow the error, `undefined` to pass through
 */
export function swallowAllVisitorErrors(env, error, originalError) {
    if (!user.isInternalUser && !odoo.debug && !session.test_mode) {
        return true;
    }
}

if (user.isInternalUser === undefined) {
    // Only warn about this while on the "frontend": the session info might
    // apparently not be present in all Odoo screens at the moment... TODO ?
    if (session.is_frontend) {
        console.warn(
            "isInternalUser information is required for this handler to work. It must be available in the page.",
        );
    }
} else {
    registry
        .category("error_handlers")
        .add("swallowAllVisitorErrors", swallowAllVisitorErrors, {
            sequence: 0,
        });
}
