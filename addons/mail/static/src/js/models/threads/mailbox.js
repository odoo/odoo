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
     * Get the local messages of the mailbox (by local messages, we mean
     * messages that have already been fetched from the server).
     *
     * It is possible to filter on local messages that are specific to a
     * document with the `options` parameter.
     *
     * @param {Object} [options]
     * @param {string} [options.documentModel] model of the document that the
     *   local messages of inbox must be linked to.
     * @param {integer} [options.documentID] ID of the document that the local
     *   messages of inbox must be linked to.
     */
    getLocalMessages: function (options) {
        var localMessages = this._cache['[]'].messages;
        if (!options) {
            return localMessages;
        }
        if (options.documentModel && options.documentID) {
            return _.filter(localMessages, function (localMessage) {
                return localMessage.getDocumentModel() === options.documentModel &&
                        localMessage.getDocumentID() === options.documentID;
            });
        }
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
     * @returns {$.Promise<Object[]>}
     */
    getMessagePreviews: function () {
        var self = this;

        return this.fetchMessages().then(function (messages) {
            // pick only last message of chatter
            // items = list of objects
            // { unreadCounter: integer, message: mail.model.Message }
            var items = [];
            _.each(messages, function (message) {
                var unreadCounter = 1;
                var similarItem = _.find(items, function (item) {
                    return self._areMessagesFromSameDocumentThread(item.message, message) ||
                            self._areMessagesFromSameChannel(item.message, message);
                });
                if (similarItem) {
                    unreadCounter = similarItem.unreadCounter + 1;
                    var index = _.findIndex(items, similarItem);
                    items[index] = {
                        unreadCounter: unreadCounter,
                        message: message,
                    };
                } else {
                    items.push({
                        unreadCounter: unreadCounter,
                        message: message,
                    });
                }
            });
            return _.map(items, function (item) {
                return _.extend(item.message.getPreview(), {
                    unreadCounter: item.unreadCounter,
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
     * @return {$.Promise} resolved when all messages have been marked as read
     *   on the server
     */
    markAllMessagesAsRead: function (domain) {
        if (this._id === 'mailbox_inbox' && this.getMailboxCounter() > 0) {
            return this._rpc({
                model: 'mail.message',
                method: 'mark_all_as_read',
                kwargs: {
                    channel_ids: [],
                    domain: domain,
                },
            });
        }
        return $.when();
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
        } else if (this._id === 'mailbox_moderation') {
            return [['need_moderation', '=', true]];
        } else {
            throw (_.str(_t("Missing domain for mailbox with ID '%s'"), this._id));
        }
    },
});

return Mailbox;

});
