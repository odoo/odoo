odoo.define('im_support.SupportChannel', function (require) {
"use strict";

var supportSession = require('im_support.SupportSession');

var SearchableThread = require('mail.model.SearchableThread');

var core = require('web.core');
var session = require('web.session');

var _t = core._t;

/**
 * This mail model represents support channel, which are communication channels
 * between two different databases for support-related reasons. It is like
 * livechat, but both users are in different databases, and both users
 * communicate from their respective 'backend' access.
 *
 * FIXME: it should inherit from mail.model.Channel, not from
 * mail.model.SearchableThread
 */
var SupportChannel = SearchableThread.extend({

    /**
     * @override
     * @param {Object} params
     * @param {Object} params.data
     * @param {boolean} params.data.available
     * @param {string|integer} params.data.id
     * @param {boolean} params.data.is_minimized
     * @param {Object} params.data.operator
     * @param {string} params.data.state ['open', 'closed', 'folded']
     * @param {string} params.data.uuid
     * @param {string} params.data.welcome_message
     * @param {Object} params.options
     */
    init: function (params) {
        var data = params.data;

        data.type = 'support_channel';
        data.name = _t("Support");

        this._available = data.available;
        this._operator = data.operator;
        this._supportChannelUUID = data.id;
        this._welcomeMessage = data.welcome_message;
        if (!this._available) {
            data.name += _t(" (offline)");
        }

        this._super.apply(this, arguments);

        // force stuff that should probably be in Thread (or at least
        // SearchableThread), but that are currently in Channel
        this._detached = data.is_minimized;
        this._folded = data.state === 'folded';
        this._uuid = data.uuid;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Adds the default message in the Support channel (depending on its
     * availability).
     */
    addDefaultMessage: function () {
        if (!this._available) {
            this._addSupportNotAvailableMessage();
        } else {
            this._addSupportWelcomeMessage();
        }
    },
    /**
     * Overrides to store the state of the Support channel in the localStorage.
     *
     * @override
     */
    close: function () {
        this._super.apply(this, arguments);
        this.call('mail_service', 'updateSupportChannelState', 'closed');
    },
    /**
     * Overrides to store the state of the Support channel in the localStorage.
     *
     * @override
     */
    detach: function () {
        this._super.apply(this, arguments);
        this.call('mail_service', 'updateSupportChannelState', 'open');
    },
    /**
     * Overrides to store the state of the Support channel in the localStorage.
     *
     * @override
     */
    fold: function (folded) {
        this._super.apply(this, arguments);
        var value = folded ? 'folded' : 'open';
        this.call('mail_service', 'updateSupportChannelState', value);
    },
    /**
     * FIXME: this override is necessary just because the support channel is
     * considered as a channel, even though it does not inherit from
     * mail.model.Channel.
     *
     * @returns {integer}
     */
    getNeedactionCounter: function () {
        return 0;
    },
    /**
     * @return {string} uuid of this channel
     */
    getUUID: function () {
        return this._uuid;
    },
    /**
     * FIXME: this method is necessary just because the support channel is
     * considered as a channel, even though it does not inherit from
     * mail.model.Channel.
     *
     * @returns {boolean}
     */
    hasBeenPreviewed: function () {
        return true;
    },
    /**
     * @returns {boolean} true iff the Support channel is available
     */
    isAvailable: function () {
        return this._available;
    },
    /**
     * FIXME: this override is necessary just because the support channel is
     * considered as a channel, even though it does not inherit from
     * mail.model.Channel.
     *
     * @override
     * @returns {boolean}
     */
    isChannel: function () {
        return true;
    },
    /**
     * Called when fold or detach (or both) status have changed on the support
     * channel.
     *
     * Note: this is partially a hack due to support channel not being a
     * channel. Also, the support channel uses another way to handle its window
     * state, by means of the local storage.
     *
     * @param {Object} params
     * @param {boolean} [params.folded]
     * @param {boolean} [params.detached]
     */
    updateWindowState: function (params) {
        if ('detached' in params) {
            this._detached = params.detached;
        }
        if ('folded' in params) {
            this._folded = params.folded;
        }

        if (!this._detached) {
            this.call('mail_service', 'updateSupportChannelState', 'closed');
        } else {
            var value = this._folded ? 'folded' : 'open';
            this.call('mail_service', 'updateSupportChannelState', value);
        }
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
            author_id: this.call('mail_service', 'getOdoobotID'),
            body: _t("None of our operators are available. <a href='https://www.odoo.com/help' " +
                "target='_blank'>Submit a ticket</a> to ask your question now."),
            channel_ids: [this.getID()],
            id: Number.MAX_SAFE_INTEGER, // last message in the channel
        };
        this.call('mail_service', 'addMessage', msg, { silent: true });
    },
    /**
     * Adds the welcome message as first message of the Support channel.
     *
     * @private
     */
    _addSupportWelcomeMessage: function () {
        if (this._welcomeMessage) {
            var msg = {
                author_id: this._operator,
                body: this._welcomeMessage,
                channel_ids: [this.getID()],
                id: -1, // first message of the channel
            };
            this.call('mail_service', 'addMessage', msg, { silent: true });
        }
    },
    /**
     * Fetches the messages from the Support server.
     *
     * @override
     * @private
     */
    _fetchMessages: function (pDomain, loadMore) {
        var self = this;
        var domain = [];
        var cache = this._getCache(pDomain);
        if (pDomain) {
            domain = domain.concat(pDomain || []);
        }
        if (loadMore) {
            // ignore the welcome message (ID==-1)
            var msgs = cache.messages.filter(function(m) {return m.getID() !== -1});
            var minMessageID = msgs[0].getID();
            domain = [['id', '<', minMessageID]].concat(domain);
        }
        return supportSession.rpc('/odoo_im_support/fetch_messages', {
                domain: domain,
                channel_uuid: session.support_token,
                limit: self._FETCH_LIMIT,
        }).then(function (messages) {
            if (!cache.allHistoryLoaded) {
                cache.allHistoryLoaded = messages.length < self._FETCH_LIMIT;
            }
            cache.loaded = true;
            _.each(messages, function (message) {
                message.channel_ids = [self.getID()];
                message.channel_id = self.getID();
                self.call('mail_service', 'addMessage', message, {
                    silent: true,
                    domain: pDomain,
                });
            });
            cache = self._getCache(pDomain || []);
            return cache.messages;
        });
    },

    /**
     * Posts the message on the Support server.
     *
     * @override
     * @private
     * @return {$.Promise}
     */
    _postMessage: function (data) {
        // ensure that the poll is active before posting the message
        this.call('mail_service', 'startPollingSupport');
        return supportSession.rpc('/odoo_im_support/chat_post', {
            uuid: this._supportChannelUUID,
            message_content: data.content,
        });
    },
});

return SupportChannel;

});
