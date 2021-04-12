/**
 * Low-level implementation of communication from the server with the use of
 * longpolling requests. Prefer using `bus.server_communication` instead because
 * browsers limit the number of requests that are allowed in parallel, so tricks
 * have been added in `bus.server_communication` to work with a single request
 * per browser and automatically sync other tabs.
 */
class LongpollingCommunication {

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
            console.log('start polling');
            this._currentRpcPromise = this.env.browser.fetch('/longpolling/poll', {
                body: JSON.stringify({
                    params: {
                        // TODO SEB handle new channels (only for livechat?)
                        channels: [],
                        last_bus_message_id: this._lastBusMessageId,
                    },
                }),
                headers: {
                    'Content-Type': 'application/json',
                },
                method: 'POST',
            });
            const catchFn = error => {
                console.error(error);
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
            await this._currentRpcPromise.then(async response => {
                if (response.ok) {
                    const jsonResponse = await response.json();
                    busMessages = jsonResponse.result;
                    console.log(busMessages);
                }
            }).catch(catchFn).finally(() => {
                this._currentRpcPromise = undefined;
            });
            if (Array.isArray(busMessages)) {
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
            console.log('end of loop', this._isActive);
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

const env = {
    browser: {
        fetch(...args) {
            return self.fetch(...args);
        },
    },
};
const longpollingCommunication = new LongpollingCommunication(env);
longpollingCommunication.start();

// TODO SEB there don't seem to be any disconnect event, but is it an issue to post messages on dead ports?
// const ports = new Set();
self.addEventListener('connect', function (ev) {
    console.log('service worker message');
    for (const port of ev.ports) {
        // ports.add(port);
        port.addEventListener('message', function (ev) {
            port.postMessage('worker received message', ev.data);
        });
        port.start();
        longpollingCommunication.registerHandler(busMessage => {
            port.postMessage({
                'type': 'bus_message',
                'payload': busMessage,
            });
        });
    }
});

self.addEventListener('install', function (ev) {
    console.log('service worker install');
    // ev.waitUntil(self.skipWaiting()); // Activate worker immediately
});

self.addEventListener('activate', function (ev) {
    console.log('service worker activate');
    // ev.waitUntil(self.clients.claim()); // Become available to all pages
});

self.addEventListener('message', function (ev) {
    console.log('service worker message', ev.ports, ev.data);
    ev.source.postMessage("Hi client");
});
