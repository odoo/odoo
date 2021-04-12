/** @odoo-module **/

/**
 * Low-level implementation of communication from the server with the use of a
 * SharedWorker. Prefer using `bus.server_communication` instead because some
 * browsers may not support SharedWorker, so tricks have been added in
 * `bus.server_communication` to work around it if necessary.
 */
export class SharedWorkerCommunication {

    constructor(env) {
        this.env = env;
        /**
         * Determines whether this shared worker service is currently active.
         */
        this._isActive;
        /**
         * Set of currently registered handlers.
         */
        this._handlers = new Set();
        /**
         * Reference to SharedWorker.
         */
        this._sharedWorker;
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
     * Starts. Has no effect if it is already in progress.
     */
    async start(lastBusMessageId = 0) {
        if (this._isActive) {
            return;
        }
        // TODO replace window by env.browser
        if (!this._sharedWorker) {
            navigator.serviceWorker.register('/server_communication_shared_worker.js').then(function(registration) {
                // Registration was successful
                console.log('ServiceWorker registration successful with scope: ', registration.scope);
            }, function(err) {
                // registration failed :(
                console.log('ServiceWorker registration failed: ', err);
            });
            // return;
            // this._sharedWorker = new window.SharedWorker('/bus/server_communication_shared_worker.js');
            // this._sharedWorker.port.addEventListener('message', ev => {
            //     const { payload, type } = ev.data;
            //     if (type === 'bus_message') {
            //         this._notifyHandlers(payload);
            //     }
            // });
            navigator.serviceWorker.addEventListener('message', ev => {
                const { payload, type } = ev.data;
                if (type === 'bus_message') {
                    this._notifyHandlers(payload);
                } else {
                    console.log('received worker message', ev.data);
                }
            });
            navigator.serviceWorker.ready.then(registration => {
                registration.active.postMessage("test post from client");
            });
        }
        // this._sharedWorker.port.start();
        this._isActive = true;
    }

    /**
     * Stops.
     */
    stop() {
        // this._sharedWorker.port.stop();
        this._isActive = false;
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
            // other.
            setTimeout(() => handler(busMessage));
        }
    }

}

export const sharedWorkerCommunicationService = {
    name: 'bus.sharedworker_communication',
    deploy: env => new SharedWorkerCommunication(env),
};
