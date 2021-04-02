/** @odoo-module **/

/**
 * Low-level implementation of communication from the server with the use of
 * longpolling requests. Prefer using `bus.server_communication` instead because
 * browsers limit the number of requests that are allowed in parallel, so tricks
 * have been added in `bus.server_communication` to work with a single request
 * per browser and automatically sync other tabs.
 */
export class LongpollingCommunication {

    constructor(env) {
        this.env = env;
        /**
         * Determines whether this longpolling service is currently active.
         */
        this._isActive;
        /**
         * Determines whether a test is in progress. longpolling is not
         * available in tests.
         */
        this._isInTestMode = false;
        /**
         * Reference to the current RPC promise (if any). Useful to be able to
         * cancel it if the longpolling is disabled or if any param has to be
         * updated.
         */
        this._currentRpcPromise;
        /**
         * Reference to the current retry `setTimeout` identifier. Useful to be
         * able to cancel it if the longpolling.
         */
        this._retryTimeoutId;
        /**
         * Id of the last bus message that was fetched. Useful to only fetch new
         * bus messages.
         */
        this._lastBusMessageId;
        /**
         * Set of currently registered handlers.
         */
        this._handlers = new Set();
    }

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------

    /**
     * Registers a new handler.
     *
     * @param {function} handler will be called when a bus message is received
     *  from the server. It will be called with one param: the message that was
     *  received from the server.
     */
    registerHandler(handler) {
        this._handlers.add(handler);
    }

    /**
     * Starts polling. Has no effect if polling is already in progress.
     *
     * @param {integer} [lastBusMessageId=0] bus messages that have a smaller or
     *  equal id will be ignored.
     */
    async start(lastBusMessageId = 0) {
        if (this._isInTestMode) {
            return;
        }
        if (this._isActive) {
            return;
        }
        this._isActive = true;
        this._lastBusMessageId = lastBusMessageId;
        while (this._isActive) {
            // Isolate RPC result handling and error handling outside of its
            // try/catch/finally block to avoid incorrectly catching exceptions
            // that are not RPC related.
            let hasError;
            let busMessages;
            this._currentRpcPromise = this.env.services.rpc({
                params: {
                    // TODO SEB handle new channels (only for livechat?)
                    channels: [],
                    last_bus_message_id: this._lastBusMessageId,
                },
                route: '/longpolling/poll',
            }, {
                shadow: true,
                timeout: 60000,
            });
            const catchFn = error => {
                // ajax.js is using exception to communicate actual information
                if (error && error.message === "XmlHttpRequestError abort") {
                    // Necessary to prevent other parts of the code from
                    // handling this as a "business exception".
                    // Note that Firefox will still report this as an
                    // "Uncaught (in promise)" even though it is caught here.
                    error.event.preventDefault();
                } else if (error && error.message && error.message.data && error.message.data.arguments && error.message.data.arguments[0] === "bus.Bus not available in test mode") {
                    // TODO SEB detect test mode beforehand and don't even start polling
                    // or even better, bus should be available in test mode...
                    this._isInTestMode = true;
                    this.stop();
                    // Necessary to prevent other parts of the code from
                    // handling this as a "business exception".
                    // Note that Firefox will still report this as an
                    // "Uncaught (in promise)" even though it is caught here.
                    error.event.preventDefault();
                } else {
                    console.error(error);
                    hasError = true;
                }
            };
            await this._currentRpcPromise.then(res => {
                busMessages = res;
            }).guardedCatch(catchFn).catch(catchFn).finally(() => {
                this._currentRpcPromise = undefined;
            });
            if (busMessages) {
                for (const busMessage of busMessages) {
                    this._lastBusMessageId = Math.max(busMessage.id, this._lastBusMessageId);
                    this._notifyHandlers(busMessage);
                }
            }
            if (hasError) {
                // Randomize the retry delay between 10s and 30s to avoid
                // deny of service if there are many other clients that would
                // otherwise all retry at the same time.
                const delay = 10000 + Math.random() * 20000;
                await new Promise(resolve => {
                    this._retryTimeoutId = setTimeout(resolve, delay);
                });
            }
        }
    }

    /**
     * Stops polling.
     */
    stop() {
        this._isActive = false;
        clearTimeout(this._retryTimeoutId);
        if (this._currentRpcPromise) {
            this._currentRpcPromise.abort();
        }
    }

    /**
     * Unregisters an existing handler.
     *
     * @param {function} handler to unregister
     */
    unregisterHandler(handler) {
        this._handlers.delete(handler);
    }

    // -------------------------------------------------------------------------
    // Private
    // -------------------------------------------------------------------------

    /**
     * Notifies the currently registered handlers.
     *
     * @param {*} busMessage
     */
    _notifyHandlers(busMessage) {
        for (const handler of this._handlers) {
            // Isolate each handler on its own stack to prevent any
            // potential issue in one of them to influence any
            // other. This also allows to restart the longpolling
            // request as soon as possible, without having to wait
            // for all handlers to terminate.
            setTimeout(() => handler(busMessage));
        }
    }

}

export const longpollingCommunicationService = {
    name: 'bus.longpolling_communication',
    dependencies: ['rpc'],
    deploy: env => new LongpollingCommunication(env),
};
