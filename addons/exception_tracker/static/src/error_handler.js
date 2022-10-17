/** @odoo-module */

import { registry } from "@web/core/registry";
import { UncaughtPromiseError } from "@web/core/errors/error_service";
import { RPCError } from "@web/core/network/rpc_service";

const errorHandlerRegistry = registry.category("error_handlers");

const getCircularReplacer = () => {
    const seen = new WeakSet();
    return (key, value) => {
        if (typeof value === "object" && value !== null) {
            if (seen.has(value)) {
                return;
            }
            seen.add(value);
        }
        return value;
    };
};

function stringifyCircularJsonObjects(obj) {
    return JSON.stringify(obj, getCircularReplacer(), 2);
}

function registerError(env, error, originalError) {

    const payload = {
        name: error.name,
        message: error.message,
        traceback: error.traceback,
        user_context: stringifyCircularJsonObjects(env.services.user),
        action_context: stringifyCircularJsonObjects(env.services.action.currentController),
    };

    if (error instanceof UncaughtPromiseError && originalError instanceof RPCError) {
        payload.traceback = originalError.data.debug;
        payload.message = originalError.data.message;
        payload.name = originalError.name + " > " + originalError.data.name;
    }

    env.services.orm.silent.create("exception_tracker.exception", [payload]);
    return false;
}

errorHandlerRegistry.add("error_tracker", registerError, { sequence: 1 });
