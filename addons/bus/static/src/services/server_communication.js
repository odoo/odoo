/** @odoo-module **/

const { EventBus } = owl.core;

/**
 * Allows communication from the server.
 */
export class ServerCommunication {

    constructor(env) {
        this.env = env;
        /**
         * Determines the type of communication with the server. Must be one of:
         * 'longpolling': this tab is in direct communication with the server
         *   through a longpolling request.
         * 'crosstab': this tab is in indirect communication with the server
         *   through another tab.
         */
        this._communicationType;
        /**
         * Id of the last bus message that was fetched. Useful to only fetch new
         * bus messages.
         */
        this._lastBusMessageId;
        /**
         * Bus that handles the communication of messages to registered clients.
         */
        this._clientBus = new EventBus();
        /**
         * Arbitrary key this service is using to communicate bus messages with
         * other tabs. Bus message are messages whose goal is to be forwarded to
         * business code.
         */
        this._crosstabTypeForBusMessage = 'bus.server_communication_message';
        /**
         * Arbitrary key this service is using to communicate service messages
         * with other tabs. Service messages are messages whose goal is to
         * ensure the proper working of this service.
         */
        this._crosstabTypeForServiceMessage = 'bus.server_communication_service';

        this._handleBusMessageFromCrosstab = this._handleBusMessageFromCrosstab.bind(this);
        this._handleBusMessageFromLongpolling = this._handleBusMessageFromLongpolling.bind(this);
        this._handleServiceMessageFromCrosstab = this._handleServiceMessageFromCrosstab.bind(this);
        this._handleUserPresenceChange = this._handleUserPresenceChange.bind(this);
        this.env.services['bus.crosstab_communication'].registerHandler(this._crosstabTypeForBusMessage, this._handleBusMessageFromCrosstab);
        this.env.services['bus.crosstab_communication'].registerHandler(this._crosstabTypeForServiceMessage, this._handleServiceMessageFromCrosstab);
        this.env.services['bus.longpolling_communication'].registerHandler(this._handleBusMessageFromLongpolling);
        this.env.services['bus.user_presence'].registerHandler(this._handleUserPresenceChange);

        this._selectCommunicationType();
    }

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------

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
    // Private
    // -------------------------------------------------------------------------

    /**
     * Selects the most appropriate communication type.
     *
     * The currently visible tab should always use longpolling because it is the
     * most reactive option (if the longpolling is on a non-visible tab it might
     * be throttled by the browser and slow down everything).
     *
     * Non-visible tabs should use cross-tab if there is at least one visible
     * tab.
     *
     * If there are no visible tab, all the non-visible tabs must decide between
     * themselves which one is going to use longpolling.
     *
     * @private
     */
    _selectCommunicationType() {
        // TODO SEB better handle longpolling/crosstab switch
        if (this.env.services['bus.user_presence'].isCurrentPageVisible()) {
            console.warn('selecting longpolling');
            this._communicationType = 'longpolling';
            this.env.services['bus.longpolling_communication'].start(this._lastBusMessageId);
            // this.env.services['bus.crosstab_communication'].sendMessage(this._crosstabTypeForServiceMessage, 'new_visible_tab');
        } else {
            console.warn('selecting crosstab');
            // if there is another tab currently active as longpolling, use crosstab
            // if there is no other tab doing longpolling: must decide...
            this._communicationType = 'crosstab';
            this.env.services['bus.longpolling_communication'].stop();
        }
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

    /**
     * Handles a new bus message specifically received from cross-tab.
     *
     * @private
     * @param {*} busMessage
     */
    _handleBusMessageFromCrosstab(busMessage) {
        if (this._communicationType !== 'crosstab') {
            console.warn(`bus.server_communication message received while crosstab was inactive: ${busMessage}`);
        }
        this._handleBusMessage(busMessage);
    }

    /**
     * Handles a new bus message specifically received from longpolling.
     *
     * @private
     * @param {*} busMessage
     */
    _handleBusMessageFromLongpolling(busMessage) {
        if (this._communicationType !== 'longpolling') {
            console.warn(`bus.server_communication message received while longpolling was inactive: ${busMessage}`);
        }
        this._handleBusMessage(busMessage);
        this.env.services['bus.crosstab_communication'].sendMessage(this._crosstabTypeForBusMessage, busMessage);
    }

    /**
     * Handles a new service message received from cross-tab.
     *
     * @private
     * @param {*} serviceMessage
     */
    _handleServiceMessageFromCrosstab(serviceMessage) {
        this._selectCommunicationType();
    }

    /**
     * Handles change in user presence.
     *
     * @private
     */
    _handleUserPresenceChange() {
        this._selectCommunicationType();
    }
}

export const serverCommunicationService = {
    name: 'bus.server_communication',
    dependencies: [
        'bus.crosstab_communication',
        'bus.longpolling_communication',
        'bus.user_presence',
    ],
    deploy: env => new ServerCommunication(env),
};
