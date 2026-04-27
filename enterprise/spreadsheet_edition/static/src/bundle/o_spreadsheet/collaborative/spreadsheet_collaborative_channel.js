/** @odoo-module **/

/**
 * This class implements the `TransportService` interface defined
 * by o-spreadsheet. Its purpose is to communicate with other clients
 * by sending and receiving spreadsheet messages through the server.
 * @see https://github.com/odoo/o-spreadsheet
 *
 * It listens messages on the long polling bus and forwards spreadsheet messages
 * to the handler. (note: it is assumed there is only one handler)
 *
 * It uses the RPC protocol to send messages to the server which
 * push them in the long polling bus for other clients.
 */
export class SpreadsheetCollaborativeChannel {
    static dependencies = ["bus_service", "orm"];
    /**
     * @param {Env} env
     * @param {string} resModel model linked to the spreadsheet
     * @param {number} resId Id of the spreadsheet
     * @param {number} [shareId]
     * @param {string} [accessToken] sharing token
     */
    constructor(env, resModel, resId, shareId, accessToken) {
        this.env = env;
        this.orm = env.services.orm.silent;
        this.resId = resId;
        this.resModel = resModel;
        this.shareId = shareId;
        this.accessToken = accessToken;
        /**
         * A callback function called to handle messages when they are received.
         */
        this._listener;
        /**
         * Messages are queued while there is no listener. They are forwarded
         * once it registers.
         */
        this._queue = [];
        this._channel = this._getChannel();
        this.env.services.bus_service.addChannel(this._channel);
        this.env.services.bus_service.subscribe("spreadsheet", (payload) => {
            if (payload.id === this.resId) {
                this._handleNotification(payload);
            }
        });
    }

    /**
     * Register a function that is called whenever a new spreadsheet revision
     * message notification is received by server.
     *
     * @param {any} id
     * @param {Function} callback
     */
    onNewMessage(id, callback) {
        this._listener = callback;
        for (const message of this._queue) {
            callback(message);
        }
        this._queue = [];
    }

    /**
     * Send a message to the server
     *
     * @param {Object} message
     */
    async sendMessage(message) {
        const isAccepted = await this.orm.call(this.resModel, "dispatch_spreadsheet_message", [
            this.resId,
            message,
            this.accessToken,
        ]);
        if (isAccepted) {
            this._handleNotification(message);
        }
    }

    /**
     * Stop listening new messages
     */
    leave() {
        this._listener = undefined;
    }

    /**
     * Either forward the message to the listener if it's already registered,
     * or put it in a queue.
     *
     * @private
     * @param {Object} notifs
     */
    _handleNotification(payload) {
        if (!this._listener) {
            this._queue.push(payload);
        } else {
            this._listener(payload);
        }
    }

    /**
     * @private
     * @returns {string}
     */
    _getChannel() {
        // Listening this channel tells the server the spreadsheet is active
        // but the server will actually push to channel [{dbname},  {resModel}, {resId}]
        // The user can listen to this channel only if he has the required read access.
        const channel = `spreadsheet_collaborative_session:${this.resModel}:${this.resId}`;
        if (this.shareId && this.accessToken) {
            return `${channel}:${this.shareId}:${this.accessToken}`;
        }
        return channel;
    }
}
