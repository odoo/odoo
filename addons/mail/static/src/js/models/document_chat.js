odoo.define('mail.model.DocumentChat', function (require) {
"use strict";

var Thread = require('mail.model.Thread');

var session = require('web.session');

var DocumentChat = Thread.extend({
    /**
     * @param {mail.ChatManager} parent
     * @param {string} model
     * @param {integer} resID
     */
    init: function (parent, model, resID) {
        this._super.apply(this, arguments);

        this._documentModel = model; // model of the related document
        this._documentResID = resID; // resID of the related document
        this._messageIDs = []; // used to handle history of messages
        this._messages = []; // list of loaded messages
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @param {mail.model.Message} message
     */
    addMessage: function (message) {
        this._messages.push(message);
        this._messages = _.sortBy(this._messages, function (message) {
            return message.getID();
        });
    },
    /**
     * Get the model name of the document that is linked to this document chat
     *
     * @return {string}
     */
    getDocumentModel: function () {
        return this._documentModel;
    },
    /**
     * Get the ID of the document that is linked to this document chat
     *
     * @return {integer}
     */
    getDocumentResID: function () {
        return this._documentResID;
    },
    /**
     * /!\ RETRO-COMPATIBILITY CHAT_MANAGER:GET_MESSAGES WITH IDS
     *
     * Get messages using their ids
     *
     * @param {Object} options
     * @param {boolean} [options.forceFetch] if true, fetch anyway, as user clicked on 'load more'.
     * @return {mail.model.Message[]} messages
     */
    getMessages: function (options) {
        var self = this;
        return this._fetchMessages(options).then(function () {
            self._chatManager.markAsRead(self._messageIDs);
            return self._messages;
        });
    },
    /**
     * Set list of message IDs of this document chat
     *
     * Useful in order to handle message history of the document chat,
     * in particular to fetch messages when necessary and/or display 'load more'.
     *
     * @param {integer[]} messageIDs
     */
    setMessageIDs: function (messageIDs) {
        this._messageIDs = messageIDs;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} options
     * @param {boolean} [options.forceFetch]
     * @return {$.Promise} resolved when messages have been fetched + document chat has updated messages
     */
    _fetchMessages: function (options) {
        var self = this;
        var messageIDs = this._messageIDs;
        var loadedMessages = _.filter(this._messages, function (message) {
            return _.contains(messageIDs, message.getID());
        });
        var loadedMessageIDs = _.map(loadedMessages, function (message) {
            return message.getID();
        });

        options = options || {};
        if (options.forceFetch || _.difference(messageIDs.slice(0, this._FETCH_LIMIT), loadedMessageIDs).length) {
            var idsToLoad = _.difference(messageIDs, loadedMessageIDs).slice(0, this._FETCH_LIMIT);
            return this._rpc({
                    model: 'mail.message',
                    method: 'message_format',
                    args: [idsToLoad],
                    context: session.user_context,
                })
                .then(function (serverMessages) {
                    _.each(serverMessages, function (serverMessage) {
                        self._chatManager.addMessage(serverMessage, { silent: true });
                    });
                });
        } else {
            return $.when();
        }
    },

});

return DocumentChat;

});
