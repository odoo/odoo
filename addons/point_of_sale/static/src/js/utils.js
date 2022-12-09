/** @odoo-module */
import { ConnectionAbortedError, ConnectionLostError } from "@web/core/network/rpc_service";

export function getFileAsText(file) {
    return new Promise((resolve, reject) => {
        if (!file) {
            reject();
        } else {
            const reader = new FileReader();
            reader.addEventListener("load", function () {
                resolve(reader.result);
            });
            reader.addEventListener("abort", reject);
            reader.addEventListener("error", reject);
            reader.readAsText(file);
        }
    });
}

/**
 * This global variable is used by nextFrame to store the timer and
 * be able to cancel it before another request for animation frame.
 */
let timer = null;

/**
 * Wait for the next animation frame to finish.
 */
export const nextFrame = () => {
    return new Promise((resolve) => {
        cancelAnimationFrame(timer);
        timer = requestAnimationFrame(() => {
            resolve();
        });
    });
};

export function isConnectionError(error) {
    const _error = identifyError(error);
    return _error instanceof ConnectionAbortedError || _error instanceof ConnectionLostError;
}

export function identifyError(error) {
    if (!error) {
        return error;
    }
    let errorToHandle;
    if (error.legacy) {
        // error.message is either RPCError or ConnectionLostError
        errorToHandle = error.message;
    } else if (error.event && error.event.type == "abort") {
        // Check if there is event and if the event type is abort.
        // If so, then it's supposed to be a ConnectionAbortedError,
        // however, it was stripped in the patch of rpc in `mapLegacyEnvToWowlEnv`.
        // We recreate the error object here so that in the actual handler,
        // ConnectionAbortedError and ConnectionLostError are handled properly.
        errorToHandle = new ConnectionAbortedError(error.message);
    } else if (error instanceof Error) {
        errorToHandle = error;
    }
    return errorToHandle || error;
}

/**
 * Creates a batched version of a callback so that all calls to it in the same
 * microtick will only call the original callback once.
 *
 * @param callback the callback to batch
 * @returns a batched version of the original callback
 */
export function batched(callback) {
    let called = false;
    return async () => {
        // This await blocks all calls to the callback here, then releases them sequentially
        // in the next microtick. This line decides the granularity of the batch.
        await Promise.resolve();
        if (!called) {
            called = true;
            // so that only the first call to the batched function calls the original callback.
            // Schedule this before calling the callback so that calls to the batched function
            // within the callback will proceed only after resetting called to false, and have
            // a chance to execute the callback again
            Promise.resolve().then(() => (called = false));
            callback();
        }
    };
}

/*
 * comes from o_spreadsheet.js
 * https://stackoverflow.com/questions/105034/create-guid-uuid-in-javascript
 * */
export function uuidv4() {
    // mainly for jest and other browsers that do not have the crypto functionality
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
        const r = (Math.random() * 16) | 0,
            v = c == "x" ? r : (r & 0x3) | 0x8;
        return v.toString(16);
    });
}
