odoo.define('point_of_sale.utils', function (require) {
    'use strict';

    const { EventBus } = owl.core;
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
        const _error = identifyError(error);
        return _error instanceof ConnectionAbortedError || _error instanceof ConnectionLostError;
    }

    function identifyError(error) {
        if (!error) return error;
        let errorToHandle;
        if (error.legacy) {
            // error.message is either RPCError or ConnectionLostError
            errorToHandle = error.message;
        } else if (error.event && error.event.type == 'abort') {
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

    return { getFileAsText, nextFrame, posbus: new EventBus(), identifyError, isConnectionError };
});
