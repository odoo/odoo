odoo.define('mail.ChatService', function (require) {
"use strict";

var ChatManager = require('mail.ChatManager');

var AbstractService = require('web.AbstractService');
var core = require('web.core');

var ChatService = AbstractService.extend({
    name: 'chat_service',
    dependencies: ['ajax', 'bus_service'],
    start: function () {
        this.chatManager = new ChatManager(this);
    },

    //--------------------------------------------------------------------------
    // Chat Manager
    //--------------------------------------------------------------------------

    /**
     * Add a new document chat, using 'model' and 'resID'
     *
     * @param {string} model
     * @param {integer} resID
     * @return {mail.model.DocumentChat}
     */
    addDocumentChat: function (model, resID) {
        return this.chatManager.addDocumentChat(model, resID);
    },
    /**
     * Creates a channel, can be either a true channel or a DM based on `type`
     *
     * @param  {integer|string} name id of partner (in case of dm) or name
     * @param  {string} type ['dm', 'public', 'private']
     * @return {$.Promise}
     */
    createChannel: function (name, type) {
        return this.chatManager.createChannel(name, type);
    },
    /**
     * Returns the list of canned responses
     * A canned response is a pre-formatted text that is triggered with
     * some keystrokes, such as with ':'.
     *
     * @return {Array} array of Objects (mail.shortcode)
     */
    getCannedResponses: function () {
        return this.chatManager.getCannedResponses();
    },
    /**
     * Returns a channel corresponding to the given id.
     *
     * @param  {integer}
     * @return {mail.model.Channel|undefined} the channel, if it exists
     */
    getChannel: function (id) {
        return this.chatManager.getChannel(id);
    },
    /**
     * Returns a list of channels
     *
     * @return {mail.model.Channel[]} list of channels
     */
    getChannels: function () {
        return this.chatManager.getChannels();
    },
    /**
     * Returns the content that will be shown in the mail navbar dropdown
     *
     * @param  {mail.model.Channel[]} channels
     * @return {$.Promise<mail.model.ChannelPreview>} resolved with array of preview msgs
     */
    getChannelPreviews: function (channels) {
        return this.chatManager.getChannelPreviews(channels);
    },
    /**
     * @return {web.Bus} the chat bus
     */
    getChatBus: function () {
        return this.chatManager.getChatBus();
    },
    /**
     * Returns a conversation corresponding to the given id.
     * note: conversations = channels & mailboxes
     *
     * @param  {string|integer} id e.g. 'mailbox_inbox', 'mailbox_starred'
     * @return {mail.model.Conversation|undefined} the conversation, if it exists
     */
    getConversation: function (id) {
        return this.chatManager.getConversation(id);
    },
    /**
     * Returns a list of conversations
     * note: conversations = channels & mailboxes
     *
     * @return {mail.model.Conversation[]} list of conversations
     */
    getConversations: function () {
        return this.chatManager.getConversations();
    },
    /**
     * Returns the record id of ir.ui.menu for Discuss
     *
     * @return {integer} record id
     */
    getDiscussMenuID: function () {
        return this.chatManager.getDiscussMenuID();
    },
    /**
     * Gets direct message channel
     *
     * @param  {integer} partnerID
     * @return {Object|undefined} channel
     */
    getDmFromPartnerID: function (partnerID) {
        return this.chatManager.getDmFromPartnerID(partnerID);
    },
    /**
     * Returns a document chat corresponding to the given model and resID.
     *
     * @param  {string} model of the document chat, if it exists
     * @return {integer} resID of the document chat, if it exists
     */
    getDocumentChat: function (model, resID) {
        return this.chatManager.getDocumentChat(model, resID);
    },
    /**
     * Returns list of emojis Objects
     *
     * @return {Object[]} list of emojis
     * ['id', 'source', 'unicode_source', 'substitution', 'description']
     */
    getEmojis: function () {
        return this.chatManager.getEmojis();
    },
    /**
     * @param {string} mailboxID
     * @return {mail.model.Mailbox} the mailbox, if any
     */
    getMailbox: function (mailboxID) {
        return this.chatManager.getMailbox(mailboxID);
    },
    /**
     * Get partners as mentions from a chatter
     *
     * Typically all employees as partner suggestions
     *
     * @return {Array<Object[]>}
     */
    getMentionPartnerSuggestions: function () {
        return this.chatManager.getMentionPartnerSuggestions();
    },
    /**
     * Gets message from its id
     *
     * @param  {integer} msgID
     * @return {Object|undefined} Message Object (if any)
     */
    getMessage: function (msgID) {
        return this.chatManager.getMessage(msgID);
    },
    /**
     * Returns the number of messages received from followed channels
     * + all messages where the current user is notified.
     *
     * @return {integer} needaction counter
     */
    getNeedactionCounter: function () {
        return this.chatManager.getNeedactionCounter();
    },
    /**
     * Gets the number of starred message
     *
     * @return {integer} starred counter
     */
    getStarredCounter: function () {
        return this.chatManager.getStarredCounter();
    },
    /**
     * Gets the number of conversation which contains unread messages
     *
     * @return {integer} unread conversation counter
     */
    getUnreadConversationCounter: function () {
        return this.chatManager.getUnreadConversationCounter();
    },
    /**
     * @return {$.Promise}
     */
    isReady: function () {
        return this.chatManager.isReady();
    },
    /**
     * Join an existing channel
     * See @createChannel to join a new channel
     *
     * @param  {integer} channelID
     * @param  {Object} [options]
     * @return {$.Promise<Object>} resolved with channel object
     */
    joinChannel: function (channelID, options) {
        return this.chatManager.joinChannel(channelID, options);
    },
    /**
     * @param {Object} data
     * @return {Object} msg to post
     */
    makeBasicPostMessage: function (data) {
        return this.chatManager.makeBasicPostMessage(data);
    },
    /**
     * Mark messages as read
     *
     * @param  {Array} msgIDs list of messages ids
     * @return {$.Promise}
     */
    markAsRead: function (msgIDs) {
        return this.chatManager.markAsRead(msgIDs);
    },
    /**
     * Post message for document chat
     *
     * @param {Object} data data related to the new message
     * @param {Object} options
     * @param {string} options.model
     * @param {integer} options.res_id
     * @return {$.Promise} resolved when message has been posted
     */
    postMessage: function (data, options) {
        return this.chatManager.postMessage(data, options);
    },
    /**
     * Special redirection handling for given model and id
     *
     * If the model is res.partner, and there is a user associated with this
     * partner which isn't the current user, open the DM with this user.
     * Otherwhise, open the record's form view, if this is not the current user's.
     *
     * @param  {string} resModel model to open
     * @param  {integer} resID record to open
     * @param  {function} [dmRedirectionCallback] only used if 'res.partner'
     */
    redirect: function (resModel, resID, dmRedirectionCallback) {
        this.chatManager.redirect(resModel, resID, dmRedirectionCallback);
    },
    /**
     * Removes all messages from the current model except 'needaction'.
     * We want to keep it in inbox.
     *
     * @param  {string} model
     */
    removeChatterMessages: function (model) {
        this.chatManager.removeChatterMessages(model);
    },
    /**
     * Search among prefetched partners, using the string 'searchVal'
     *
     * @param  {string} searchVal
     * @param  {integer} limit max number of found partners in the response
     * @return {$.Promise<Object[]>} list of found partners (matching 'searchVal')
     */
    searchPartner: function (searchVal, limit) {
        return this.chatManager.searchPartner(searchVal, limit);
    },
    /**
     * Unstars all messages from all channels
     *
     * @return {$.Promise}
     */
    unstarAll: function () {
        return this.chatManager.unstarAll();
    },

    //--------------------------------------------------------------------------
    // Chat Window Manager
    //--------------------------------------------------------------------------

    /**
     * @param {Object} chatSession
     * @param {integer} chatSession.id
     * @param {Object} options
     */
    closeChat: function (chatSession, options) {
        this.chatManager.chatWindowManager.closeChat(chatSession, options);
    },
    /**
     * Open chat window without a session ('new conversation')
     */
    openChatWithoutSession: function () {
        this.chatManager.chatWindowManager.openChatWithoutSession();
    },
    /**
     * Called when unfolding the chat window
     *
     * @param {mail.model.Channel} channel
     */
    toggleFoldChat: function (channel) {
        this.chatManager.chatWindowManager.toggleFoldChat(channel);
    },
});

core.serviceRegistry.add('chat_service', ChatService);

return ChatService;

});
