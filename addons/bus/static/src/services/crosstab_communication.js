/** @odoo-module **/

const { EventBus } = owl.core;

/**
 * Allows communication from/to other tabs.
 * Prefer using `bus.server_communication` whenever it is possible because
 * cross-tab is limited to the current browser, so if the goal is to sync all
 * tabs of the current user, this class would fail to sync other browsers and
 * other devices.
 */
export class CrossTabCommunication {

    constructor(env) {
        this.env = env;
        /**
         * Bus that handles the communication of messages to registered clients.
         */
        this._clientBus = new EventBus();
        /**
         * Arbitrary key this service is using to communicate with localStorage.
         */
        this._localStorageType = 'bus.crosstab_communication';

        this._handleLocalStorageMessage = this._handleLocalStorageMessage.bind(this);
        // Current implementation of cross-tab relies on localStorage.
        this.env.services['bus.localstorage_communication'].registerHandler(this._localStorageType, this._handleLocalStorageMessage);
    }

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------

    /**
     * Registers a new handler.
     *
     * @param {string} type of the messages to catch with this handler.
     * @param {function} handler will be called when a message is
     *  received from another tab.
     */
    registerHandler(type, handler) {
        this._clientBus.on(type, handler, handler);
    }

    /**
     * Sends a message to other tabs.
     *
     * @param {string} type of the messages to send.
     * @param {*} payload that will be sent. `JSON.stringify()` must be
     *  able to serialize this payload.
     */
    sendMessage(type, payload) {
        this.env.services['bus.localstorage_communication'].sendMessage(this._localStorageType, {
            payload,
            type,
        });
    }

    /**
     * Unregisters an existing handler.
     *
     * @param {string} type for which the handler must be unregistered
     * @param {function} handler to unregister
     */
    unregisterHandler(type, handler) {
        this._clientBus.off(type, handler);
    }

    // -------------------------------------------------------------------------
    // Handlers
    // -------------------------------------------------------------------------

    /**
     * Handles message from localStorage.
     *
     * @param {Object} message
     * @param {*} message.payload
     * @param {string} message.type
     */
    _handleLocalStorageMessage({ payload, type }) {
        this._clientBus.trigger(type, payload);
    }

    // TODO SEB add "execute once" method whose goal is to ensure something is
    // executed only once, no matter how many tabs are requesting it at the
    // same time (so only execute it on the main tab)
}

export const crossTabCommunicationService = {
    name: 'bus.crosstab_communication',
    dependencies: ['bus.localstorage_communication'],
    deploy: env => new CrossTabCommunication(env),
};
