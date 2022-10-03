odoo.define('point_of_sale.utils', function (require) {
    'use strict';

    const { ConnectionAbortedError, ConnectionLostError } = require('@web/core/network/rpc_service');

    function getFileAsText(file) {
        return new Promise((resolve, reject) => {
            if (!file) {
                reject();
            } else {
                const reader = new FileReader();
                reader.addEventListener('load', function () {
                    resolve(reader.result);
                });
                reader.addEventListener('abort', reject);
                reader.addEventListener('error', reject);
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
    const nextFrame = () => {
        return new Promise((resolve) => {
            cancelAnimationFrame(timer);
            timer = requestAnimationFrame(() => {
                resolve();
            });
        });
    };

    function isConnectionError(error) {
        return error instanceof ConnectionAbortedError || error instanceof ConnectionLostError;
    }

    /**
     * Creates a batched version of a callback so that all calls to it in the same
     * microtick will only call the original callback once.
     *
     * @param callback the callback to batch
     * @returns a batched version of the original callback
     */
    function batched(callback) {
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
                Promise.resolve().then(() => called = false);
                callback();
            }
        };
    }

    /*
     * comes from o_spreadsheet.js
     * https://stackoverflow.com/questions/105034/create-guid-uuid-in-javascript
     * */
    function uuidv4() {
        // mainly for jest and other browsers that do not have the crypto functionality
        return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
            let r = (Math.random() * 16) | 0, v = c == "x" ? r : (r & 0x3) | 0x8;
            return v.toString(16);
        });
    };

    return { getFileAsText, nextFrame, isConnectionError, batched, uuidv4 };
});
