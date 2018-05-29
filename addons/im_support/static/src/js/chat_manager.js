odoo.define('im_support.ChatManager', function (require) {
"use strict";

/**
 * This module includes the ChatManager to handle the case of the Support
 * channel, allowing the users of the current database to communicate with
 * livechat operators from another database (the Support database).
 */

var ChatManager = require('mail.ChatManager');

var core = require('web.core');
var session = require('web.session');
var WebClient = require('web.WebClient');

var supportSession = require('im_support.SupportSession');
var supportBus = require('im_support.SupportBus');

var _t = core._t;
var CHANNEL_STATES = {
    CLOSED: 'closed',
    FOLDED: 'folded',
    OPEN: 'open',
};
var ODOOBOT_ID = "ODOOBOT"; // FIXME: should be exported by the ChatManager
var POLL_TIMEOUT_DELAY = 1000 * 60 * 30; // 30 minutes
var POLL_TIMEOUT_KEY = 'im_support.poll_timeout';
var SUPPORT_CHANNEL_LIMIT = 30; // limit of messages to fetch
var SUPPORT_CHANNEL_STATE_KEY = 'im_support.channel_state';

ChatManager.include({
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Overrides to prevent from calling the server with the Support channel
     * (which is a record on the Support database).
     *
     * @override
     */
    closeChatSession: function (channelID) {
        if (channelID === this.supportChannelUUID) {
            this.call('local_storage', 'setItem', SUPPORT_CHANNEL_STATE_KEY, CHANNEL_STATES.CLOSED);
            return $.when();
        }
        return this._super.apply(this, arguments);
    },
    /**
     * Overrides to prevent from calling the server with the Support channel
     * (which is a record on the Support database).
     *
     * @override
     */
    detachChannel: function (channelID) {
        if (channelID === this.supportChannelUUID) {
            this.call('local_storage', 'setItem', SUPPORT_CHANNEL_STATE_KEY, CHANNEL_STATES.OPEN);
            return $.when();
        }
        return this._super.apply(this, arguments);
    },
    /**
     * Overrides to prevent from calling the server with the Support channel
     * (which is a record on the Support database).
     *
     * @override
     */
    foldChannel: function (channelID, folded) {
        if (channelID === this.supportChannelUUID) {
            var value = folded ? CHANNEL_STATES.FOLDED : CHANNEL_STATES.OPEN;
            this.call('local_storage', 'setItem', SUPPORT_CHANNEL_STATE_KEY, value);
            return $.when();
        }
        return this._super.apply(this, arguments);
    },
    /**
     * Overrides to filter out the Support channel from the previews.
     *
     * @override
     */
    getChannelsPreview: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function (channelsPreview) {
            return _.reject(channelsPreview, {id: self.supportChannelUUID});
        });
    },
    /**
     * Overrides to prevent from calling the server with the Support channel
     * (which is a record on the Support database).
     *
     * @override
     */
    getMentionPartnerSuggestions: function (channel) {
        if (channel && channel.id === this.supportChannelUUID) {
            return $.when();
        }
        return this._super.apply(this, arguments);
    },
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
        supportBus.on('notification', this, this._onSupportNotification);

        // check if there is a pending chat session with the Support
        var timeoutTimestamp = this.call('local_storage', 'getItem', POLL_TIMEOUT_KEY);
        var pollingDelay = timeoutTimestamp && (JSON.parse(timeoutTimestamp) - Date.now());
        if (pollingDelay && pollingDelay > 0) {
            var channelState = this.call('local_storage', 'getItem', SUPPORT_CHANNEL_STATE_KEY);
            this.startSupportLivechat(channelState).then(function () {
                var supportChannel = self.getChannel(self.supportChannelUUID);
                if (supportChannel.available) {
                    self._startPollingSupport(pollingDelay);
                }
            });
        }
    },
    /**
     * Overrides to prevent from calling the server with the Support channel
     * (which is a record on the Support database).
     *
     * @override
     */
    markChannelAsSeen: function (channel) {
        if (channel.id === this.supportChannelUUID) {
            this._updateChannelUnreadCounter(channel, 0);
            return $.when();
        }
        return this._super.apply(this, arguments);
    },
    /**
     * Overrides to call a specific route for messages posted in the Support
     * channel.
     *
     * @override
     */
    postMessage: function (data, options) {
        if (options.channelID && options.channelID === this.supportChannelUUID) {
            // ensure that the poll is active before posting the message
            if (!this.pollingSupport) {
                this._startPollingSupport();
            }
            return supportSession.rpc("/odoo_im_support/chat_post", {
                uuid: this.supportChannelUUID,
                message_content: data.content,
            });
        }
        return this._super.apply(this, arguments);
    },
    /**
     * Opens the support channel between a livechat operator from the Support
     * database and the current user (if there is an available operator).
     * Ensures to perform only once the request to create/retrieve the Support
     * channel.
     *
     * @param {string} [channelState=CHANNEL_STATES.OPEN] state of the Support
     *   channel (see CHANNEL_STATES for accepted values)
     * @returns {Deferred}
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
                channelState = self.discussOpen ? CHANNEL_STATES.CLOSED : CHANNEL_STATES.OPEN;
                self.call('local_storage', 'setItem', SUPPORT_CHANNEL_STATE_KEY, channelState);
            }
            if (!self.supportChannelUUID) {
                // this part is only executed the first time the RPC is resolved
                self.supportChannelUUID = channel.uuid;

                // add the channel to the ChatManager
                self._addChannel(_.extend(channel, {
                    id: channel.uuid,
                    is_minimized: _.contains([CHANNEL_STATES.OPEN, CHANNEL_STATES.FOLDED], channelState),
                    state: channelState,
                }));

                // display automatic messages in the channel
                if (!channel.available) {
                    self._addSupportNotAvailableMessage();
                } else {
                    self._addSupportWelcomeMessage();
                }
            } else {
                // the channel has already been added to the ChatManager, so
                // simply re-open it
                channel = self.getChannel(self.supportChannelUUID);
                if (self.discussOpen) {
                    self.openChannel(channel);
                } else {
                    channel.is_folded = channelState === CHANNEL_STATES.FOLDED;
                    self.call('chat_window_manager', 'openChat', channel);
                }
            }
        }).fail(function () {
            self.do_warn(_t("The Support server can't be reached."));
        });
    },
    /**
     * Overrides to prevent from calling the server for messages of the Support
     * channel (which are records on the Support database).
     *
     * @override
     */
    toggleStarStatus: function (msgID) {
        var message = this.getMessage(msgID);
        if (_.contains(message.channel_ids, this.supportChannelUUID)) {
            return $.when();
        }
        return this._super.apply(this, arguments);
    },
    /**
     * Overrides to prevent from calling the server with the Support channel
     * (which is a record on the Support database).
     *
     * @override
     */
    unsubscribe: function (channel) {
        if (channel.id === this.supportChannelUUID) {
            return $.when();
        }
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Adds a message in the Support channel indicating that this channel is
     * not available for now.
     *
     * @private
     */
    _addSupportNotAvailableMessage: function () {
        var msg = {
            author_id: ODOOBOT_ID,
            body: _t("None of our operators are available. <a href='https://www.odoo.com/help' " +
                "target='_blank'>Submit a ticket</a> to ask your question now."),
            channel_ids: [this.supportChannelUUID],
            id: Number.MAX_SAFE_INTEGER, // last message in the channel
        };
        this._addMessage(msg, {silent: true});
    },
    /**
     * Adds a welcome message as first message of the Support channel.
     *
     * @private
     */
    _addSupportWelcomeMessage: function () {
        var channel = this.getChannel(this.supportChannelUUID);
        if (channel.welcome_message) {
            var msg = {
                author_id: channel.operator,
                body: channel.welcome_message,
                channel_ids: [this.supportChannelUUID],
                id: -1, // first message of the channel
            };
            this._addMessage(msg, {silent: true});
        }
    },
    /**
     * Overrides to handle the Support channel case: fetches the messages from
     * the Support database in that case.
     *
     * @override
     * @private
     */
    _fetchFromChannel: function (channel, options) {
        var self = this;
        if (channel.id === this.supportChannelUUID) {
            var domain = options && options.domain || [];
            var cache = this._getChannelCache(channel, domain);
            if (options && options.loadMore) {
                var minMessageID = cache.messages[0].id;
                domain = [['id', '<', minMessageID]].concat(domain);
            }

            return supportSession.rpc('/odoo_im_support/fetch_messages', {
                    domain: domain,
                    channel_uuid: session.support_token,
                    limit: SUPPORT_CHANNEL_LIMIT,
                }).then(function (msgs) {
                    if (!cache.all_history_loaded) {
                        cache.all_history_loaded =  msgs.length < SUPPORT_CHANNEL_LIMIT;
                    }
                    cache.loaded = true;

                    _.each(msgs, function (msg) {
                        _.extend(msg, {channel_ids: [self.supportChannelUUID]});
                        self._addMessage(msg, {
                            channel_id: self.supportChannelUUID,
                            silent: true,
                            domain: domain,
                        });
                    });
                    var channelCache = self._getChannelCache(channel, domain);
                    return channelCache.messages;
                });
        }
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     * @private
     */
    _makeChannel: function (data) {
        var channel = this._super.apply(this, arguments);
        if (channel.id === this.supportChannelUUID) {
            channel.supportChannel = true;
            channel.name = _t('Support');
            channel.available = data.available;
            if (!channel.available) {
                channel.name += _t(' (offline)');
            }
            channel.welcome_message = data.welcome_message;
            channel.operator = data.operator;
        }
        return channel;
    },
    /**
     * @override
     * @private
     */
    _makeMessage: function (data) {
        if (_.contains(data.channel_ids, this.supportChannelUUID) && data.author_id !== ODOOBOT_ID) {
            if (!data.author_id[0]) { // the author is the client
                data.author_id = [session.partner_id, session.name];
            } else { // the author is the operator
                data.author_id[0] = -1; // prevent from conflicting with partners of this instance
                var msg = this._super.apply(this, arguments);
                msg.author_redirect = false;
                msg.avatar_src = "/mail/static/src/img/odoo_o.png";
                return msg;
            }
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
     * Initiates a longpoll with the server hosting the Support channel.
     *
     * @private
     * @param {integer} [pollingDelay=POLL_TIMEOUT_DELAY] the longpolling
     * timeout delay to set
     */
    _startPollingSupport: function (pollingDelay) {
        this.pollingSupport = true;
        supportBus.add_channel(this.supportChannelUUID);
        supportBus.start_polling();
        this._setPollTimeout(pollingDelay);
    },
    /**
     * Stops the longpoll with the server hosting the Support channel.
     *
     * @private
     */
    _stopPollingSupport: function () {
        this.pollingSupport = false;
        supportBus.stop_polling();
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
            var msg = _.extend(notification[1], {
                channel_ids: [self.supportChannelUUID],
            });
            self._manageChannelNotification(msg);
        });
    },
});


// Unfortunately, we can't override init() of ChatManager because it is called
// before the include is applied, so we override the WebClient instead to call
// an initialization hook for Livechat Support in the ChatManager service.
WebClient.include({
    /**
     * Overrides to ask the ChatManager service to check whether there is a
     * pending chat session with Support, and if so, to re-open it.
     *
     * @override
     */
    show_application: function () {
        this.call('chat_manager', 'initSupport');
        return this._super.apply(this, arguments);
    },
});

});
