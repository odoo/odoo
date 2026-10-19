import { useService } from "@web/core/utils/hooks";
import { registry } from "../registry";

const errorHandlerRegistry = registry.category("error_handlers");

export class NonSecureContextError extends Error {
    name = "NonSecureContextError";
}

/**
 * @param {OdooEnv} env
 * @param {UncaughError} _error
 * @param {Error} originalError
 * @returns {boolean}
 */
export function NonSecureContextErrorHandler(env, _error, originalError) {
    const notification = useService("notification");

    if (originalError instanceof NonSecureContextError) {
        notification.add(originalError.message, { type: "danger", sticky: true });
        return true;
    }
}

errorHandlerRegistry.add("NonSecureContextErrorHandler", NonSecureContextErrorHandler, {
    sequence: 98,
});
