odoo.define('mail.model.DocumentThread', function (require) {
"use strict";

var Thread = require('mail.model.Thread');

var session = require('web.session');

/**
 * These threads represent threads that are directly attached to documents.
 * It is sometimes called the "chatter", but technically this is just the
 * part of the chatter containing the thread, as the chatter also contains
 * the activity and listener fields.
 *
 * Note that there are still some hacks in the handling of document threads,
 * due to document threads are instantiated from fetched messages, either from
 * mail.ThreadField or by fetching messages in Inbox.
 *
 * Also, because messages are not sent on the longpoll bus for this kind of
 * threads, it stores the list of message IDs that it contains, which should
 * be up-to-date whenever someone wants to get the messages in the document
 * thread.
 */
var DocumentThread = Thread.extend({

    /**
     * @override
     * @param {Object} params
     * @param {Object} params.data
     * @param {string} [params.data.messagesIDs] the list of message ids linked
     *   to the document (if not given, they will be fetched before fetching the
     *   messages)
     * @param {string} params.data.model
     * @param {integer} params.data.resID
     */
    init: function (params) {
        var data = params.data;
        data.id = data.resModel + '_' + data.resID;
        data.type = 'document_thread';

        this._super.apply(this, arguments);

        // ID of the related document
        this._documentID = data.resID;
        // model of the related document
        this._documentModel = data.resModel;
        // used to handle history of messages
        this._messageIDs = data.messageIDs || [];
        // list of loaded messages
        this._messages = [];

        // if the messageIDs haven't been given, fetch them before fetching the
        // messages
        this._mustFetchMessageIDs = !_.isArray(data.messageIDs);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Overrides to store the thread's state in the LocalStorage, so that it is
     * shared between tabs, and restored on F5.
     *
     * @override
     */
    close: function () {
        this._super.apply(this, arguments);
        this.call('mail_service', 'updateDocumentThreadState', this._id, {
            name: this.getName(),
            windowState: 'closed',
        });
    },
    /**
     * Overrides to store the thread's state in the LocalStorage, so that it is
     * shared between tabs, and restored on F5.
     *
     * @override
     */
    detach: function () {
        this._super.apply(this, arguments);
        var windowState = this._folded ? 'folded' : 'open';
        this.call('mail_service', 'updateDocumentThreadState', this._id, {
            name: this.getName(),
            windowState: windowState,
        });
    },
    /**
     *
     * Fetch messages of the document thread
     *
     * @override
     * @param {Object} options
     * @param {boolean} [options.forceFetch] if true, fetch anyway, as user
     *   clicked on 'load more'.
     * @returns {$.Promise<mail.model.Message[]>}
     */
    fetchMessages: function (options) {
        var self = this;
        return this._fetchMessages(options).then(function () {
            return self._messages;
        });
    },
    /**
     * Overrides to store the thread's state in the LocalStorage, so that it is
     * shared between tabs, and restored on F5.
     *
     * @override
     */
    fold: function () {
        this._super.apply(this, arguments);
        var windowState = this._folded ? 'folded' : 'open';
        this.call('mail_service', 'updateDocumentThreadState', this._id, {
            name: this.getName(),
            windowState: windowState,
        });
    },
    /**
     * Get the model name of the document that is linked to this document thread
     *
     * @returns {string}
     */
    getDocumentModel: function () {
        return this._documentModel;
    },
    /**
     * Get the ID of the document that is linked to this document thread
     *
     * @returns {integer}
     */
    getDocumentID: function () {
        return this._documentID;
    },
    /**
     * Get he list of message IDs that this document threads contain.
     *
     * @returns {integer[]}
     */
    getMessageIDs: function () {
        return this._messageIDs;
    },
    /**
     * @override
     * @returns {mail.model.Message[]}
     */
    getMessages: function () {
        return this._messages;
    },
    /**
     * States whether the thread is linked to a document
     * Document thread's are always linked to a document.
     *
     * @override
     * @returns {boolean}
     */
    isLinkedToDocument: function () {
        return true;
    },
    /**
     * @param {integer[]} attachmentIDs
     */
    removeAttachmentsFromMessages: function (attachmentIDs) {
        _.each(this.getMessages(), function (message) {
            message.removeAttachments(attachmentIDs);
        });
    },
    /**
     * Set list of message IDs of this document thread
     *
     * Useful in order to handle message history of the document thread,
     * in particular to fetch messages when necessary and/or display 'load more'.
     *
     * @param {integer[]} messageIDs
     */
    setMessageIDs: function (messageIDs) {
        this._mustFetchMessageIDs = false;
        this._messageIDs = messageIDs;
    },
    /**
     * Set the name of this document thread
     *
     * This is useful if the name of the document related to the document thread
     * has changed
     *
     * @param {string} newName
     */
    setName: function (newName) {
        this._name = newName;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Add this message to this document thread.
     *
     * This is ignored if the message is already linked to this document thread.
     * Also, there is no fetch of unread message counter in a document thread,
     * as this object is built from messages and/or thread field widget. The
     * unread counter of a document thread is the sum of needaction messages
     * linked to this document thread.
     *
     * @override
     * @private
     * @param {mail.model.Message} message
     */
    _addMessage: function (message) {
        this._super.apply(this, arguments);
        if (_.contains(this._messages, message)) {
            return;
        }
        // update internal list of messages
        this._messages.push(message);
        this._messages = _.sortBy(this._messages, function (msg) {
            return msg.getID();
        });
        // update message ids associated to this document thread
        if (!_.contains(this._messageIDs, message.getID())) {
            this._messageIDs.push(message.getID());
        }
        // update unread counter
        if (message.isNeedaction()) {
            this._unreadCounter++;
        }
    },
    /**
     * Get most up to date messageIDs
     *
     * @private
     * @returns {$.Promise} resolved when message IDs have been fetched and set
     *   in the model
     */
    _fetchMessageIDs: function () {
        var self = this;
        var resID = this.getDocumentID();
        if (!resID || !this._mustFetchMessageIDs) {
            return $.when();
        }
        return this._rpc({
            model: this.getDocumentModel(),
            method: 'read',
            args: [[resID], ['message_ids']],
        }).then(function (result) {
            self.setMessageIDs(result[0].message_ids);
        });
    },
    /**
     * @override
     * @private
     * @param {Object} options
     * @param {boolean} [options.forceFetch]
     * @returns {$.Promise} resolved when messages have been fetched + document
     *   thread has updated messages
     */
    _fetchMessages: function (options) {
        var self = this;
        return this._fetchMessageIDs().then(function () {
            var messageIDs = self._messageIDs;
            var loadedMessages = _.filter(self._messages, function (message) {
                return _.contains(messageIDs, message.getID());
            });
            var loadedMessageIDs = _.map(loadedMessages, function (message) {
                return message.getID();
            });

            options = options || {};
            var shouldFetch = _.difference(
                messageIDs.slice(0, self._FETCH_LIMIT),
                loadedMessageIDs
            ).length > 0;
            if (options.forceFetch || shouldFetch) {
                var idsToLoad = _.difference(messageIDs, loadedMessageIDs)
                                 .slice(0, self._FETCH_LIMIT);
                return self._rpc({
                        model: 'mail.message',
                        method: 'message_format',
                        args: [idsToLoad],
                        context: session.user_context,
                    })
                    .then(function (messagesData) {
                        _.each(messagesData, function (messageData) {
                            self.call('mail_service', 'addMessage', messageData, { silent: true });
                        });
                    });
            } else {
                return $.when();
            }

        });
    },
    /**
     * Overrides this method so that all the messages of this document thread
     * are marked as read on the server.
     *
     * @override
     * @private
     * @returns {$.Promise} resolved when messages have been marked as read on
     *   the server.
     */
    _markAsRead: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self.call('mail_service', 'markMessagesAsRead', self._messageIDs);
        });
    },
    /**
     * Post message for document thread
     *
     * @override
     * @private
     * @param {Object} data data related to the new message
     * @return {$.Promise<Object>} resolved when the message has been sent to
     *   the server, with the object message that has been sent to the server.
     */
    _postMessage: function (data) {
        var self = this;
        var resModel = this.getDocumentModel();
        var resID = this.getDocumentID();
        return this._super.apply(this, arguments)
            .then(function (messageData) {
                _.extend(messageData, {
                    context: data.context,
                    message_type: data.message_type,
                    subtype: data.subtype || "mail.mt_comment",
                    subtype_id: data.subtype_id,
                });
                return self._rpc({
                        model: resModel,
                        method: 'message_post',
                        args: [resID],
                        kwargs: messageData,
                    })
                    .then(function (messageID) {
                        return self._rpc({
                                model: 'mail.message',
                                method: 'message_format',
                                args: [[messageID]],
                            })
                            .then(function (messages) {
                                messages[0].model = resModel;
                                messages[0].res_id = resID;
                                self.call('mail_service', 'addMessage', messages[0], {
                                    postedFromDocumentThread: true,
                                });
                                return messages[0];
                            });
                    });
        });
    },
});

return DocumentThread;

});
