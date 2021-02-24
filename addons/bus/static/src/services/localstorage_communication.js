/** @odoo-module **/
const { EventBus } = owl.core;

/**
 * Low-level implementation of cross-tab communication with the use of
 * `localStorage`. Prefer using `bus.crosstab_communication` instead for
 * functional needs.
 */
export const busLocalstorageCommunication = {
    name: 'bus.localstorage_communication',
    dependencies: [],
    deploy(env) {
        /**
         * Bus that handles the communication of messages to registered clients.
         */
        const clientBus = new EventBus();
        /**
         * Forwards from another tab to current tab.
         */
        const handleCrosstab = (type, message) => {
            clientBus.trigger(type, message);
        };
        return {
            /**
             * Registers a new handler.
             *
             * @param {string} type of the messages to catch with this handler.
             * @param {function} handler will be called when a message is
             *  received from another tab.
             */
            on(type, handler) {
                clientBus.on(type, handler, handler);
            },
            /**
             * Unregisters an existing handler.
             *
             * @param {string} type for which the handler must be unregistered
             * @param {function} handler to unregister
             */
            off(type, handler) {
                clientBus.off(type, handler);
            },
            /**
             * Sends a message to other tabs.
             *
             * @param {string} type of the messages to send.
             * @param {*} message that will be sent. `JSON.stringify()` must be
             *  able to serialize this message.
             */
            trigger(type, message) {

            },
        };
    },
};
