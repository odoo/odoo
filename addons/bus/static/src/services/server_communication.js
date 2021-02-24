/** @odoo-module **/
const { EventBus } = owl.core;

/**
 * Allows communication from the server.
 */
export const busServerCommunication = {
    name: 'bus.server_communication',
    dependencies: ['bus.longpolling_communication', 'bus.crosstab_communication'],
    deploy(env) {
        const {
            services: {
                'bus.longpolling_communication': longpolling,
                'bus.crosstab_communication': crosstab,
            },
        } = env;
        /**
         * Determines the type of communication with the server. Must be one of:
         * 'longpolling': this tab is in direct communication with the server
         *   through a longpolling request.
         * 'crosstab': this tab is in indirect communication with the server
         *   through another tab.
         */
        let communicationType = 'longpolling';
        /**
         * Bus that handles the communication of messages to registered clients.
         */
        const clientBus = new EventBus();
        // Registers the handlers.
        longpolling.registerHandler(busMessage => {
            if (communicationType !== 'longpolling') {
                console.warn(`bus.server_communication message received while longpolling was inactive: ${busMessage}`);
            }
            clientBus.trigger(busMessage.message.type, busMessage.message.payload);
            crosstab.trigger('bus.server_communication', busMessage);
        });
        // TODO SEB handle longpolling/crosstab switch
        longpolling.start();
        crosstab.on('bus.server_communication', busMessage => {
            if (communicationType !== 'crosstab') {
                console.warn(`bus.server_communication message received while crosstab was inactive: ${busMessage}`);
            }
            clientBus.trigger(busMessage.message.type, busMessage.message.payload);
        });
        return {
            /**
             * Registers a new handler.
             *
             * @param {string} type of the messages to catch with this handler.
             * @param {function} handler will be called when a message is
             *  received from the server, with one param, an object that contains
             *  the following keys: {
             *    'payload' {*} data the server communicated
             *    'target' {string} the target recipient(s) of this data
             *    'type' {string} the type of data
             *  }
             *  Note that `target` and `type` are only provided for debugging
             *  purposes. It is advised to simply register one handler per type
             *  to avoid the need of any post filtering based on type.
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
        };
    },
};
