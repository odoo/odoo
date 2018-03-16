odoo.define('mail.model.Conversation', function (require) {
"use strict";

var Thread = require('mail.model.Thread');

var session = require('web.session');

var Conversation = Thread.extend({

    init: function (parent, data, options, commands) {
        this._super.apply(this, arguments);

        this._cache = {
            '[]': {
                allHistoryLoaded: false,
                loaded: false,
                messages: [],
            }
        };
        this._id = data.id;
        this._name = data.name;
        this._type = data.type || data.channel_type;
        /**
         * any new message that has not been read yet
         */
        this._unreadCounter = 0;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Add `message` to this conversation
     *
     * @private
     * @param {Object} message
     * @param {Array} domain
     */
    addMessage: function (message, domain) {
        var cache = this._getCache(domain);
        var index = _.sortedIndex(cache.messages, message, function (msg) {
            return msg.getID();
        });
        if (cache.messages[index] !== message) {
            cache.messages.splice(index, 0, message);
        }
    },
    /**
     * @return {integer|string} string for mailboxes (e.g. 'mailbox_inbox')
     */
    getID: function () {
        return this._id;
    },
    /**
     * @param {Array} [domain]
     * @param {boolean} [loadMore=false]
     * @return {$.Promise<Object[]>} list of messages
     */
    getMessages: function (domain, loadMore) {
        if (loadMore) {
            return this._fetchMessages(domain, true);
        }
        var cache = this._getCache(domain);
        if (cache.loaded) {
            return $.when(cache.messages);
        } else {
            return this._fetchMessages(domain);
        }
    },
    /**
     * @return {string|Object} object for lazy translated names with _lt
     */
    getName: function () {
        return this._name;
    },
    /**
     * @return {string}
     */
    getType: function () {
        return this._type;
    },
    /**
     * @return {integer}
     */
    getUnreadCounter: function () {
        return this._unreadCounter;
    },
    /**
     * State whether all messages have been loaded or not
     *
     * @param  {Array} domain
     * @return {boolean}
     */
    isAllHistoryLoaded: function (domain) {
        return this._getCache(domain).allHistoryLoaded;
    },
    /**
     * By default, any conversation is not a chat
     */
    isChat: function () {
        return false;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Gets messages from channel
     *
     * @private
     * @param  {Array} [pDomain] filter on the messages of the channel
     * @param  {boolean} [loadMore] Whether it should load more message
     * @return {$.Promise<Object[]>} resolved with list of messages
     */
    _fetchMessages: function (pDomain, loadMore) {
        var self = this;
        var domain =
            (this._id === 'mailbox_inbox') ? [['needaction', '=', true]] :
            (this._id === 'mailbox_starred') ? [['starred', '=', true]] :
            [['channel_ids', 'in', [this._id]]];

        var cache = this._getCache(pDomain);

        if (pDomain) {
            domain = domain.concat(pDomain || []);
        }
        if (loadMore) {
            var minMessageID = cache.messages[0].getID();
            domain = [['id', '<', minMessageID]].concat(domain);
        }

        return this._rpc({
            model: 'mail.message',
            method: 'message_fetch',
            args: [domain],
            kwargs: { limit: this._FETCH_LIMIT, context: session.user_context },
        })
        .then(function (msgs) {
            if (!cache.allHistoryLoaded) {
                cache.allHistoryLoaded = msgs.length < self._FETCH_LIMIT;
            }
            cache.loaded = true;
            _.each(msgs, function (msg) {
                self._chatManager.addMessage(msg, {
                    silent: true,
                    domain: pDomain,
                });
            });
            cache = self._getCache(pDomain || []);
            return cache.messages;
        });
    },
    /**
     * Get channel content from the cache
     * Useful to get cached messages.
     *
     * @private
     * @param  {Array} domain
     * @return {Object|undefined}
     */
    _getCache: function (domain) {
        var stringifiedDomain = JSON.stringify(domain || []);
        if (!this._cache[stringifiedDomain]) {
            this._cache[stringifiedDomain] = {
                allHistoryLoaded: false,
                loaded: false,
                messages: [],
            };
        }
        return this._cache[stringifiedDomain];
    },
});


/**
 * Chat Window compatibility for mailboxes
 */
Conversation.include({
    init: function () {
        this._super.apply(this, arguments);
        this._chatBus = this._chatManager.getChatBus();

        this._detached = false; // all conversations are not detached by default
        this._folded = false; // all conversations are unfolded by default
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Close the channel
     */
    close: function () {
        this.updateChatWindowVisibility({
            newFoldState: this._folded,
            newDetachState: false,
        });
    },
    /**
     * Detach this conversation
     */
    detach: function () {
        this.updateChatWindowVisibility({
            newFoldState: this._folded,
            newDetachState: true,
        });
    },
    /**
     * Folds/Minimize the conversation
     *
     * @param  {boolean} folded
     */
    fold: function (folded) {
        this.updateChatWindowVisibility({
            newFoldState: folded ? 'folded' : 'open',
            newDetachState: this._detached,
        });
    },
    /**
     * Update its chat window
     *
     * Note: public because the channel should be registered in ChatManager,
     * so we cannot do this directly on "new Channel()"
     */
    handleChatWindowVisibility: function () {
        this._chatBus.trigger(this.isDetached() ? 'open_chat' : 'close_chat', this);
    },
    /**
     * @return {boolean}
     */
    isDetached: function () {
        return this._detached;
    },
    /**
     * @return {boolean}
     */
    isFolded: function () {
        return this._folded;
    },
    /**
     * Open the conversation:
     *
     *      1. If discuss is opened, asks discuss to open the conversation
     *      2. Otherwise, asks the chat_window_manager to detach the conversation
     */
    open: function () {
        this._chatBus.trigger(this._chatManager.isDiscussOpen() ? 'open_conversation' : 'detach_conversation', this);
    },
    /**
     * @param {Object} params
     * @param {string} serverData.newFoldState
     * @param {boolean} serverData.newDetachState
     */
    updateChatWindowVisibility: function (params) {
        this._detached = params.newDetachState;
        this._folded = params.newFoldState === 'folded';
        this.handleChatWindowVisibility();
    },
});

/**
 * missing utility functions for chat window
 * (mailbox compatibility, may be dropped one way or other?)
 */
Conversation.include({

    /**
     * By default, a conversation does not have any command
     *
     * @return {Array}
     */
    getCommands: function () {
        return [];
    },
    /**
     * By default, a conversation has not listener
     *
     * @abstract
     * @return {$.Promise<Object[]>}
     */
    getMentionPartnerSuggestions: function () {
        return $.when([]);
    },
    /**
     * By default, mark as seen does nothing on the conversation
     *
     * @abstract
     */
    markAsSeen: function () {},

});

return Conversation;

});
