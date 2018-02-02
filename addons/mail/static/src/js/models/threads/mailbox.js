odoo.define('mail.model.Mailbox', function (require) {
"use strict";

var SearchableThread = require('mail.model.SearchableThread');

var core = require('web.core');

var _t = core._t;

/**
 * Mailboxes, called "static channels" in earlier version of Odoo, are threads
 * that are not represented on the server. We can see them as "threads that are
 * not conversations". For instance, the well-known "Inbox" folder contains a
 * list of messages, but the inbox does not represent a conversation: Inbox is
 * modeled as a mailbox.
 */
var Mailbox = SearchableThread.extend({

    /**
     * @override
     * @param {Object} params
     * @param {Object} params.data
     * @param {string} params.data.id the ID of the mailbox, without the ``mailbox_`` prefix.
     * @param {integer} [params.data.mailboxCounter=0] the initial mailbox counter of this mailbox.
     */
    init: function (params) {
        var data = params.data;
        // ID or mailboxes are always prefixed with 'mailbox_'
        data.id = 'mailbox_' + data.id;
        data.type = 'mailbox';
        this._super.apply(this, arguments);
        this._mailboxCounter = data.mailboxCounter || 0;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Decrement the counter of this mailbox. It floors to 0.
     *
     * @param {integer} [num=1] how many, at most, the counter is decremented
     */
    decrementMailboxCounter: function (num) {
        num = _.isNumber(num) ? num : 1;
        this._mailboxCounter = Math.max(this._mailboxCounter - num, 0);
    },
    /**
     * Get the mailbox counter of this mailbox.
     *
     * @returns {integer}
     */
    getMailboxCounter: function () {
        return this._mailboxCounter;
    },
    /**
     * Get the preview of the messages from the inbox mailbox.
     * If there are multiple messages associated to a similar document or
     * channel, only keep the lastest message of this document/channel in the
     * previews.
     *
     * @returns {Promise<Object[]>}
     */
    getMessagePreviews: function () {
        var self = this;

        return this.fetchMessages().then(function (messages) {
            // pick only last message of chatter
            // items = list of objects
            // {
            //    unreadCounter: {integer},
            //    message: {mail.model.Message},
            //    messageIDs: {integer[]},
            // }
            var items = [];
            _.each(messages, function (message) {
                var unreadCounter = 1;
                var messageIDs = [message.getID()];
                var similarItem = _.find(items, function (item) {
                    return self._areMessagesFromSameDocumentThread(item.message, message) ||
                            self._areMessagesFromSameChannel(item.message, message);
                });
                if (similarItem) {
                    unreadCounter = similarItem.unreadCounter + 1;
                    messageIDs = similarItem.messageIDs.concat(messageIDs);
                    var index = _.findIndex(items, similarItem);
                    items[index] = {
                        unreadCounter: unreadCounter,
                        message: message,
                        messageIDs: messageIDs
                    };
                } else {
                    items.push({
                        unreadCounter: unreadCounter,
                        message: message,
                        messageIDs: messageIDs,
                    });
                }
            });
            return _.map(items, function (item) {
                return _.extend(item.message.getPreview(), {
                    unreadCounter: item.unreadCounter,
                    messageIDs: item.messageIDs,
                });
            });
        });
    },
    /**
     * Increment the counter of this mailbox
     *
     * @param {integer} [num=1] how many, the counter is incremented
     */
    incrementMailboxCounter: function (num) {
        num = _.isNumber(num) ? num : 1;
        this._mailboxCounter = Math.max(this._mailboxCounter + num, 0);
    },
    /**
     * Marks all messages from the mailbox as read. At the moment, this method
     * makes only sense for 'Inbox'.
     *
     * @param  {Array} domain
     * @return {Promise} resolved when all messages have been marked as read
     *   on the server
     */
    markAllMessagesAsRead: function (domain) {
        if (this._id === 'mailbox_inbox' && this.getMailboxCounter() > 0) {
            return this._rpc({
                model: 'mail.message',
                method: 'mark_all_as_read',
                kwargs: {
                    domain: domain,
                },
            });
        }
        return Promise.resolve();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Tell whether the two messages originate from the same channel.
     * If any one of them does not originate from a channel, returns false.
     *
     * @private
     * @param {mail.model.Message} message1
     * @param {mail.model.Message} message2
     * @returns {boolean}
     */
    _areMessagesFromSameChannel: function (message1, message2) {
        return message1.originatesFromChannel() &&
                message2.originatesFromChannel() &&
                message1.getOriginChannelID() === message2.getOriginChannelID();
    },
    /**
     * Tell whether the two messages are linked to the same document thread.
     * If any one of them is not linked to a document, returns false.
     *
     * @private
     * @param {mail.model.Message} message1
     * @param {mail.model.Message} message2
     * @returns {boolean}
     */
    _areMessagesFromSameDocumentThread: function (message1, message2) {
        return message1.isLinkedToDocumentThread() &&
                message2.isLinkedToDocumentThread() &&
                message1.getDocumentModel() === message2.getDocumentModel() &&
                message1.getDocumentID() === message2.getDocumentID();
    },
    /**
     * Get the domain to fetch all the messages in the current mailbox
     *
     * @override
     * @private
     * @returns {Array}
     * @throws on missing domain for the provided mailbox (mailboxes should
     *   always have a domain on messages to fetch)
     */
    _getThreadDomain: function () {
        if (this._id === 'mailbox_inbox') {
            return [['needaction', '=', true]];
        } else if (this._id === 'mailbox_starred') {
            return [['starred', '=', true]];
        } else if (this._id === 'mailbox_history') {
            return [['needaction', '=', false]];
        } else if (this._id === 'mailbox_moderation') {
            return [['need_moderation', '=', true]];
        } else {
            throw (_.str(_t("Missing domain for mailbox with ID '%s'"), this._id));
        }
    },
    /**
     * Post a message from inbox. This is used when using the 'reply' feature
     * on a message that is linked to a document thread.
     *
     * @override
     * @private
     * @param {Object} messageData
     * @param {Object} options
     * @param {integer} options.documentID
     * @param {string} options.documentModel
     * @returns {$.Promise}
     */
    _postMessage: function (messageData, options) {
        var documentThread = this.call(
            'mail_service',
            'getDocumentThread',
            options.documentModel,
            options.documentID
        );
        return documentThread.postMessage(messageData);
    },
});

return Mailbox;

});
