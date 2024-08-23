/** @odoo-module */

import { registry } from "@web/core/registry";
import { UncaughtPromiseError } from "@web/core/errors/error_service";
import { ConnectionLostError, ConnectionAbortedError, RPCError } from "@web/core/network/rpc_service";

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

    if (originalError instanceof ConnectionLostError || originalError instanceof ConnectionAbortedError) {
        return;
    }

    const payload = {
        name: error.name,
        message: error.message,
        traceback: error.traceback,
        user_context: stringifyCircularJsonObjects(env.services.user),
        action_context: stringifyCircularJsonObjects(env.services.action.currentController),
        source: "Frontend",
    };

    if (originalError instanceof RPCError) {
        if (originalError.code == 100) {
            return; // Odoo session expired, we can't create records.
        }
        payload.traceback = originalError.data.debug;
        payload.message = originalError.data.message;
        payload.name = originalError.name + " > " + originalError.data.name;
        payload.source = "Backend";
    }

    try {
        env.services.orm.silent.create("exception_tracker.exception", [payload]);
    } catch(e) {
        console.error("Couldn't store exception: ", e.message);
        console.error("The error to log was: ", error, originalError);
    }
    return false;
}

errorHandlerRegistry.add("error_tracker", registerError, { sequence: 1 });
