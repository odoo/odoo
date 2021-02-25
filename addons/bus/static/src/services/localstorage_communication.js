/** @odoo-module **/

const { EventBus } = owl.core;

/**
 * Low-level implementation of cross-tab communication with the use of
 * `localStorage`. Prefer using `bus.crosstab_communication` instead for
 * functional needs.
 */
export class LocalStorageCommunication {

    constructor(env) {
        /**
         * Bus that handles the communication of messages to registered clients.
         */
        this._clientBus = new EventBus();
        /**
         * Arbitrary key this service is using to communicate with localStorage.
         */
        this._localStorageKey = 'bus.localstorage_communication';
        this._handleStorageChange = this._handleStorageChange.bind(this);
        window.addEventListener('storage', this._handleStorageChange);
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
        window.localStorage.setItem(this._localStorageKey, JSON.stringify({ payload, type }));
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
     * @private
     * @param {StorageEvent} ev
     */
    _handleStorageChange(ev) {
        const { key, newValue } = ev;
        if (key !== this._localStorageKey) {
            return;
        }
        const { payload, type } = JSON.parse(newValue);
        this._clientBus.trigger(type, payload);
    }
}

export const localStorageCommunicationService = {
    name: 'bus.localstorage_communication',
    dependencies: [],
    deploy: env => new LocalStorageCommunication(env),
};
