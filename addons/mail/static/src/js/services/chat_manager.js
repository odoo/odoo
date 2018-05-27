odoo.define('mail.ChatManager', function (require) {
"use strict";

var ChatWindowManager = require('mail.ChatWindowManager');
var emojiUnicodes = require('mail.emojiUnicodes');
var Channel = require('mail.model.Channel');
var DocumentChat = require('mail.model.DocumentChat');
var Mailbox = require('mail.model.Mailbox');
var Message = require('mail.model.Message');
var utils = require('mail.utils');

var Bus = require('web.Bus');
var Class = require('web.Class');
var config = require('web.config');
var core = require('web.core');
var Mixins = require('web.mixins');
var ServicesMixin = require('web.ServicesMixin');
var session = require('web.session');
var webClient = require('web.web_client');

var _t = core._t;
var _lt = core._lt;

var PREVIEW_MSG_MAX_SIZE = 350;  // optimal for native english speakers

/**
 * This service handles everything about chat channels and messages.
 *
 * There are basically two points of entry:
 *
 *      1. Calling a public method by means of 'this.call'
 *      2. Receiving events on busBus (e.g. 'notification')
 */
var ChatManager =  Class.extend(Mixins.EventDispatcherMixin, ServicesMixin, {

    init: function (parent) {
        var self = this;

        Mixins.EventDispatcherMixin.init.call(this, arguments);
        this.setParent(parent);

        // chat window manager needs it, so it must be assigned before
        // chat window manager is instantiated
        this._chatBus = new Bus(this);

        this.chatWindowManager = new ChatWindowManager(this); // temporarily public, due to chat_service

        this._busBus = this.call('bus_service', 'getBus');
        this._cannedResponses = [];
        this._conversations = []; // channels & mailboxes
        this._commands = [];
        this._discussMenuID = undefined;
        this._discussOpen = false;
        this._documentChats = [];
        this._emojis = [];
        this._mentionPartnerSuggestions = []; // list of employees for chatter mentions
        this._messages = [];
        this._outOfFocusUnreadMessageCounter = 0; // # of message received when odoo is out of focus
        this._pinnedDmPartners = [];  // partner_ids we have a pinned DM with
        this._unreadConversationCounter = 0; // # of unread channels

        // add emojis from list of emoji_unicodes
        var lastAdded = null;
        _.each(emojiUnicodes, function (unicode, key) {
            if (lastAdded !== unicode) {
                lastAdded = unicode;
                self._emojis.push({
                    source: key,
                    unicode_source: unicode,
                    description: key
                });
            }
        });

        // listen on buses
        this._chatBus.on('discuss_open', this, this._onDiscussOpen);
        this._busBus.on('window_focus', this, this._onWindowFocus);

        this._initializeFromServer();
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Add a new document chat, using 'model' and 'resID'
     *
     * Use by
     *      {mail.ThreadField} - create document chat on loading document record
     *      self - message from document for which we do not have registered the document chat yet
     *
     * @param {string} model
     * @param {integer} resID
     * @return {mail.model.DocumentChat}
     */
    addDocumentChat: function (model, resID) {
        var documentChat = this.getDocumentChat(model, resID);
        if (!documentChat) {
            documentChat = new DocumentChat(this, model, resID);
            this._documentChats.push(documentChat);
        }
        return documentChat;
    },
    /**
     * Adds a message
     *
     * Use by
     *      {mail.model.Channel} - after fetching messages, add them locally
     *      {mail.model.DocumentChat} - after fetching messages, add then locally
     *      self - after posting a message on document chat, fetch format and add it locally
     *           - when adding a channel in mobile, data contains last_message (used for mobile channel preview)
     *           - when fetching channel previews, data contains last_message (used for channels preview in general)
     *           - when receiving a channel notification (new message channel)
     *           - when receiving a needaction notification (new message inbox)
     *
     * @param  {Object} data message data
     * @param  {integer} data.id
     * @param  {Object} [options]
     * @param  {Array} [options.domain]
     * @param  {boolean} [options.incrementUnread] whether we should increment
     *   the unread_counter of channel.
     * @param  {boolean} [options.silent] whether it should inform in the chatBus
     *   of the newly created message.
     * @return {mail.model.Message} message object
     */
    addMessage: function (data, options) {
        options = options || {};
        var msg = this.getMessage(data.id);
        if (!msg) {
            msg = new Message(this, data, this._emojis);
            // Keep the array ordered by id when inserting the new message
            var index = _.sortedIndex(this._messages, msg, function (msg) {
                return msg.getID();
            });
            this._messages.splice(index, 0, msg);
            this._addNewMessagePostprocessDocumentChat(msg);
            this._addNewMessagePostprocessConversation(msg, data, options);
            if (!options.silent) {
                this._chatBus.trigger('new_message', msg);
            }
        } else if (options.domain && options.domain !== []) {
            this._addMessageToConversations(msg, options.domain);
        }
        return msg;
    },
    /**
     * Creates a channel, can be either a true channel or a DM based on `type`
     *
     * Use by
     *      {mail.Discuss} - when creating a new public channel (input text then select)
     *                     - when creating a new private channel (input text then ENTER)
     *                     - when creating a new DM (input text then select)
     *      self - when redirect to a partner, create DM
     *
     * @param  {integer|string} name id of partner (in case of dm) or name
     * @param  {string} type ['dm', 'public', 'private']
     * @return {$.Promise}
     */
    createChannel: function (name, type) {
        if (type === 'dm') {
            return this._createDM(name);
        } else {
            return this._createChannel(name, type);
        }
    },
    /**
     * Decrements the number of conversation which contains unread messages
     *
     * Use by {mail.model.Channel} - on any change of its unread counter
     */
    decrementUnreadConversationCounter: function () {
        return this._unreadConversationCounter--;
    },
    /**
     * Returns the list of canned responses
     * A canned response is a pre-formatted text that is triggered with
     * some keystrokes, such as with ':'.
     *
     * Use by {mail.composer} - show canned responses in composer dropdown menu
     *
     * @return {Array} array of Objects (mail.shortcode)
     */
    getCannedResponses: function () {
        return this._cannedResponses;
    },
    /**
     * Returns a channel corresponding to the given id.
     *
     * Use by
     *      {mail.Discuss} - force fetch members on adding a new members in a channel (useful for updating mentions)
     *                     - use default channel
     *                     - on switching channel
     *                     - on leaving a channel, back to mailbox_inbox
     *                     - unsubscribe from a channel
     *      {mail.DiscussMobile} - switch mailbox (inbox or starred)
     *                           - set inbox on tab click 'Inbox'
     *                           - set channel on clicking on this channel
     *      {mail.ExtendedChatWindow} - post message in channel
     *                                - get commands and members of a channel
     *      {mail.systray} - get mailbox_inbox for message previews
     *                     - open channel when clicking on it from messaging menu
     *      {mail.model.ChatSession} - fold channel
     *                               - post message in channel
     *      {mail.model.Message} - set channel origin of message + its name
     *      self - on join channel, if already channel locally, just return it
     *           - on add channel, if already channel locally, just update its fold state
     *           - on add message, add it to channel that it refers to (too many)
     *           - on channel previews, mark channel as previewed (so that no fetch again)
     *           - on receiving a message, invalidate caches of related channels
     *           - on receiving a message, if channel in cache, increment its unread counter
     *           - on channel seen notif, mark this channel as seen (+ update last message)
     *           - on receiving chat session notif, update chat window state of channel + open/close it
     *           - on receiving mark as read notif, update needaction counter of channel
     *           - on receiving needaction notif, update needaction counter of channel
     *           - on receiving unsubscribe notif, remove this channel
     *           - on receiving toggle star notif, update starred mailbox cache
     *      {mail.ChatWindowManager} - get messages of channel
     *                               - close channel on removing its chat session
     *                               - mark channel as seen on last message visible
     *
     * @param  {string|integer} id e.g. 'mailbox_inbox', 'mailbox_starred'
     * @return {mail.model.Channel|undefined} the channel, if it exists
     */
    getChannel: function (id) {
        return _.find(this._conversations, function (conversation) {
            return conversation.getID() === id && conversation.getType() !== 'mailbox';
        });
    },
    /**
     * Returns a list of channels
     *
     * Use by
     *      {mail.Discuss} - on rendering sidebar of discuss with list of channels
     *      {mail.DiscussMobile} - on selecting channels with certain type for channel previews
     *      {mail.systray} - on selecting channels with certain type for channel previews
     *      {mail.ChatWindowManager} - open channel if they are detached (from mail/init_messaging)
     *
     * @return {mail.model.Channel[]} list of conversations
     */
    getChannels: function () {
        return _.filter(this._conversations, function (conversation) {
            return conversation.getType() !== 'mailbox';
        });
    },
    /**
     * Returns the content that will be shown in the mail navbar dropdown
     *
     * Use by
     *      {mail.DiscussMobile} - display channel previews
     *      {mail.systray} - display channel previews
     *
     * @param  {mail.model.Channel[]} channels
     * @return {$.Promise<mail.model.ChannelPreview[]>} resolved with list of channel previews
     */
    getChannelPreviews: function (channels) {
        var self = this;
        return this._getChannelPreviews(channels).then(function (channelPreviews) {
            var sortedChannelsPreview = self._sortChannelPreviews(channelPreviews);
            return sortedChannelsPreview;
        });
    },
    /**
     * list of events:
     *
     *
     * activity_updated
     *          listen:  {mail.Discuss}
     *                   {mail.systray}
     *          trigger: self
     *
     * anyone_listening
     *          listen:  {mail.Discuss}
     *                   {mail.ChatWindowManager}
     *          trigger: self
     *
     * detach_channel
     *          listen:  {mail.ChatWindowManager}
     *          trigger: self
     *
     * discuss_open
     *          listen:  {mail.Discuss}
     *                   self
     *          trigger: {mail.ExtendedChatWindow}
     *
     * new_channel
     *          listen:  {mail.Discuss}
     *          trigger: self
     *
     * new_message
     *          listen:  {mail.Discuss}
     *                   {mail.ThreadField}
     *                   {mail.ChatWindowManager}
     *          trigger: self
     *
     * open_channel
     *          listen:  {mail.Discuss}
     *          trigger: {mail.model.Channel}
     *
     * unsubscribe_from_channel
     *          listen:  {mail.Discuss}
     *                   {mail.ChatWindowManager}
     *          trigger: self
     *
     * update_channel_unread_counter
     *          listen:  {mail.Discuss}
     *                   {mail.systray}
     *                   {mail.ChatWindowManager}
     *          trigger: {mail.model.Channel}
     *
     * update_dm_presence
     *          listen:  {mail.Discuss}
     *                   {mail.ChatWindowManager}
     *          trigger: self
     *
     * update_message
     *          listen:  {mail.Discuss}
     *                   {mail.ThreadField}
     *                   {mail.ChatWindowManager}
     *          trigger: self
     *
     * update_needaction
     *          listen:  {mail.Discuss}
     *                   {mail.systray}
     *          trigger: self
     *
     * update_starred
     *          listen:  {mail.Discuss}
     *          trigger: self
     *
     * voip_reload_chatter
     *          listen:  {voip.Activity}
     *          trigger: {voip.Phonecall}
     *
     *
     * Use by
     *      {voip.Activity} - listen
     *      {voip.Phonecall} - trigger
     *      {mail.Discuss} - listen
     *      {mail.ExtendedChatWindow} - trigger
     *      {mail.systray} - listen
     *      {mail.ThreadField} - listen
     *      {mail.model.Channel} - trigger
     *      {mail.ChatWindowManager} - listen
     *
     * @return {web.Bus} the chat bus
     */
    getChatBus: function () {
        return this._chatBus;
    },
    /**
     * Returns conversation, if any
     *
     * @param  {string|integer} id e.g. 'mailbox_inbox', 'mailbox_starred'
     * @return {mail.model.Conversation|undefined} the channel, if it exists
     */
    getConversation: function (id) {
        return _.find(this._conversations, function (conversation) {
            return conversation.getID() === id;
        });
    },
    /**
     * Returns a list of conversations
     *
     * Use by
     *      {mail.Discuss} - on rendering sidebar of discuss with list of channels
     *      {mail.DiscussMobile} - on selecting channels with certain type for channel previews
     *      {mail.systray} - on selecting channels with certain type for channel previews
     *      {mail.ChatWindowManager} - open channel if they are detached (from mail/init_messaging)
     *
     * @return {mail.model.Channel[]} list of conversations
     */
    getConversations: function () {
        return this._conversations;
    },
    /**
     * Returns the record id of ir.ui.menu for Discuss
     *
     * Use by {mail.systray} - on click preview on mailbox_inbox not linked to document, open discuss
     *
     * @return {integer} record id
     */
    getDiscussMenuID: function () {
        return this._discussMenuID;
    },
    /**
     * Gets direct message channel
     *
     * Use by
     *      {mail.Discuss} - on entering partner in 'Add DM', set it as selected channel in discuss
     *      self - on receiving bus presence notification, update status of dm
     *      {mail.ChatWindowManager} - open and detach DM when switching to DM from new chat session
     *
     * @param  {integer} partnerID
     * @return {Object|undefined} channel
     */
    getDmFromPartnerID: function (partnerID) {
        return _.findWhere(this._conversations, { directPartnerID: partnerID });
    },
    /**
     * Returns a document chat corresponding to the given model and resID.
     *
     * Use by
     *      {mail.ThreadField} - update list of message ids
     *      self - create it if not defined locally
     *
     * @param  {string} model of the document chat, if it exists
     * @return {integer} resID of the document chat, if it exists
     */
    getDocumentChat: function (model, resID) {
        return _.find(this._documentChats, function (documentChat) {
            return documentChat.getDocumentModel() === model &&
                    documentChat.getDocumentResID() === resID;
        });
    },
    /**
     * Returns list of emojis Objects
     *
     * Use by {mail.composer}
     *
     * @return {Object[]} list of emojis
     * ['id', 'source', 'unicode_source', 'substitution', 'description']
     */
    getEmojis: function () {
        return this._emojis;
    },
    /**
     * @param {string} mailboxID
     * @return {mail.model.Mailbox} the mailbox, if any
     */
    getMailbox: function (mailboxID) {
        return _.find(this._conversations, function (conversation) {
            return conversation.getID() === 'mailbox_' + mailboxID;
        });
    },
    /**
     * Get partners as mentions from a chatter
     * Typically all employees as partner suggestions.
     *
     * Use by {mail.Chatter}
     *
     * @return {Array<Object[]>}
     */
    getMentionPartnerSuggestions: function () {
        return this._mentionPartnerSuggestions;
    },
    /**
     * Gets message from its id
     *
     * Use by
     *      {mail.Discuss}
     *      {mail.ThreadField}
     *      {mail.model.ChatSession}
     *      self
     *      {mail.ChatWindowManager}
     *
     * @param  {integer} msgID
     * @return {mail.model.Message|undefined} the matched message (if any)
     */
    getMessage: function (msgID) {
        return _.find(this._messages, function (message) {
            return message.getID() === msgID;
        });
    },
    /**
     * Gets all messages that have been fetched from the server
     *
     * Use by
     *      {mail.ThreadField}
     *      self
     *
     * @return {mail.model.Message[]} list of messages
     */
    getMessages: function () {
        return this._messages;
    },
    /**
     * Gets the number of conversation which contains unread messages
     *
     * Use by {mail.systray}
     *
     * @return {integer} unread conversation counter
     */
    getUnreadConversationCounter: function () {
        return this._unreadConversationCounter;
    },
    /**
     * Increments the number of conversation which contains unread messages
     *
     * Use by {mail.model.Channel}
     */
    incrementUnreadConversationCounter: function () {
        this._unreadConversationCounter++;
    },
    /**
     * State whether discuss app is open or not
     *
     * Use by
     *      {mail.model.Channel}
     *      self
     *
     * @return {boolean}
     */
    isDiscussOpen: function () {
        return this._discussOpen;
    },
    /**
     * Use by
     *      {mail.Discuss}
     *      {mail.systray}
     *      {mail.ThreadField}
     *
     * @return {$.Promise}
     */
    isReady: function () {
        return this._isReady;
    },
    /**
     * Join an existing channel
     * See @createChannel to join a new channel
     *
     * Use by
     *      {mail.Discuss}
     *      {mail.ThreadField}
     *      {mail.model.ChatSession}
     *      self
     *
     * @param  {integer} channelID
     * @param  {Object} [options]
     * @return {$.Promise<mail.model.Channel>} resolved with channel object
     */
    joinChannel: function (channelID, options) {
        var def;
        var channel = this.getChannel(channelID);
        if (channel) {
            // channel already joined
            def = $.when(channel);
        } else {
            def = this._joinAndAddChannel(channelID, options);
        }
        return def;
    },
    /**
     * Use by
     *      {mail.model.Channel}
     *      self
     *
     * @param {Object} data
     * @return {Object} msg to post
     */
    makeBasicPostMessage: function (data) {
        // This message will be received from the mail composer as html content subtype
        // but the urls will not be linkified. If the mail composer takes the responsibility
        // to linkify the urls we end up with double linkification a bit everywhere.
        // Ideally we want to keep the content as text internally and only make html
        // enrichment at display time but the current design makes this quite hard to do.
        var body = utils.parse_and_transform(_.str.trim(data.content), utils.add_link);

        var msg = {
            partner_ids: data.partner_ids,
            body: body,
            attachment_ids: data.attachment_ids,
        };

        this._substituteEmojisByUnicodes(msg);

        if ('subject' in data) {
            msg.subject = data.subject;
        }
        return msg;
    },
    /**
     * Mark messages as read
     *
     * Use by
     *      {mail.Discuss}
     *      {mail.model.DocumentChat}
     *
     * @param  {Array} msgIDs list of messages ids
     * @return {$.Promise}
     */
    markAsRead: function (msgIDs) {
        var self = this;
        var ids = _.filter(msgIDs, function (id) {
            var message = self.getMessage(id);
            // If too many messages, not all are fetched, and some might not be found
            return !message || message.isNeedaction();
        });
        if (ids.length) {
            return this._rpc({
                    model: 'mail.message',
                    method: 'set_message_done',
                    args: [ids],
                });
        } else {
            return $.when();
        }
    },
    /**
     * Opens the chat window in discuss.
     *
     * Use by {mail.ChatWindowManager}
     *
     * @param  {integer} partnerID
     * @return {$.Promise<Object>} resolved with the dm channel
     */
    openAndDetachDm: function (partnerID) {
        return this._rpc({
                model: 'mail.channel',
                method: 'channel_get_and_minimize',
                args: [[partnerID]],
            })
            .then(this._addChannel.bind(this));
    },
    /**
     * Post message for document chat
     *
     * Use by {mail.ThreadField}
     *
     * @param {Object} data data related to the new message
     * @param {Object} options
     * @param {string} options.model
     * @param {integer} options.res_id
     * @return {$.Promise} resolved when message has been posted
     */
    postMessage: function (data, options) {
        var self = this;
        var msg = this.makeBasicPostMessage(data);

        _.extend(msg, {
            content_subtype: data.content_subtype,
            context: data.context,
            message_type: data.message_type,
            subtype: data.subtype,
            subtype_id: data.subtype_id,
        });

        return this._rpc({
                model: options.model,
                method: 'message_post',
                args: [options.resID],
                kwargs: msg,
            })
            .then(function (msgID) {
                return self._rpc({
                        model: 'mail.message',
                        method: 'message_format',
                        args: [[msgID]],
                    })
                    .then(function (msgs) {
                        msgs[0].model = options.model;
                        msgs[0].res_id = options.resID;
                        self.addMessage(msgs[0]);
                    });
            });
    },
    /**
     * Special redirection handling for given model and id
     *
     * If the model is res.partner, and there is a user associated with this
     * partner which isn't the current user, open the DM with this user.
     * Otherwhise, open the record's form view, if this is not the current user's.
     *
     * Use by {mail.Discuss}
     *
     * @param {string} resModel model to open
     * @param {integer} resID record to open
     * @param {function} [dmRedirectionCallback] only used if 'res.partner'
     */
    redirect: function (resModel, resID, dmRedirectionCallback) {
        if (resModel === 'res.partner') {
            this._redirectPartner(resModel, resID, dmRedirectionCallback);
        } else {
            this._redirectDefault(resModel, resID);
        }
    },
    /**
     * Removes all messages from the current model except 'needaction'.
     * We want to keep it in inbox.
     *
     * Use by {mail.ThreadField}
     *
     * @param {string} model
     */
    removeChatterMessages: function (model) {
        this._messages = _.reject(this._messages, function (message) {
            return (!message.isLinkedToConversation()) && message.getDocumentModel() === model;
        });
    },
    /**
     * Search among prefetched partners, using the string 'searchVal'
     *
     * Use by
     *      {mail.Discuss}
     *      {mail.ExtendedChatWindow}
     *
     * @param {string} searchVal
     * @param {integer} limit max number of found partners in the response
     * @return {$.Promise<Object[]>} list of found partners (matching 'searchVal')
     */
    searchPartner: function (searchVal, limit) {
        var def = $.Deferred();
        var partners = this._searchPartnerPrefetch(searchVal, limit);

        if (!partners.length) {
            def = this._searchPartnerFetch(searchVal, limit);
        } else {
            def = $.when(partners);
        }
        return def.then(function (partners) {
            var suggestions = _.map(partners, function (partner) {
                return { id: partner.id, value: partner.name, label: partner.name };
            });
            return _.sortBy(suggestions, 'label');
        });
    },
    /**
     * Unstars all messages from all channels
     *
     * Use by {mail.Discuss}
     *
     * @return {$.Promise}
     */
    unstarAll: function () {
        return this._rpc({
                model: 'mail.message',
                method: 'unstar_all',
                args: [[]]
            });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Adds a channel and returns it.
     * Simply returns the channel if already exists.
     *
     * @private
     * @param  {Object} data
     * @param  {string|integer} data.id id of channel or 'mailbox_inbox', 'mailbox_starred', ...
     * @param  {string|Object} data.name name of channel, e.g. 'general'
     * @param  {string} data.type type of channel, e.g. 'mailbox'
     * @param  {string} [data.state] e.g. 'open', 'folded'
     * @param  {Object|integer} [options=undefined]
     * @param  {boolean} [options.silent]
     * @return {Object} the newly or already existing channel
     */
    _addChannel: function (data, options) {
        options = typeof options === 'object' ? options : {};
        var channel = this.getChannel(data.id);
        if (channel) {
            this.chatWindowManager.updateConversationFoldState(channel, data.state);
        } else {
            channel = new Channel(this, data, options, this._commands);
            if (channel.getType() === 'dm') {
                this._pinnedDmPartners.push(channel.directPartnerID);
                this._busBus.update_option('bus_presence_partner_ids', this._pinnedDmPartners);
            }
            this._conversations.push(channel);
            channel.handleChatWindowVisibility();
            if (data.last_message) { // channel_info in mobile, necessary for showing channel preview in mobile
                this.addMessage(data.last_message);
            }
            this._sortConversations();
            if (!options.silent) {
                this._chatBus.trigger('new_channel', channel);
            }
        }
        return channel;
    },
    /**
     * Add a new mailbox
     *
     * @private
     * @param {Object} data
     * @param {Object} options
     * @return {mail.model.Mailbox}
     */
    _addMailbox: function (data, options) {
        options = typeof options === 'object' ? options : {};
        var mailbox = new Mailbox(this, data, options, this._commands);
        this._conversations.push(mailbox);
        mailbox.handleChatWindowVisibility();
        this._sortConversations();
        return mailbox;
    },
    /**
     * Stores `message` to the cache `domain` of all of its channels
     *
     * @private
     * @param  {mail.model.Message} message
     * @param  {Array} domain
     */
    _addMessageToConversations: function (message, domain) {
        var self = this;
        _.each(message.getConversationIDs(), function (conversationID) {
            var conversation = self.getConversation(conversationID);
            if (conversation) {
                conversation.addMessage(message, domain);
            }
        });
    },
    /**
     * For newly added message, postprocess conversations linked to this message
     *
     * @private
     * @param {mail.model.Message} msg
     * @param {Object} data
     * @param {Object} options
     * @param {Array} [options.domain]
     * @param {boolean} [options.incrementUnread]
     * @param {boolean} [options.showNotification]
     */
    _addNewMessagePostprocessConversation: function (msg, data, options) {
        var self = this;
        _.each(msg.getConversationIDs(), function (conversationID) {
            var conversation = self.getConversation(conversationID);
            if (conversation) {
                self._addMessageToConversations(msg, []);
                if (options.domain && options.domain !== []) {
                    self._addMessageToConversations(msg, options.domain);
                }
                if (conversation.getType() !== 'mailbox' && !msg.isAuthor() && !msg.isSystemNotification()) {
                    if (options.incrementUnread) {
                        conversation.incrementUnreadCounter();
                    }
                    if (conversation.isChat() && options.showNotification) {
                        if (!self.isDiscussOpen() && !config.device.isMobile) {
                            // automatically open chat window
                            conversation.updateChatWindowVisibility({
                                newDetachState: true,
                                newFoldState: 'open',
                            });
                        }
                        var query = { is_displayed: false };
                        self._chatBus.trigger('anyone_listening', conversation, query);
                        self._notifyIncomingMessage(msg, query);
                    }
                }
            }
        });
    },
    /**
     * For newly added message, postprocess document chat linked to this message
     *
     * Simply adds the message to the corresponding document chat.
     * If there is no such document chat, create it.
     *
     * @private
     * @param {mail.model.Message} message
     */
    _addNewMessagePostprocessDocumentChat: function (message) {
        var model = message.getDocumentModel();
        var resID = message.getDocumentResID();
        if (model && resID) {
            var documentChat = this.getDocumentChat(model, resID);
            if (!documentChat) {
                documentChat = this.addDocumentChat(model, resID);
            }
            documentChat.addMessage(message);
        }
    },
    /**
     * Create a Channel (other than a DM)
     *
     * @private
     * @param {string} name
     * @param {string} type
     * @return {$.Promise}
     */
    _createChannel: function (name, type) {
        var context = _.extend({ isMobile: config.device.isMobile }, session.user_context);
        return this._rpc({
                model: 'mail.channel',
                method: 'channel_create',
                args: [name, type],
                kwargs: {context: context},
            })
            .then(this._addChannel.bind(this));
    },
    /**
     * Create a Direct Messages Chat
     *
     * @private
     * @param {string} name
     * @return {$.Promise}
     */
    _createDM: function (name) {
        var context = _.extend({ isMobile: config.device.isMobile }, session.user_context);
        return this._rpc({
                model: 'mail.channel',
                method: 'channel_get',
                args: [[name]],
                kwargs: {context: context},
            })
            .then(this._addChannel.bind(this));
    },
    /**
     * @private
     * @param {integer[]} channelIDs
     * @return {$.Promise<Object[]>} resolved with list of channel preview
     */
    _fetchChannelPreviews: function (channelIDs) {
        return this._rpc({
            model: 'mail.channel',
            method: 'channel_fetch_preview',
            args: [channelIDs],
        }, {shadow: true});
    },
    /**
     * Get previews of the channels
     *
     * The preview of a channel is built from the channel information and its
     * lastest message. A channel without a last message is incomplete, so it
     * must fetch this message.
     *
     * Note that a channel could have no message at all, so it fetches for the
     * last message only once per channel. This is correct to not fetch more
     * than once in this case, because any later received message updates
     * automatically the last message of a channel.
     *
     * @private
     * @param {mail.model.Channel[]} channels
     * @return {$.Deferred<mail.model.ChannelPreview[]>} resolved with list of channel previews
     */
    _getChannelPreviews: function (channels) {
        var fetchDef;
        var self = this;

        var previews = _.map(channels, function (channel) {
            return channel.getPreview();
        });
        var incompletePreviews = _.filter(previews, function (preview) {
            return preview.isComplete() === false;
        });

        if (incompletePreviews.length) {
            var ids = _.map(incompletePreviews, function (preview) {
                return preview.getID();
            });
            fetchDef = this._fetchChannelPreviews(ids);
        } else {
            fetchDef = $.when();
        }

        return fetchDef.then(function (fetchedPreviews) {
            // update last message from fetch
            _.each(fetchedPreviews, function (fetchedPreview) {
                    var preview = _.filter(previews, function (preview) {
                        return preview.getID() === fetchedPreview.id;
                    });
                    if (preview) {
                        self.addMessage(fetchedPreview.last_message);
                    }
            });
            // mark these channels as previewed, so that we do not need to fetch preview again
            _.each(previews, function (preview) {
                var channel = self.getChannel(preview.getID());
                channel.markAsPreviewed();
            });
            return previews;
        });
    },
    /**
     * @private
     * @returns {$.Promise}
     */
    _initializeFromServer: function () {
        var self = this;
        this._isReady = session.is_bound.then(function () {
            var context = _.extend({ isMobile: config.device.isMobile }, session.user_context);
            return self._rpc({
                route: '/mail/init_messaging',
                params: { context: context },
            });
        }).then(function (result) {
            self._updateInternalStateFromServer(result);
            self._busBus.start_polling();
        });
    },
    /**
     * Join the channel, and add it locally afterwards
     *
     * @private
     * @param {integer|string} channelID
     * @param {Object} options
     * @return {$.Promise}
     */
    _joinAndAddChannel: function (channelID, options) {
        var self = this;
        return this._rpc({
                model: 'mail.channel',
                method: 'channel_join_and_get_info',
                args: [[channelID]],
            })
            .then(function (result) {
                return self._addChannel(result, options);
            });
    },
    /**
     * shows a popup to notify a new received message.
     * This will also rename the odoo tab browser if
     * the user is not in it.
     *
     * @private
     * @param {mail.model.Message} msg message received
     * @param {Object} options
     * @param {boolean} options.isDisplayed
     */
    _notifyIncomingMessage: function (msg, options) {
        if (this._busBus.is_odoo_focused() && options.isDisplayed) {
            // no need to notify
            return;
        }
        var title = _t("New message");
        if (msg.hasAuthor()) {
            title = _.escape(msg.getAuthorName());
        }
        var content = utils.parse_and_transform(msg.getBody(), utils.strip_html)
            .substr(0, PREVIEW_MSG_MAX_SIZE);

        if (!this._busBus.is_odoo_focused()) {
            this._outOfFocusUnreadMessageCounter++;
            var tabTitle = _.str.sprintf(_t("%d Messages"), this._outOfFocusUnreadMessageCounter);
            webClient.set_title_part('_chat', tabTitle);
        }

        this.call('bus_service', 'sendNotification', webClient, title, content);
    },
    /**
     * @private
     * @param {string} resModel
     * @param {integer} resID
     */
    _redirectDefault: function (resModel, resID) {
        var self = this;
        this._rpc({
                model: resModel,
                method: 'get_formview_id',
                args: [[resID], session.user_context],
            })
            .then(function (viewID) {
                self._redirectToDocument(resModel, resID, viewID);
            });
    },
    /**
     * @private
     * @param {string} resModel
     * @param {integer} resID
     * @param {string} viewID
     */
    _redirectToDocument: function (resModel, resID, viewID) {
        webClient.do_action({
            type: 'ir.actions.act_window',
            view_type: 'form',
            view_mode: 'form',
            res_model: resModel,
            views: [[viewID || false, 'form']],
            res_id: resID,
        });
    },
    /**
     * @private
     * @param {string} resModel 'res.partner'
     * @param {integer} resID
     * @param {function} dmRedirectionCallback
     */
    _redirectPartner: function (resModel, resID, dmRedirectionCallback) {
        var self = this;
        var domain = [['partner_id', '=', resID]];
        this._rpc({
                model: 'res.users',
                method: 'search',
                args: [domain],
            })
            .then(function (userIDs) {
                if (userIDs.length && userIDs[0] !== session.uid && dmRedirectionCallback) {
                    self.createChannel(resID, 'dm').then(dmRedirectionCallback);
                } else {
                    self._redirectToDocument(resModel, resID);
                }
            });
    },
    /**
     * Remove channel
     *
     * This is only called by the chat_notification_manager
     *
     * @private
     * @param  {mail.model.Channel} [channel]
     * @param  {integer} [channel.directPartnerID] mandatory if type is 'dm'
     */
    _removeChannel: function (channel) {
        if (!channel) { return; }
        if (channel.getType() === 'dm') {
            var index = this._pinnedDmPartners.indexOf(channel.directPartnerID);
            if (index > -1) {
                this._pinnedDmPartners.splice(index, 1);
                this._busBus.update_option('bus_presence_partner_ids', this._pinnedDmPartners);
            }
        }
        this._conversations = _.without(this._conversations, channel);
    },
    /**
     * Removes a message from a mailbox.
     *
     * This is only called by the chat_notification_manager
     *
     * @private
     * @param {string} mailboxID
     * @param {mail.model.Message} message
     */
    _removeMessageFromMailbox: function (mailboxID, message) {
        message.removeMailbox(mailboxID);
        var mailbox = _.find(this._conversations, function (conversation) {
            return conversation.getID() === 'mailbox_' + mailboxID;
        });
        mailbox.removeMessage(message);
    },
    /**
     * @private
     */
    _resetOutOfFocusUnreadMessageCounter: function () {
        this._outOfFocusUnreadMessageCounter = 0;
    },
    /**
     * Extend the research to all users
     *
     * @private
     * @param {string} searchVal
     * @param {integer} limit
     * @return {$.Promise<Object[]>} fetched partners matching 'searchVal'
     */
    _searchPartnerFetch: function (searchVal, limit) {
        return this._rpc({
                model: 'res.partner',
                method: 'im_search',
                args: [searchVal, limit || 20],
            }, {
                shadow: true,
            });
    },
    /**
     * Search among prefetched partners
     *
     * @private
     * @param {string} searchVal
     * @param {integer} limit
     * @return {string[]} partner suggestions that match searchVal
     *   (max limit, exclude session partner)
     */
    _searchPartnerPrefetch: function (searchVal, limit) {
        var values = [];
        var searchRegexp = new RegExp(_.str.escapeRegExp(utils.unaccent(searchVal)), 'i');
        _.each(this._mentionPartnerSuggestions, function (partners) {
            if (values.length < limit) {
                values = values.concat(_.filter(partners, function (partner) {
                    return session.partner_id !== partner.id && searchRegexp.test(partner.name);
                })).splice(0, limit);
            }
        });
        return values;
    },
    /**
     * Sort channels previews
     *
     *      1. unread,
     *      2. chat,
     *      3. date of last msg
     *
     * @private
     * @param {mail.model.ChannelPreview[]} channel previews
     * @return {mail.model.ChannelPreview[]} sorted list of channel previews
     */
    _sortChannelPreviews: function (channelPreviews) {
        var res = channelPreviews.sort(function (cp1, cp2) {
            return Math.min(1, cp2.getUnreadCounter()) - Math.min(1, cp1.getUnreadCounter()) ||
                cp2.isChat() - cp1.isChat() ||
                !!cp2.hasLastMessage() - !!cp1.hasLastMessage() ||
                (cp2.hasLastMessage() && cp2.getLastMessageDate().diff(cp1.getLastMessageDate()));
        });
        return res;
    },
    /**
     * Sort conversations
     *
     * In case of mailboxes (Inbox, Starred), the name is translated
     * thanks to _lt (lazy translate). In this case, channel.getName() is an object,
     * not a string.
     *
     * @private
     */
    _sortConversations: function () {
        this._conversations = _.sortBy(this._conversations, function (conversation) {
            return _.isString(conversation.getName()) ? conversation.getName().toLowerCase() : '';
        });
    },
    /**
     * Replace emojis in a message by their corresponding unicodes
     *
     * @private
     * @param {Object} message a basic post message
     * @return {Object} updated message
     */
    _substituteEmojisByUnicodes: function (message) {
        // Replace emojis by their unicode character
        _.each(emojiUnicodes, function (unicode, key) {
            var escapedSource = String(_.escape(key)).replace(/([.*+?=^!:${}()|[\]/\\])/g, '\\$1');
            var regexp = new RegExp("(\\s|^)(" + escapedSource + ")(?=\\s|$)", 'g');
            message.body = message.body.replace(regexp, '$1' + unicode);
        });
        return message;
    },
    /**
     * Update internal state from server data (mail/init_messaging rpc result)
     *
     * @private
     * @param {Object} result data from server on mail/init_messaging rpc
     */
    _updateInternalStateFromServer: function (result) {
        var self = this;
        // commands are needed for channel instantiation
        this._commands = _.map(result.commands, function (command) {
            return _.extend({ id: command.name }, command);
        });
        // initialize channels
        _.each(result.channel_slots, function (channels) {
            _.each(channels, self._addChannel.bind(self));
        });
        // initialize mailboxes
        this._addMailbox({
            id: 'inbox',
            name: _lt("Inbox"),
            mailboxCounter: result.needaction_inbox_counter || 0,
        });
        this._addMailbox({
            id: 'starred',
            name: _lt("Starred"),
            mailboxCounter: result.starred_counter || 0,
        });
        this._mentionPartnerSuggestions = result.mention_partner_suggestions;
        this._discussMenuID = result.menu_id;

        // shortcodes: canned responses
        _.each(result.shortcodes, function (s) {
            var cannedResponse = _.pick(s, ['id', 'source', 'substitution']);
            self._cannedResponses.push(cannedResponse);
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {boolean} open
     */
    _onDiscussOpen: function (open) {
        this._discussOpen = open;
        this.chatWindowManager._onDiscussOpen(open);
    },
    /**
     * Reset out of focus unread message counter + tab title
     *
     * @private
     */
    _onWindowFocus: function () {
        this._resetOutOfFocusUnreadMessageCounter();
        webClient.set_title_part('_chat');
    },
});

var ODOOBOT_ID = "ODOOBOT"; // default author_id for transient messages

// CHAT NOTIFICATION MANAGER
ChatManager.include({

    init: function () {
        this._super.apply(this, arguments);
        this._busBus.on('notification', this, this._onNotification);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object[]} notifications
     * @return {Object[]} notifications filtered of channel notifications matching unsubscribe notifs
     */
    _filterNotificationsOnUnsubscribe: function (notifications) {
        var unsubscribedNotif = _.find(notifications, function (notif) {
            return notif[1].info === 'unsubscribe';
        });
        if (unsubscribedNotif) {
            notifications = _.reject(notifications, function (notif) {
                return notif[0][1] === 'mail.channel' && notif[0][2] === unsubscribedNotif[1].id;
            });
        }
        return notifications;
    },
    /**
     * @private
     * @param  {Object} data key, value to decide activity created or deleted
     */
    _handleActivityUpdateNotification: function (data) {
        this._chatBus.trigger('activity_updated', data);
    },
    /**
     * @private
     * @param  {Object} messageData
     * @param  {Array} messageData.channel_ids list of integers and strings,
     *      where strings for static channels, e.g. 'mailbox_inbox'.
     */
    _handleChannelNotification: function (messageData) {
        var self = this;
        var def;
        var channelAlreadyInCache = true;
        if (messageData.channel_ids.length === 1) {
            channelAlreadyInCache = !!this.getChannel(messageData.channel_ids[0]);
            def = this.joinChannel(messageData.channel_ids[0], {autoswitch: false});
        } else {
            def = $.when();
        }
        def.then(function () {
            // don't increment unread if channel wasn't in cache yet as
            // its unread counter has just been fetched
            self.addMessage(messageData, {
                showNotification: true,
                incrementUnread: channelAlreadyInCache
            });
        });
    },
    /**
     * @private
     * @param  {Object} data
     * @param  {integer|string} data.id string for static channels, e.g. 'mailbox_inbox'
     * @param  {integer} [data.last_message_id] mandatory if 'id' refers to an
     *      existing channel.
     */
    _handleChannelSeenNotification: function (data) {
        var channel = this.getChannel(data.id);
        if (channel) {
            channel.setLastSeenMessageID(data.last_message_id);
            if (channel.hasUnreadMessages()) {
                channel.updateUnreadCounter(0);
            }
        }
    },
    /**
     * Controls the session of the chat window
     * open/fold/close chat window
     *
     * @private
     * @param  {Object} serverChannelData
     * @param  {integer} serverChannelData.id
     * @param  {boolean} serverChannelData.is_minimized
     * @param  {string} serverChannelData.state
     */
    _handleChatSessionNotification: function (serverChannelData) {
        var conversation = this.getConversation(serverChannelData.id);
        if (conversation) {
            conversation.updateChatWindowVisibility({
                newFoldState: serverChannelData.state,
                newDetachState: serverChannelData.is_minimized,
            });
        }
    },
    /**
     * Updates mailbox_inbox when a message has marked as read.
     *
     * @private
     * @param  {Object} data
     * @param  {integer[]} [data.channel_ids]
     * @param  {integer[]} [data.message_ids]
     * @param  {string} [data.type]
     */
    _handleMarkAsReadNotification: function (data) {
        var self = this;
        _.each(data.message_ids, function (msgID) {
            var message = _.find(self.getMessages(), function (message) {
                return message.getID() === msgID;
            });
            if (message) {
                self._removeMessageFromMailbox('inbox', message);
                self._chatBus.trigger('update_message', message, data.type);
            }
        });
        if (data.channel_ids) {
            _.each(data.channel_ids, function (channelID) {
                var channel = self.getChannel(channelID);
                if (channel) {
                    channel.setNeedactionCounter(Math.max(channel.getNeedactionCounter() - data.message_ids.length, 0));
                }
            });
        } else { // if no channel_ids specified, this is a 'mark all read' in the inbox
            _.each(this._conversations, function (conversation) {
                conversation.setNeedactionCounter(0);
            });
        }
        var inbox = this.getMailbox('inbox');
        inbox.setMailboxCounter(Math.max(inbox.getMailboxCounter() - data.message_ids.length, 0));
        this._chatBus.trigger('update_needaction', inbox.getMailboxCounter());
    },
    /**
     * On message becoming a need action (pinned to inbox)
     *
     * @private
     * @param  {Object} messageData
     * @param  {integer[]} messageData.channel_ids
     */
    _handleNeedactionNotification: function (messageData) {
        var self = this;
        var inbox = this.getMailbox('inbox');
        var message = this.addMessage(messageData, {
            incrementUnread: true,
            showNotification: true,
        });
        if (message.isLinkedToConversation()) {
            inbox.setMailboxCounter(inbox.getMailboxCounter() + 1);
        }
        _.each(message.getConversationIDs(), function (conversationID) {
            var channel = self.getChannel(conversationID);
            if (channel) {
                channel.incrementNeedactionCounter();
            }
        });
        this._chatBus.trigger('update_needaction', inbox.getMailboxCounter());
    },
    /**
     * @private
     * @param  {Object} data structure depending on the type
     * @param  {integer} data.id
     */
    _handlePartnerNotification: function (data) {
        if (data.info === 'unsubscribe') {
            this._handleUnsubscribeNotification(data);
        } else if (data.type === 'toggle_star') {
            this._handleToggleStarNotification(data);
        } else if (data.type === 'mark_as_read') {
            this._handleMarkAsReadNotification(data);
        } else if (data.info === 'channel_seen') {
            this._handleChannelSeenNotification(data);
        } else if (data.info === 'transient_message') {
            this._handleTransientMessageNotification(data);
        } else if (data.type === 'activity_updated') {
            this._handleActivityUpdateNotification(data);
        } else {
            this._handleChatSessionNotification(data);
        }
    },
    /**
     * @private
     * @param {Object} data
     * @param {Object} data.id id of the unsubscribed channel
     */
    _handleUnsubscribeNotification: function (data) {
        var channel = this.getChannel(data.id);
        if (channel) {
            var msg;
            if (_.contains(['public', 'private'], channel.getType())) {
                msg = _.str.sprintf(_t("You unsubscribed from <b>%s</b>."), channel.getName());
            } else {
                msg = _.str.sprintf(_t("You unpinned your conversation with <b>%s</b>."), channel.getName());
            }
            this._removeChannel(channel);
            this._chatBus.trigger('unsubscribe_from_channel', data.id);
            webClient.do_notify(_("Unsubscribed"), msg);
        }
    },
    /**
     * @private
     * @param  {Object} data partner infos
     * @param  {integer} data.id
     * @param  {string} data.im_status
     */
    _handlePresenceNotification: function (data) {
        var dm = this.getDmFromPartnerID(data.id);
        if (dm) {
            dm.setStatus(data.im_status);
            this._chatBus.trigger('update_dm_presence', dm);
        }
    },
    /**
     * @private
     * @param  {Object} data
     * @param  {integer[]} data.message_ids
     * @param  {boolean} data.starred
     * @param  {string} data.type
     */
    _handleToggleStarNotification: function (data) {
        var self = this;
        var starred = this.getMailbox('starred');
        _.each(data.message_ids, function (msgID) {
            var message = _.find(self.getMessages(), function (message) {
                return message.getID() === msgID;
            });
            if (message) {
                message.setStarred(data.starred);
                if (!message.isStarred()) {
                    self._removeMessageFromMailbox('starred', message);
                } else {
                    self._addMessageToConversations(message, []);
                    var channelStarred = self.getMailbox('starred');
                    channelStarred._cache = _.pick(channelStarred._cache, '[]'); // FIXME: should not update internal state of channel
                }
                self._chatBus.trigger('update_message', message);
            }
        });

        if (data.starred) { // increase starred counter if message is marked as star
            starred.setMailboxCounter(starred.getMailboxCounter() + data.message_ids.length);
        } else { // decrease starred counter if message is remove from star if unstar_all then it will set to 0.
            starred.setMailboxCounter(starred.getMailboxCounter() - data.message_ids.length);
        }

        this._chatBus.trigger('update_starred', starred.getMailboxCounter());
    },
    /**
     * @private
     * @param  {Object} data
     * @param  {string} data.author_id
     */
    _handleTransientMessageNotification: function (data) {
        var lastMessage = _.last(this._messages);
        data.id = (lastMessage ? lastMessage.getID() : 0) + 0.01;
        data.author_id = data.author_id || ODOOBOT_ID;
        this.addMessage(data);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Notification handlers
     * Sometimes, the web client receives unsubscribe notification and an extra
     * notification on that channel.  This is then followed by an attempt to
     * rejoin the channel that we just left.  The next few lines remove the
     * extra notification to prevent that situation to occur.
     *
     * @private
     * @param  {Array} notifications
     */
    _onNotification: function (notifications) {
        var self = this;
        notifications = this._filterNotificationsOnUnsubscribe(notifications);
        _.each(notifications, function (notification) {
            var model = notification[0][1];
            if (model === 'ir.needaction') {
                // new message in the inbox
                self._handleNeedactionNotification(notification[1]);
            } else if (model === 'mail.channel') {
                // new message in a channel
                self._handleChannelNotification(notification[1]);
            } else if (model === 'res.partner') {
                // channel joined/left, message marked as read/(un)starred, chat open/closed
                self._handlePartnerNotification(notification[1]);
            } else if (model === 'bus.presence') {
                // update presence of users
                self._handlePresenceNotification(notification[1]);
            }
        });
    },
});

return ChatManager;

});
