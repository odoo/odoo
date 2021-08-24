odoo.define('bus.Websocket', function (require) {
"use strict";

var Bus = require('web.Bus');
var ServicesMixin = require('web.ServicesMixin');


/**
 * Event Websocket bus used to bind events on the Websocket notifications
 *
 * trigger:
 * - window_focus : when the window focus change (true for focused, false for blur)
 * - notification : when a notification is receive from the socket
 *
 * @class Websocket
 */
var WebsocketBus = Bus.extend(ServicesMixin, {
    // constants
    WS_ROUTE: `ws://${window.location.hostname}:${window.location.port}/websocket`,
    USER_PRESENCE_UPDATE_PERIOD: 30000, // don't update presence more than once every 30s
    ERROR_RETRY_DELAY: 10000, // 10 seconds

    // properties
    _isOdooFocused: true,

    /**
     * @override
     */
    init: async function (parent, params) {
        this._super.apply(this, arguments);
        this._channels = [];

        // bus presence
        this._lastPresenceTime = new Date().getTime();
        $(window).on("focus." + this._longPollingBusId, this._onFocusChange.bind(this, {focus: true}));
        $(window).on("blur." + this._longPollingBusId, this._onFocusChange.bind(this, {focus: false}));
        $(window).on("unload." + this._longPollingBusId, this._onFocusChange.bind(this, {focus: false}));

        $(window).on("click." + this._longPollingBusId, this._onPresence.bind(this));
        $(window).on("keydown." + this._longPollingBusId, this._onPresence.bind(this));
        $(window).on("keyup." + this._longPollingBusId, this._onPresence.bind(this));

        // websocket initialization
        this._websocket = await this._websocketConnect();
        this._startUpdateUserPresenceLoop();
    },
    /**
     * @override
     */
    destroy: function () {
        $(window).off("focus." + this._longPollingBusId);
        $(window).off("blur." + this._longPollingBusId);
        $(window).off("unload." + this._longPollingBusId);
        $(window).off("click." + this._longPollingBusId);
        $(window).off("keydown." + this._longPollingBusId);
        $(window).off("keyup." + this._longPollingBusId);
        this._cleanupSocket();
        this._super();
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @param {string} channel
     */
    addChannel: function (channel) {
        if (this._channels.indexOf(channel) === -1) {
            this._channels.push(channel);
            this._updateChannels();
        }
    },
    /**
     * @param {string} channel
     */
    deleteChannel: function (channel) {
        const index = this._channels.indexOf(channel);
        if (index !== -1) {
            this._channels.splice(index, 1);
            this._updateChannels();
        }
    },
    /**
     * Tell whether odoo is focused or not
     *
     * @returns {boolean}
     */
    isOdooFocused: function () {
        return this._isOdooFocused;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Creates a WebSocket and connects it to server. Set onmessage handler to this._onWebsocketReceive afterward.
     *
     * @returns {Promise<WebSocket>} A connected WebSocket
     */
    _websocketConnect: function () {
        return new Promise((resolve, reject) => {
            const websocket = new WebSocket(this.WS_ROUTE);
            websocket.onopen = () => {
                websocket.onmessage = ev => this._onWebsocketReceive(JSON.parse(ev.data));
                websocket.onerror = null;
                resolve(websocket);
            };
            websocket.onerror = () => reject();
        });
    },
    /**
     * Cleanup all WebSocket handlers and intervals and close the WebSocket.
     */
    _cleanupSocket: function () {
        clearInterval(this.userPresenceInterval);
        this._websocket.onopen = null;
        this._websocket.onmessage = null;
        this._websocket.onerror = null;
        this._websocket.close();
    },
    /**
     * Helper for add/remove channels since both operations result in channel overwrite server side.
     */
    _updateChannels: function () {
        this._websocket.send(JSON.stringify({
            "channel": "subscribe",
            "message": this._channels,
        }));
    },
    /**
     * Helper for updateUserPresenceLoop which is executed each USER_PRESENCE_UPDATE_PERIOD seconds in order
     * to update user presence thus, status.
     */
    _updateUserPresence: function () {
        const now = new Date().getTime();
        this._websocket.send(JSON.stringify({
            "channel": "/bus_inactivity",
            "message": now - this._lastPresenceTime,
        }));
    },
    /**
     * Periodically calls _updateUserPresence.
     */
    _startUpdateUserPresenceLoop: function () {
        this._lastPresenceTime = new Date().getTime();
        this._updateUserPresence();
        this.userPresenceInterval = setInterval(this._updateUserPresence.bind(this), this.USER_PRESENCE_UPDATE_PERIOD);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Handler when the focus of the window change.
     * Trigger the 'window_focus' event.
     *
     * @private
     * @param {Object} params
     * @param {Boolean} params.focus
     */
    _onFocusChange: function (params) {
        this._isOdooFocused = params.focus;
        if (params.focus) {
            this._lastPresenceTime = new Date().getTime();
            this.trigger('window_focus', this._isOdooFocused);
        }
    },
    /**
     * Handler when there is an activity on the window (click, keydown, keyup)
     * Update the last presence date.
     *
     * @private
     */
    _onPresence: function () {
        this._lastPresenceTime = new Date().getTime();
    },
    /**
     * Handler when the WebSocket receive the new notifications
     * Triggers the 'notification' event with a list [channel, message] from notifications.
     *
     * @private
     * @param {Object[]} notifications, Input notifications have an id, channel, message
     * @returns {Array[]} Output arrays have notification's channel and message
     */
    _onWebsocketReceive: function (notifications) {
        const notifs = notifications.map(notif => [notif.channel, notif.message]);
        this.trigger("notification", notifs);
        return notifs;
    },
});

return WebsocketBus;

});
