/** @odoo-module **/

import { debounce } from '@bus/workers/websocket_worker_utils';

/**
 * Type of events that can be sent from the worker to its clients.
 *
 * @typedef { 'connect' | 'reconnect' | 'disconnect' | 'reconnecting' | 'notification' } WorkerEvent
 */

/**
 * Type of action that can be sent from the client to the worker.
 *
 * @typedef {'add_channel' | 'delete_channel' | 'force_update_channels' | 'initialize_connection', 'send' | 'leave' } WorkerAction
 */

export const WEBSOCKET_CLOSE_CODES = Object.freeze({
    CLEAN: 1000,
    GOING_AWAY: 1001,
    PROTOCOL_ERROR: 1002,
    INCORRECT_DATA: 1003,
    ABNORMAL_CLOSURE: 1006,
    INCONSISTENT_DATA: 1007,
    MESSAGE_VIOLATING_POLICY: 1008,
    MESSAGE_TOO_BIG: 1009,
    EXTENSION_NEGOTIATION_FAILED: 1010,
    SERVER_ERROR: 1011,
    RESTART: 1012,
    TRY_LATER: 1013,
    BAD_GATEWAY: 1014,
    SESSION_EXPIRED: 4001,
    KEEP_ALIVE_TIMEOUT: 4002,
});

/**
 * This class regroups the logic necessary in order for the
 * SharedWorker/Worker to work. Indeed, Safari and some minor browsers
 * do not support SharedWorker. In order to solve this issue, a Worker
 * is used in this case. The logic is almost the same than the one used
 * for SharedWorker and this class implements it.
 */
export class WebsocketWorker {
    constructor(websocketURL) {
        this.websocketURL = websocketURL;
        this.channelsByClient = new Map();
        this.connectRetryDelay = 1000;
        this.connectTimeout = null;
        this.debugModeByClient = new Map();
        this.isDebug = false;
        this.isReconnecting = false;
        this.lastChannelSubscription = null;
        this.lastNotificationId = 0;
        this.messageWaitQueue = [];
        this._forceUpdateChannels = debounce(this._forceUpdateChannels, 300, true);
        this._start();
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Send the message to all the clients that are connected to the
     * worker.
     *
     * @param {WorkerEvent} type Event to broadcast to connected
     * clients.
     * @param {Object} data
     */
    broadcast(type, data) {
        for (const client of this.channelsByClient.keys()) {
            client.postMessage({ type, data });
        }
    }

    /**
     * Register a client handled by this worker.
     *
     * @param {MessagePort} messagePort
     */
    registerClient(messagePort) {
        messagePort.onmessage = ev => {
            this._onClientMessage(messagePort, ev.data);
        };
        this.channelsByClient.set(messagePort, []);
    }

    /**
     * Send message to the given client.
     *
     * @param {number} client
     * @param {WorkerEvent} type
     * @param {Object} data
     */
    sendToClient(client, type, data) {
        client.postMessage({ type, data });
    }

    //--------------------------------------------------------------------------
    // PRIVATE
    //--------------------------------------------------------------------------

    /**
     * Called when a message is posted to the worker by a client (i.e. a
     * MessagePort connected to this worker).
     *
     * @param {MessagePort} client
     * @param {Object} message
     * @param {WorkerAction} [message.action]
     * Action to execute.
     * @param {Object|undefined} [message.data] Data required by the
     * action.
     */
    _onClientMessage(client, { action, data }) {
        switch (action) {
            case 'send':
                return this._sendToServer(data);
            case 'leave':
                return this._unregisterClient(client);
            case 'add_channel':
                return this._addChannel(client, data);
            case 'delete_channel':
                return this._deleteChannel(client, data);
            case 'force_update_channels':
                return this._forceUpdateChannels();
            case 'initialize_connection':
                return this._initializeConnection(client, data);
        }
    }

    /**
     * Add a channel for the given client. If this channel is not yet
     * known, update the subscription on the server.
     *
     * @param {MessagePort} client
     * @param {string} channel
     */
    _addChannel(client, channel) {
        const clientChannels = this.channelsByClient.get(client);
        if (!clientChannels.includes(channel)) {
            clientChannels.push(channel);
            this.channelsByClient.set(client, clientChannels);
            this._updateChannels();
        }
    }

    /**
     * Remove a channel for the given client. If this channel is not
     * used anymore, update the subscription on the server.
     *
     * @param {MessagePort} client
     * @param {string} channel
     */
    _deleteChannel(client, channel) {
        const clientChannels = this.channelsByClient.get(client);
        if (!clientChannels) {
            return;
        }
        const channelIndex = clientChannels.indexOf(channel);
        if (channelIndex !== -1) {
            clientChannels.splice(channelIndex, 1);
            this._updateChannels();
        }
    }

    /**
     * Update the channels on the server side even if the channels on
     * the client side are the same than the last time we subscribed.
     */
    _forceUpdateChannels() {
        this._updateChannels({ force: true });
    }

    /**
     * Remove the given client from this worker client list as well as
     * its channels. If some of its channels are not used anymore,
     * update the subscription on the server.
     *
     * @param {MessagePort} client
     */
    _unregisterClient(client) {
        this.channelsByClient.delete(client);
        this.debugModeByClient.delete(client);
        this.isDebug = Object.values(this.debugModeByClient).some(debugValue => debugValue !== '');
        this._updateChannels();
    }

    /**
     * Initialize a client connection to this worker.
     *
     * @param {Object} param0
     * @param {String} [param0.debug] Current debugging mode for the
     * given client.
     * @param {Number} [param0.lastNotificationId] Last notification id
     * known by the client.
     */
    _initializeConnection(client, { debug, lastNotificationId }) {
        this.lastNotificationId = lastNotificationId;
        this.debugModeByClient[client] = debug;
        this.isDebug = Object.values(this.debugModeByClient).some(debugValue => debugValue !== '');
        this._updateChannels();
    }

    /**
     * Determine whether or not the websocket associated to this worker
     * is connected.
     *
     * @returns {boolean}
     */
    _isWebsocketConnected() {
        return this.websocket && this.websocket.readyState === 1;
    }

    /**
     * Triggered when a connection is closed. If closure was not clean ,
     * try to reconnect after indicating to the clients that the
     * connection was closed.
     *
     * @param {CloseEvent} ev
     * @param {number} code  close code indicating why the connection
     * was closed.
     * @param {string} reason reason indicating why the connection was
     * closed.
     */
    _onWebsocketClose({ code, reason }) {
        if (this.isDebug) {
            console.debug(`%c${new Date().toLocaleString()} - [onClose]`, 'color: #c6e; font-weight: bold;', code, reason);
        }
        if (this.isReconnecting) {
            // Connection was not established but the close event was
            // triggered anyway. Let the onWebsocketError method handle
            // this case.
            return;
        }
        this.broadcast('disconnect', { code, reason });
        if (code === WEBSOCKET_CLOSE_CODES.CLEAN) {
            // WebSocket was closed on purpose, do not try to reconnect.
            return;
        }
        // WebSocket was not closed cleanly, let's try to reconnect.
        this.broadcast('reconnecting', { closeCode: code });
        this.isReconnecting = true;
        if (code === WEBSOCKET_CLOSE_CODES.KEEP_ALIVE_TIMEOUT) {
            // Don't wait to reconnect on keep alive timeout.
            this.connectRetryDelay = 0;
        }
        this._retryConnectionWithDelay();
    }

    /**
     * Triggered when a connection failed or failed to established.
     */
    _onWebsocketError() {
        if (this.isDebug) {
            console.debug(`%c${new Date().toLocaleString()} - [onError]`, 'color: #c6e; font-weight: bold;');
        }
        this._retryConnectionWithDelay();
    }

    /**
    * Handle data received from the bus.
    *
    * @param {MessageEvent} messageEv
    */
    _onWebsocketMessage(messageEv) {
        const notifications = JSON.parse(messageEv.data);
        if (this.isDebug) {
            console.debug(`%c${new Date().toLocaleString()} - [onMessage]`, 'color: #c6e; font-weight: bold;', notifications);
        }
        this.lastNotificationId = notifications[notifications.length - 1].id;
        this.broadcast('notification', notifications);
    }

    /**
     * Triggered on websocket open. Send message that were waiting for
     * the connection to open.
     */
    _onWebsocketOpen() {
        if (this.isDebug) {
            console.debug(`%c${new Date().toLocaleString()} - [onOpen]`, 'color: #c6e; font-weight: bold;');
        }
        this.messageWaitQueue.forEach(msg => this.websocket.send(msg));
        this.messageWaitQueue = [];
        this.broadcast(this.isReconnecting ? 'reconnect' : 'connect');
        if (this.isReconnecting) {
            this._forceUpdateChannels();
        }
        this.connectRetryDelay = 0;
        this.connectTimeout = null;
        this.isReconnecting = false;
    }

    /**
     * Try to reconnect to the server, an exponential back off is
     * applied to the reconnect attempts.
     */
    _retryConnectionWithDelay() {
        this.connectRetryDelay = this.connectRetryDelay * 1.5 + 500 * Math.random();
        this.connectTimeout = setTimeout(this._start.bind(this), this.connectRetryDelay);
    }

    /**
     * Send a message to the server through the websocket connection.
     * If the websocket is not open, enqueue the message and send it
     * upon the next reconnection.
     *
     * @param {any} message Message to send to the server.
     */
    _sendToServer(message) {
        const payload = JSON.stringify(message);
        if (!this._isWebsocketConnected()) {
            this.messageWaitQueue.push(payload);
        } else {
            this.websocket.send(payload);
        }
    }

    /**
     * Start the worker by opening a websocket connection.
     */
    _start() {
        this.websocket = new WebSocket(this.websocketURL);
        this.websocket.addEventListener('open', this._onWebsocketOpen.bind(this));
        this.websocket.addEventListener('error', this._onWebsocketError.bind(this));
        this.websocket.addEventListener('message', this._onWebsocketMessage.bind(this));
        this.websocket.addEventListener('close', this._onWebsocketClose.bind(this));
    }

    /**
     * Update the channel subscription on the server. Ignore if the channels
     * did not change since the last subscription.
     *
     * @param {boolean} force Whether or not we should update the subscription
     * event if the channels haven't change since last subscription.
     */
    _updateChannels({ force = false } = {}) {
        const allTabsChannels = [...new Set([].concat.apply([], [...this.channelsByClient.values()]))].sort();
        const allTabsChannelsString = JSON.stringify(allTabsChannels);
        const shouldUpdateChannelSubscription = allTabsChannelsString !== this.lastChannelSubscription;
        if (force || shouldUpdateChannelSubscription) {
            this.lastChannelSubscription = allTabsChannelsString;
            this._sendToServer({ event_name: 'subscribe', data: { channels: allTabsChannels, last: this.lastNotificationId } });
        }
    }
}
