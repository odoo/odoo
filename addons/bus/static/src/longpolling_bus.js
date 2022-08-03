/** @odoo-module **/

const { EventBus } = owl;

/**
 * Event Longpolling bus used to bind events on the server long polling return
 *
 * trigger:
 * - notification : when a notification is receive from the long polling
 */
export class Longpolling extends EventBus {
    constructor(env, { multi_tab }) {
        super();
        this.env = env;

        // CONSTANTS
        this.PARTNERS_PRESENCE_CHECK_PERIOD = 30000; // don't check presence more than once every 30s
        this.ERROR_RETRY_DELAY = 10000; // 10 seconds
        this.POLL_ROUTE = '/longpolling/poll';

        // PROPERTIES
        this._isActive = null;
        this._id = multi_tab.currentTabId;
        this._lastNotificationID = 0;
        this._pollRetryTimeout = null;

        // the _id is modified by crosstab_bus, so we can't use it to unbind the events in the destroy.
        this._longPollingBusId = this._id;
        this._options = {};
        this._channels = [];
    }

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
        if (this._channels.indexOf(channel) === -1) {
            this._channels.push(channel);
            this._restartPolling();
        }
    }

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
        if (index !== -1) {
            this._channels.splice(index, 1);
            if (this._pollRpc) {
                this._pollRpc.abort();
            }
        }
    }

    /**
     * Start a long polling, i.e. it continually opens a long poll
     * connection as long as it is not stopped (@see `stopPolling`)
     */
    startPolling() {
        if (this._isActive === null) {
            this._poll = this._poll.bind(this);
        }
        if (!this._isActive) {
            this._isActive = true;
            this._poll();
        }
    }

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
    }

    /**
     * Add or update an option on the longpoll bus.
     * Stored options are sent to the server whenever a poll is started.
     *
     * @param {string} key
     * @param {any} value
     */
    updateOption(key, value) {
        this._options[key] = value;
    }


    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

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
        var self = this;
        if (!this._isActive) {
            return;
        }
        var now = new Date().getTime();
        var options = _.extend({}, this._options, {
            bus_inactivity: now - this.env.services['presence'].getLastPresence(),
        });
        var data = {channels: this._channels, last: this._lastNotificationID, options: options};
        // The backend has a maximum cycle time of 50 seconds so give +10 seconds
        this._pollRpc = this._makePoll(data);
        this._pollRpc.then(function (result) {
            self._pollRpc = false;
            self._onPoll(result);
            self._poll();
        }).catch(function (result) {
            self._pollRpc = false;
            if (result.message === "XmlHttpRequestError abort") {
                self._poll();
            } else {
                // random delay to avoid massive longpolling
                self._pollRetryTimeout = setTimeout(self._poll, self.ERROR_RETRY_DELAY + (Math.floor((Math.random()*20)+1)*1000));
            }
        });
    }

    /**
     * @private
     * @param data: object with poll parameters
     */
    _makePoll(params) {
        return this.env.services.rpc(this.POLL_ROUTE, params, { silent: true, timeout: 60000 });
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Handler when the long polling receive the new notifications
     * Update the last notification id received.
     * Triggered the 'notification' event with a list [channel, message] from notifications.
     *
     * @private
     * @param {Object[]} notifications, Input notifications have an id, channel, message
     * @returns {Array[]} Output arrays have notification's channel and message
     */
    _onPoll(notifications) {
        var self = this;
        var notifs = _.map(notifications, function (notif) {
            if (notif.id > self._lastNotificationID) {
                self._lastNotificationID = notif.id;
            }
            return notif.message;
        });
        this.trigger("notification", notifs);
        return notifs;
    }

    /**
     * Restart polling.
     *
     * @private
     */
    _restartPolling() {
        if (this._pollRpc) {
            this._pollRpc.abort();
        } else {
            this.startPolling();
        }
    }
}
