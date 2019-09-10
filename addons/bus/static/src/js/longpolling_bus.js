odoo.define('bus.Longpolling', function (require) {
"use strict";

const Bus = require('web.Bus');
const ServicesMixin = require('web.ServicesMixin');


/**
 * Event Longpolling bus used to bind events on the server long polling return
 *
 * trigger:
 * - window_focus : when the window focus change (true for focused, false for blur)
 * - notification : when a notification is receive from the long polling
 *
 * @class Longpolling
 */
const LongpollingBus = Bus.extend(ServicesMixin, {
    POLL_ROUTE: '/longpolling/poll',

    /**
     * @override
     */
    init(...args) {
        this._super(...args);

        this._channels = [];
        this._id = _.uniqueId('bus');
        this._isActive = false;
        this._isOdooFocused = true;
        this._lastNotificationID = 0;
        this._options = {};
        this._pollRetryTimeout = null;
        this._pollRpc = null;
        this._presence = Date.now();

        this._beforeunloadGlobalListener = ev => this._onBeforeunloadGlobal(ev);
        this._blurGlobalListener = ev => this._onBlurGlobal(ev);
        this._clickGlobalListener = ev => this._onClickGlobal(ev);
        this._focusGlobalListener = ev => this._onFocusGlobal(ev);
        this._keydownGlobalListener = ev => this._onKeydownGlobal(ev);
        this._keyupGlobalListener = ev => this._onKeyupGlobal(ev);

        window.addEventListener('beforeunload', this._beforeunloadGlobalListener);
        window.addEventListener('blur', this._blurGlobalListener);
        window.addEventListener('click', this._clickGlobalListener);
        window.addEventListener('focus', this._focusGlobalListener);
        window.addEventListener('keydown', this._keydownGlobalListener);
        window.addEventListener('keyup', this._keyupGlobalListener);
    },

    /**
     * @override
     */
    destroy() {
        this.stopPolling();
        window.removeEventListener('beforeunload', this._beforeunloadGlobalListener);
        window.removeEventListener('blur', this._blurGlobalListener);
        window.removeEventListener('click', this._clickGlobalListener);
        window.removeEventListener('focus', this._focusGlobalListener);
        window.removeEventListener('keydown', this._keydownGlobalListener);
        window.removeEventListener('keyup', this._keyupGlobalListener);
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
    addChannel(channel) {
        if (this._channels.includes(channel)) {
            return;
        }
        this._channels.push(channel);
        if (this._pollRpc) {
            this._pollRpc.abort();
        } else {
            this.startPolling();
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
    deleteChannel(channel) {
        var index = this._channels.indexOf(channel);
        if (index === -1) {
            return;
        }
        this._channels.splice(index, 1);
        if (this._pollRpc) {
            this._pollRpc.abort();
        }
    },
    /**
     * Tell whether odoo is focused or not
     *
     * @returns {boolean}
     */
    isOdooFocused() {
        return this._isOdooFocused;
    },
    /**
     * Start a long polling, i.e. it continually opens a long poll
     * connection as long as it is not stopped (@see `stopPolling`)
     */
    startPolling() {
        if (this._isActive) {
            return;
        }
        this._isActive = true;
        this._poll();
    },
    /**
     * Stops any started long polling
     *
     * Aborts a pending longpoll so that we immediately remove ourselves
     * from listening on notifications on this channel.
     */
    stopPolling() {
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
    updateOption(key, value) {
        this._options[key] = value;
    },
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object[]} notifications
     */
    _parseAndTriggerNotifications(notifications) {
        const notifs = notifications
            .filter(notif =>
                !this._lastNotificationId ||
                notif.id > this._lastNotificationId)
            .map(notif => {
                if (notif.id > this._lastNotificationID) {
                    this._lastNotificationID = notif.id;
                }
                return [notif.channel, notif.message];
            });
        this.trigger('notification', notifs);
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
    _poll() {
        if (!this._isActive) {
            return;
        }
        const now = Date.now();
        const options = Object.assign(
            {},
            this._options,
            { bus_inactivity: now - this._presence }
        );
        const data = {
            channels: this._channels,
            last: this._lastNotificationID,
            options,
        };
        // The backend has a maximum cycle time of 50 seconds so give +10 seconds
        this._pollRpc = this._rpc({
            params: data,
            route: this.POLL_ROUTE,
        }, {
            shadow: true,
            timeout: 60*1000,
        });
        this._pollRpc.then(result => {
            this._pollRpc = false;
            this._onPoll(result);
            this._poll();
        }).guardedCatch(result => {
            this._pollRpc = false;
            // no error popup if request is interrupted or fails for any reason
            result.event.preventDefault();
            if (
                result.message &&
                result.message.message === "XmlHttpRequestError abort"
            ) {
                this._poll();
            } else {
                // random delay to avoid massive longpolling
                this._pollRetryTimeout = setTimeout(
                    () => this._poll(),
                    (10+Math.floor((Math.random()*20)+1))*1000
                );
            }
        });
    },
    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onBeforeunloadGlobal() {
        this._isOdooFocused = false;
    },
    /**
     * @private
     */
    _onBlurGlobal() {
        this._isOdooFocused = false;
    },
    /**
     * @private
     */
    _onClickGlobal() {
        this._presence = Date.now();
    },
    /**
     * @private
     */
    _onFocusGlobal() {
        this._isOdooFocused = true;
        this._presence = Date.now();
        this.trigger('window_focus', this._isOdooFocused);
    },
    /**
     * @private
     */
    _onKeydownGlobal() {
        this._presence = Date.now();
    },
    /**
     * @private
     */
    _onKeyupGlobal() {
        this._presence = Date.now();
    },
    /**
     * Handler when the long polling receive the new notifications
     * Update the last notification id received.
     * Triggered the 'notification' event with a list [channel, message] from notifications.
     *
     * @private
     * @param {Object[]} notifications, Input notifications have an id, channel, message
     */
    _onPoll(notifications) {
        this._parseAndTriggerNotifications(notifications);
    },
});

return LongpollingBus;

});
