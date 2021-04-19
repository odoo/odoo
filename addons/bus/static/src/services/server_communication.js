/** @odoo-module **/

const { EventBus } = owl.core;

/**
 * Allows communication from the server.
 */
export class ServerCommunication {

    constructor(env) {
        this.env = env;
        /**
         * Id of the last bus message that was fetched. Useful to only fetch new
         * bus messages.
         */
        this._lastBusMessageId;
        /**
         * Bus that handles the communication of messages to registered clients.
         */
        this._clientBus = new EventBus();

        this._handleBusMessage = this._handleBusMessage.bind(this);
        this.env.services['bus.longpolling_communication'].registerHandler(this._handleBusMessage);

        this.env.services['bus.longpolling_communication'].start(this._lastBusMessageId);
    }

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------

    // TODO same rename register methods? Here or in other files.

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
        this._clientBus.on(type, handler, handler);
    }

    /**
     * Unregisters an existing handler.
     *
     * @param {string} type for which the handler must be unregistered
     * @param {function} handler to unregister
     */
    off(type, handler) {
        this._clientBus.off(type, handler);
    }

    // -------------------------------------------------------------------------
    // Handlers
    // -------------------------------------------------------------------------

    /**
     * Handles a new bus message.
     *
     * @private
     * @param {*} busMessage
     */
    _handleBusMessage(busMessage) {
        this._lastBusMessageId = Math.max(busMessage.id, this._lastBusMessageId);
        this._clientBus.trigger(busMessage.message.type, busMessage.message.payload);
    }
}

export const serverCommunicationService = {
    name: 'bus.server_communication',
    dependencies: [
        'bus.longpolling_communication',
    ],
    deploy: env => new ServerCommunication(env),
};
