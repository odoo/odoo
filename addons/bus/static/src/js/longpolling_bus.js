odoo.define('bus.Longpolling', function (require) {
"use strict";

var Bus = require('web.Bus');
var ServicesMixin = require('web.ServicesMixin');


/**
 * Event Longpolling bus used to bind events on the server long polling return
 *
 * trigger:
 * - window_focus : when the window focus change (true for focused, false for blur)
 * - notification : when a notification is receive from the long polling
 *
 * @class Longpolling
 */
var LongpollingBus = Bus.extend(ServicesMixin, {
    // constants
    PARTNERS_PRESENCE_CHECK_PERIOD: 30000,  // don't check presence more than once every 30s
    ERROR_RETRY_DELAY: 10000, // 10 seconds
    POLL_ROUTE: '/longpolling/poll',

    // properties
    _isActive: null,
    _lastNotificationID: 0,
    _isOdooFocused: true,
    _pollRetryTimeout: null,

    /**
     * @override
     */
    init: function (parent, params) {
        this._super.apply(this, arguments);
        this._id = _.uniqueId('bus');
        this._options = {};
        this._channels = [];

        // bus presence
        this._lastPresenceTime = new Date().getTime();
        this._lastPartnersPresenceCheck = this._lastPresenceTime;
        $(window).on("focus." + this._id, this._onFocusChange.bind(this, {focus: true}));
        $(window).on("blur." + this._id, this._onFocusChange.bind(this, {focus: false}));
        $(window).on("unload." + this._id, this._onFocusChange.bind(this, {focus: false}));

        $(window).on("click." + this._id, this._onPresence.bind(this));
        $(window).on("keydown." + this._id, this._onPresence.bind(this));
        $(window).on("keyup." + this._id, this._onPresence.bind(this));
    },
    /**
     * @override
     */
    destroy: function () {
        this.stopPolling();
        $(window).off("focus." + this._id);
        $(window).off("blur." + this._id);
        $(window).off("unload." + this._id);
        $(window).off("click." + this._id);
        $(window).off("keydown." + this._id);
        $(window).off("keyup." + this._id);
        this._super();
    },
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------
    /**
     * Register a new channel to listen on the longpoll (ignore if already
     * listening on this channel).
     * Aborts a pending longpoll, in order to re-start another longpoll, so
     * that we can immediately get notifications on newly registered channel.
     *
     * @param {string} channel
     */
    addChannel: function (channel) {
        if (this._channels.indexOf(channel) === -1) {
            this._channels.push(channel);
            if (this._pollRpc) {
                this._pollRpc.abort();
            } else {
                this.startPolling();
            }
        }
    },
    /**
     * Unregister a channel from listening on the longpoll.
     *
     * Aborts a pending longpoll, in order to re-start another longpoll, so
     * that we immediately remove ourselves from listening on notifications
     * on this channel.
     *
     * @param {string} channel
     */
    deleteChannel: function (channel) {
        var index = this._channels.indexOf(channel);
        if (index !== -1) {
            this._channels.splice(index, 1);
            if (this._pollRpc) {
                this._pollRpc.abort();
            }
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
    /**
     * Start a long polling, i.e. it continually opens a long poll
     * connection as long as it is not stopped (@see `stopPolling`)
     */
    startPolling: function () {
        if (this._isActive === null) {
            this._poll = this._poll.bind(this);
        }
        if (!this._isActive) {
            this._isActive = true;
            this._poll();
        }
    },
    /**
     * Stops any started long polling
     *
     * Aborts a pending longpoll so that we immediately remove ourselves
     * from listening on notifications on this channel.
     */
    stopPolling: function () {
        this._isActive = false;
        this._channels = [];
        clearTimeout(this._pollRetryTimeout);
        if (this._pollRpc) {
            this._pollRpc.abort();
        }
    },
    /**
     * Add or update an option on the longpoll bus.
     * Stored options are sent to the server whenever a poll is started.
     *
     * @param {string} key
     * @param {any} value
     */
    updateOption: function (key, value) {
        this._options[key] = value;
    },
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------
    /**
     * returns the last recorded presence
     *
     * @private
     * @returns {integer} number of milliseconds since 1 January 1970 00:00:00
     */
    _getLastPresence: function () {
        return this._lastPresenceTime;
    },
    /**
     * Continually start a poll:
     *
     * A poll is a connection that is kept open for a relatively long period
     * (up to 1 minute). Local bus data are sent to the server each time a poll
     * is initiated, and the server may return some "real-time" notifications
     * about registered channels.
     *
     * A poll ends on timeout, on abort, on receiving some notifications, or on
     * receiving an error. Another poll usually starts afterward, except if the
     * poll is aborted or stopped (@see stopPolling).
     *
     * @private
     */
    _poll: function () {
        var self = this;
        if (!this._isActive) {
            return;
        }
        var now = new Date().getTime();
        var options = _.extend({}, this._options, {
            bus_inactivity: now - this._getLastPresence(),
        });
        if (this._lastPartnersPresenceCheck + this.PARTNERS_PRESENCE_CHECK_PERIOD > now) {
            options = _.omit(options, 'bus_presence_partner_ids');
        } else {
            this._lastPartnersPresenceCheck = now;
        }
        var data = {channels: this._channels, last: this._lastNotificationID, options: options};
        // The backend has a maximum cycle time of 50 seconds so give +10 seconds
        this._pollRpc = this._rpc({route: this.POLL_ROUTE, params: data}, {shadow : true, timeout: 60000});
        this._pollRpc.then(function (result) {
            self._pollRpc = false;
            self._onPoll(result);
            self._poll();
        }, function (error, ev) {
            self._pollRpc = false;
            // no error popup if request is interrupted or fails for any reason
            ev.preventDefault();
            if (error && error.message === "XmlHttpRequestError abort") {
                self._poll();
            } else {
                // random delay to avoid massive longpolling
                self._pollRetryTimeout = setTimeout(self._poll, self.ERROR_RETRY_DELAY + (Math.floor((Math.random()*20)+1)*1000));
            }
        });
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
     * Handler when the long polling receive the new notifications
     * Update the last notification id received.
     * Triggered the 'notification' event with a list [channel, message] from notifications.
     *
     * @private
     * @param {Object[]} notifications, Input notifications have an id, channel, message
     * @returns {Array[]} Output arrays have notification's channel and message
     */
    _onPoll: function (notifications) {
        var self = this;
        var notifs = _.map(notifications, function (notif) {
            if (notif.id > self._lastNotificationID) {
                self._lastNotificationID = notif.id;
            }
            return [notif.channel, notif.message];
        });
        this.trigger("notification", notifs);
        return notifs;
    },
    /**
     * Handler when they are an activity on the window (click, keydown, keyup)
     * Update the last presence date.
     *
     * @private
     */
    _onPresence: function () {
        this._lastPresenceTime = new Date().getTime();
    },
});

return LongpollingBus;

});
