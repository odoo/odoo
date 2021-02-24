/** @odoo-module **/
const { EventBus } = owl.core;

/**
 * Allows communication from/to other tabs.
 */
export const busCrosstabCommunication = {
    name: 'bus.crosstab_communication',
    dependencies: ['bus.localstorage_communication'],
    deploy(env) {
        const {
            services: {
                'bus.localstorage_communication': localStorageCommunication,
            },
        } = env;
        /**
         * Bus that handles the communication of messages to registered clients.
         */
        const clientBus = new EventBus();
        /**
         * Registers the localSotrage handlers. Current implementation of
         * cross-tab communication relies on localSotrage but this is subject to
         * change in the future.
         */
        localStorageCommunication.on('bus.crosstab_communication', (type, message) => {
            clientBus.trigger(type, message);
        });
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
                localStorageCommunication.trigger(type, message);
            },
        };
    },
};
