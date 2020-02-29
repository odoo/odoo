odoo.define('im_support.MailManager', function (require) {
"use strict";

var MailManager = require('mail.Manager');

var core = require('web.core');
var session = require('web.session');
var WebClient = require('web.WebClient');

var SupportChannel = require('im_support.SupportChannel');
var SupportMessage = require('im_support.SupportMessage');
var supportSession = require('im_support.SupportSession');

var _t = core._t;

var POLL_TIMEOUT_DELAY = 1000 * 60 * 30; // 30 minutes
var POLL_TIMEOUT_KEY = 'im_support.poll_timeout';
var SUPPORT_CHANNEL_STATE_KEY = 'im_support.channel_state';

/**
 * This module includes the MailService to handle the case of the Support
 * channel, allowing the users of the current database to communicate with
 * livechat operators from another database (the Support database).
 */
MailManager.include({
    dependencies: (MailManager.prototype.dependencies || []).concat(['support_bus_service']),
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Initialises the Support: checks if there is a pending chat session
     * between the user and Support, and if so, re-opens it.
     * Note: we can't directly override init(), because it is already called
     * when the include is applied, so we use this hook instead (called at
     * webclient startup)
     */
    initSupport: function () {
        var self = this;
        this.supportChannelDef = null;
        this.supportChannelUUID = null;
        this.pollTimeout = null;
        this.pollingSupport = false;

        // listen to notifications coming from Support longpolling
        this.call('support_bus_service', 'onNotification', this, this._onSupportNotification);

        // check if there is a pending chat session with the Support
        var timeoutTimestamp = this.call('local_storage', 'getItem', POLL_TIMEOUT_KEY);
        var pollingDelay = timeoutTimestamp && (JSON.parse(timeoutTimestamp) - Date.now());
        if (pollingDelay && pollingDelay > 0) {
            var channelState = this.call('local_storage', 'getItem', SUPPORT_CHANNEL_STATE_KEY);
            this.startSupportLivechat(channelState).then(function () {
                var supportChannel = self.getChannel(self.supportChannelUUID);
                if (supportChannel.isAvailable()) {
                    self.startPollingSupport(pollingDelay);
                }
            });
        }
    },
    /**
     * Overrides to filter out the Support channel from the previews.
     *
     * @override
     * @returns {Promise<Object[]>} list of valid objects for mail.Preview
     *   template
     */
    getChannelPreviews: function () {
        var self = this;
        return this._super.apply(this, arguments)
            .then(function (channelsPreview) {
                return _.reject(channelsPreview, { id: self.supportChannelUUID });
            });
    },
    /**
     * Initiates a longpoll with the server hosting the Support channel.
     *
     * @param {integer} [pollingDelay=POLL_TIMEOUT_DELAY] the longpolling
     *   timeout delay to set
     */
    startPollingSupport: function (pollingDelay) {
        if (!('pollingSupport' in this)) {
            return this.initSupport();
        }
        if (!this.pollingSupport) {
            this.pollingSupport = true;
            this.call('support_bus_service', 'addChannel', this.supportChannelUUID);
            this.call('support_bus_service', 'startPolling');
            this._setPollTimeout(pollingDelay);
        }
    },
    /**
     * Opens the Support channel between a livechat operator from the Support
     * database and the current user (if there is an available operator).
     * Ensures to perform only once the request to create/retrieve the Support
     * channel.
     *
     * @param {string} [channelState='open'] state of the Support
     *   channel (see CHANNEL_STATES for accepted values)
     * @returns {Promise}
     */
    startSupportLivechat: function (channelState) {
        var self = this;
        if (!this.supportChannelDef) {
            // retrieve or create the channel
            this.supportChannelDef = supportSession.rpc('/odoo_im_support/get_support_channel', {
                channel_uuid: session.support_token,
                db_uuid: session.db_uuid,
                user_name: session.name,
            });
        }
        return this.supportChannelDef.then(function (channel) {
            if (!channel) {
                // there is no channel (because there is no online operator, and
                // no support channel has been created yet), so create one to
                // open in a chat window
                channel = {
                    available: false,
                    support_channel: true,
                    type: 'livechat',
                    uuid: "support_unavailable",
                };
            }
            if (!channelState) {
                channelState = self._isDiscussOpen() ? 'closed' : 'open';
                self.call('local_storage', 'setItem', SUPPORT_CHANNEL_STATE_KEY, channelState);
            }
            if (!self.supportChannelUUID) {
                // this part is only executed the first time the RPC is resolved
                self.supportChannelUUID = channel.uuid;

                // add the channel to the MailManager
                return self._addChannel(_.extend(channel, {
                    id: channel.uuid,
                    is_minimized: _.contains(['open', 'folded'], channelState),
                    state: channelState,
                })).then(function () {
                    // display an automatic message in the channel
                    var supportChannel = self.getChannel(channel.uuid);
                    supportChannel.addDefaultMessage();
                });
            } else {
                // the channel has already been added to the MailManager, so
                // simply re-open it
                if (self._isDiscussOpen()) {
                    self._openThreadInDiscuss(self.supportChannelUUID);
                } else {
                    channel = self.getChannel(self.supportChannelUUID);
                    channel.fold(channelState === 'folded');
                }
            }
        }).guardedCatch(function () {
            self.do_warn(_t("The Support server can't be reached."));
        });
    },
    /**
     * Updates the state of the Support channel (stored in the localStorage).
     *
     * @param {string} state ('closed', 'folded' or 'open')
     */
    updateSupportChannelState: function (state) {
        this.call('local_storage', 'setItem', SUPPORT_CHANNEL_STATE_KEY, state);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _makeChannel: function (data, options) {
        if (data.id === this.supportChannelUUID) {
            return new SupportChannel({
                parent: this,
                data: data,
                options: options,
                commands: this._commands
            });
        }
        return this._super.apply(this, arguments);
    },
    /**
     * Overrides to instantiate a SupportMessage when necessary.
     * @override
     */
    _makeMessage: function (data) {
        if (
            this.supportChannelUUID &&
            _.contains(data.channel_ids, this.supportChannelUUID)
        ) {
            return new SupportMessage(this, data, this._emojis);
        }
        return this._super.apply(this, arguments);
    },
    /**
     * Automatically stop polling for Support messages after a given delay of
     * inactivity.
     *
     * @private
     * @param {integer} [pollingDelay=POLL_TIMEOUT_DELAY] the longpolling
     * timeout delay to set
     */
    _setPollTimeout: function (pollingDelay) {
        pollingDelay = pollingDelay || POLL_TIMEOUT_DELAY;
        clearTimeout(this.pollTimeout);
        this.pollTimeout = setTimeout(this._stopPollingSupport.bind(this), pollingDelay);
        // save the timeout expiration datetime into the LocalStorage so that
        // we can re-open the Support channel if necessary on F5
        var timeoutTimestamp = Date.now() + pollingDelay;
        this.call('local_storage', 'setItem', POLL_TIMEOUT_KEY, timeoutTimestamp);
    },
    /**
     * Stops the longpoll with the server hosting the Support channel.
     *
     * @private
     */
    _stopPollingSupport: function () {
        this.pollingSupport = false;
        this.call('support_bus_service', 'stopPolling');
        this.call('local_storage', 'removeItem', POLL_TIMEOUT_KEY);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Handles poll notifications from the Support server.
     *
     * @private
     * @param {Object[]} notifications
     */
    _onSupportNotification: function (notifications) {
        var self = this;
        if (notifications && notifications.length) {
            this._setPollTimeout();
        }
        _.each(notifications, function (notification) {
            if (notification[1]._type === 'history_command') {
                // ignore history requests
                return;
            }
            var messageData = _.extend(notification[1], {
                channel_ids: [self.supportChannelUUID],
            });
            self._handleChannelNotification({ data: messageData });
        });
    },
});


// Unfortunately, we can't override init() of MailService because it is called
// before the include is applied, so we override the WebClient instead to call
// an initialization hook for Livechat Support in the Mail service.
WebClient.include({
    /**
     * Overrides to ask the Mail service to check whether there is a
     * pending chat session with Support, and if so, to re-open it.
     *
     * @override
     */
    show_application: function () {
        this.call('mail_service', 'initSupport');
        return this._super.apply(this, arguments);
    },
});

});

