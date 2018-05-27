odoo.define('mail.model.Mailbox', function (require) {
"use strict";

var Conversation = require('mail.model.Conversation');

var Mailbox = Conversation.extend({

    /**
     * @override
     */
    init: function (parent, data, options, commands) {
        data.id = 'mailbox_' + data.id;
        data.type = 'mailbox';
        this._super.apply(this, arguments);
        this._mailboxCounter = data.mailboxCounter;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * return {integer}
     */
    getMailboxCounter: function () {
        return this._mailboxCounter;
    },
    /**
     * @return {$.Promise<mail.model.MessagePreview[]>}
     */
    getMessagePreviews: function () {
        return this.getMessages().then(function (messages) {
            // pick only last message of chatter
            var items = []; // list of { unreadCounter: integer, message: mail.model.Message }
            _.each(messages, function (message) {
                var unreadCounter = 1;
                var similarItem = _.find(items, function (item) {
                    return item.message.getDocumentModel() === message.getDocumentModel() &&
                            item.message.getDocumentResID() === message.getDocumentResID();
                });
                if (message.isLinkedToDocument() && similarItem) {
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
            var messagePreviews = [];
            _.each(items, function (item) {
                messagePreviews.push(item.message.getPreview(item.unreadCounter));
            });
            return $.when(messagePreviews);
        });
    },
    /**
     * Marks all messages from the channel as read
     *
     * @param  {Array} domain
     * @return {$.Promise}
     */
    markAllAsRead: function (domain) {
        var self = this;
        var messageCount = this._getCache(domain).messages.length;
        if (this._id === 'mailbox_inbox' && messageCount > 0) {
            return this._rpc({
                model: 'mail.message',
                method: 'mark_all_as_read',
                kwargs: {
                    channel_ids: this._id !== 'mailbox_inbox' ? [this._id] : [],
                    domain: domain,
                },
            }).then(function () {
                self._mailboxCounter = 0;
            });
        }
        return $.when();
    },
    /**
     * @param {integer} newMailboxCounter
     */
    setMailboxCounter: function (newMailboxCounter) {
        this._mailboxCounter = newMailboxCounter;
    },
    /**
     * Remove `message` from this mailbox
     *
     * This is equivalent to removing this message from all the caches
     *
     * @param {mail.model.Message} message
     */
    removeMessage: function (message) {
        _.each(this._cache, function (cache) {
            cache.messages = _.without(cache.messages, message);
        });
    },

});

return Mailbox;

});
